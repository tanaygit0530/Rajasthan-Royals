"""Shared player-skill machinery for S4B (backtest, s12) and S4D (final ratings, s13).

Unit of performance = run value per ball (rv): runs above context expectation minus KW x dismissals above
expectation (batter), or runs saved plus KW x wickets above expectation (bowler). KW from s11.
Pressure balls = chosen definition from s11, threshold = top 25% of RR legal balls in the TRAINING seasons.
"""
import json
import scipy.sparse as sp
from common import *

PCFG = json.load(open(res('pressure/chosen_pressure.json')))
KW = PCFG['KW_runs_per_wicket']
PDEF = os.environ.get('PDEF', PCFG['chosen'])
REC = lambda c, s: np.clip(1 - 0.1 * (c - s), 0.3, 1.0)       # recency weight (1.0 for the latest season)


def pressure_score(V, d=PDEF):
    st = np.where(V.knockout == 1, 1.0, V.stakes_bat.fillna(0.5))
    return {'D1_leverage': V.li, 'D2_leverage_phase': V.li_phase,
            'D3_baseline_PI': V.li_phase * np.where(V.knockout == 1, 1.2, 1.0),
            'D4_rrr_gap': np.where(V.innings == 2, V.rrr_gap.fillna(-99), -99),
            'D5_wicket_stress': V.wkt_stress, 'D6_close_game': V.close.astype(float),
            'D7_leverage_stakes': V.li * (0.75 + 0.5 * st)}[d]


def add_flags(V, c, d=PDEF, q=0.75):
    s = np.asarray(pressure_score(V, d), dtype=float)
    base = (V.source.eq('RR') & V.legal & V.season.between(2022, c)).values
    if d == 'D4_rrr_gap':
        base &= (V.innings == 2).values
    thr = 0.5 if d == 'D6_close_game' else np.nanquantile(s[base], q)
    V['pres'] = (s >= thr).astype(int)
    V['rv_bat'] = np.where(V.faced, (V.runs_bat - V.xruns) - KW * (V.striker_out - V.xout), np.nan)
    V['rv_bowl'] = (V.xbowl_runs - V.bowl_runs) + KW * (V.bowl_wkt - V.xbowl_wkt)
    return V, thr


def role_view(V, role):
    if role == 'bat':
        d = V[V.faced].rename(columns={'batter': 'pid', 'rv_bat': 'rv', 'bat_wpa_oe': 'wpa'})
    else:
        d = V.rename(columns={'bowler': 'pid', 'rv_bowl': 'rv', 'bowl_wpa_oe': 'wpa'})
    return d[d.pid.notna()]


def eb_shrink(sum_, n, mu, k):
    return (sum_ + k * mu) / (n + k)


def mom_k(means, ns, ball_var):
    """method-of-moments shrinkage constant k = ball variance / between-player variance (normal-normal model)"""
    w = ns / ns.sum(); mu = np.sum(w * means)
    tot = np.sum(w * (means - mu) ** 2) - np.sum(w * ball_var / ns)
    tau2 = max(tot, 1e-6)
    return float(np.clip(ball_var / tau2, 5, 1e5)), mu, tau2


# ---------------- ridge APM per cutoff (competition, venue, opponent adjusted; all sources) ----------------
def apm(c, rr_only=False, src=None):
    """player effects from the s07 ridge, refit on seasons <= c (cached).
    src: 'all' (default), 'rr' (RR-pack matches only), 'cs' (public Cricsheet matches only = no overlap with the
    RR-pack likelihood, so it can serve as a prior without counting the same balls twice)."""
    src = src or ('rr' if rr_only else 'all')
    path = w(f'skill/apm_{c}{ {"all": "", "rr": "_rronly", "cs": "_csonly"}[src]}.parquet')
    if os.path.exists(path):
        return pd.read_parquet(path)
    import s07_comp_strength as S7
    meta = json.load(open(w('comp_strength/fit_meta.json')))
    S7.DELIV_PER_LEGAL = meta['deliv_per_legal']
    B, cat = S7.load()
    E = {}
    for t, spec in S7.TARGETS.items():
        sm = B.match_id.str.startswith('rr')
        keep = (B.season <= c) & ({'all': True, 'rr': sm, 'cs': ~sm}[src])
        idx = S7.rows_for(B, spec['rows'], np.asarray(keep, bool))
        x0 = np.load(w(f'comp_strength/sol_{t}.npy'))
        E[t] = S7.fit(cat, idx, B[t].astype(float).values[idx], meta['lam'][t], spec['blocks'], x0=x0)
    pe = S7.player_table(E)
    nb = B[B.legal & (B.season <= c) & ({'all': True, 'rr': B.match_id.str.startswith('rr'), 'cs': ~B.match_id.str.startswith('rr')}[src])]
    pe['apm_bat_n'] = nb.batter.value_counts().reindex(pe.index).fillna(0)
    pe['apm_bowl_n'] = nb.bowler.value_counts().reindex(pe.index).fillna(0)
    pe['apm_bat_rv'] = pe.bat_runs - KW * pe.bat_out
    pe['apm_bowl_rv'] = pe.bowl_runs_total + KW * pe.bowl_wkt
    os.makedirs(w('skill'), exist_ok=True)
    pe.to_parquet(path)
    return pe


# ---------------- features at cutoff c ----------------
def features(V, c, role, A, P, roles):
    """V: ball values with flags (seasons <= c used). A: apm table for cutoff c. P: players (dob). roles: role table."""
    d = role_view(V[V.season <= c], role)
    r = d[d.source.eq('RR') & d.season.between(2022, c)].copy()
    r['rw'] = REC(c, r.season)
    g = r.groupby(['pid', 'pres'])
    s = g.rv.agg(['sum', 'size']).unstack(fill_value=0)
    F = pd.DataFrame(index=s.index)
    F['p_n'] = s[('size', 1)]; F['n_n'] = s[('size', 0)]
    F['p_sum'] = s[('sum', 1)]; F['n_sum'] = s[('sum', 0)]
    F['p_raw'] = F.p_sum / F.p_n.replace(0, np.nan)
    F['n_raw'] = F.n_sum / F.n_n.replace(0, np.nan)
    rw = r.assign(x=r.rv * r.rw).groupby(['pid', 'pres'])[['x', 'rw']].sum().unstack(fill_value=0)
    F['p_rec'] = rw[('x', 1)] / rw[('rw', 1)].replace(0, np.nan)
    F['p_wpa'] = r[r.pres == 1].groupby('pid').wpa.mean() * 100
    var_ball = float(r.rv.var())
    # M3 EB on pressure balls
    ok = F.p_n >= 20
    k3, mu3, _ = mom_k(F.p_raw[ok].values, F.p_n[ok].values, var_ball)
    F['M3_eb_pressure'] = eb_shrink(F.p_sum, F.p_n, mu3, k3)
    # M4 EB overall (RR balls, all situations) - no pressure term
    F['all_n'] = F.p_n + F.n_n; F['all_sum'] = F.p_sum + F.n_sum
    ok = F.all_n >= 60
    k4, mu4, _ = mom_k((F.all_sum / F.all_n)[ok].values, F.all_n[ok].values, var_ball)
    F['M4_eb_overall'] = eb_shrink(F.all_sum, F.all_n, mu4, k4)
    # pressure gap (pressure minus normal), EB shrunk to the pooled gap
    ok = (F.p_n >= 30) & (F.n_n >= 30)
    gap = (F.p_raw - F.n_raw)[ok]; gn = 1 / (1 / F.p_n[ok] + 1 / F.n_n[ok])
    kg, mug, tau2g = mom_k(gap.values, gn.values, var_ball)
    gn_all = 1 / (1 / F.p_n.clip(lower=1) + 1 / F.n_n.clip(lower=1))
    F['gap_eb'] = np.where((F.p_n > 0) & (F.n_n > 0), eb_shrink((F.p_raw - F.n_raw).fillna(0) * gn_all, gn_all, mug, kg), mug)
    F['M5_eb_overall_plus_gap'] = F.M4_eb_overall + F.gap_eb
    # M0, M1
    F['M0_raw_pressure'] = F.p_raw
    F['M1_recency_raw'] = F.p_rec
    # M6 APM
    col = 'apm_bat_rv' if role == 'bat' else 'apm_bowl_rv'
    F['M6_apm'] = A[col].reindex(F.index)
    F['apm_n'] = A['apm_bat_n' if role == 'bat' else 'apm_bowl_n'].reindex(F.index)
    # public-data volume (non-RR balls <= c)
    pub = role_view(V[(V.season <= c) & V.source.eq('CS')], role)
    F['pub_n'] = pub.groupby('pid').size().reindex(F.index).fillna(0)
    # age at 1 April of season c+1
    dob = P.set_index('uid').dob
    F['age'] = ((pd.Timestamp(f'{c + 1}-04-01') - pd.to_datetime(dob.reindex(F.index))).dt.days / 365.25)
    # role info
    R = roles.set_index('uid')
    if role == 'bat':
        F['bat_pos'] = R.bat_pos_median.reindex(F.index)
    else:
        F['pp_share'] = R.pp_share.reindex(F.index); F['death_share'] = R.death_share.reindex(F.index)
        allb = role_view(V[V.season <= c], 'bowl')
        dots = allb[allb.legal].assign(dot=lambda z: z.bowl_runs.eq(0)).groupby('pid').dot.mean()
        F['dot_rate'] = dots.reindex(F.index)
    F['last_season'] = r.groupby('pid').season.max().reindex(F.index)
    F['ipl_share'] = r.assign(i=r.comp2.eq('IPL')).groupby('pid').i.mean().reindex(F.index)
    F['rr_balls_last'] = r[r.season == c].groupby('pid').size().reindex(F.index).fillna(0)
    F.attrs.update(dict(k3=k3, k4=k4, kg=kg, mug=mug, tau2g=tau2g, var_ball=var_ball, mu4=mu4))
    return F


# ---------------- M2: baseline-style composite (re-implementation of 03_code/ratings.py logic) ----------------
def baseline_composite(V, c, role):
    d = role_view(V[V.season <= c], role)
    r = d[d.source.eq('RR') & d.season.between(2022, c)].copy()
    r['w'] = REC(c, r.season)
    r['match_n'] = r.match_id.str[2:].astype(int)
    if role == 'bat':
        r['x_main'] = r.wpa * 100; r['x_rae'] = (r.runs_bat - r.xruns) * 100; r['x_surv'] = (r.xout - r.striker_out) * 100
    else:
        r['x_main'] = r.wpa * 100; r['x_rae'] = (r.xbowl_runs - r.bowl_runs) * 100; r['x_surv'] = (r.bowl_wkt - r.xbowl_wkt) * 100
    out = pd.DataFrame(index=r.pid.unique()); sds = {}
    for cmp in ['x_main', 'x_rae', 'x_surv']:
        for pres in (0, 1):
            x = r[r.pres == pres].assign(v=lambda z: z[cmp] * z.w)
            h = x.assign(h=x.match_n % 2).groupby(['pid', 'h'])[['v', 'w']].sum()
            hm = (h.v / h.w).unstack().dropna(); rr_ = hm.corr().iloc[0, 1] if len(hm) > 10 else 0
            rel = 2 * rr_ / (1 + rr_) if rr_ > 0 else 0
            tot = x.groupby('pid')[['v', 'w']].sum()
            nbar = tot.w.median(); k = np.clip(nbar * (1 - rel) / rel, 20, 1e4) if rel > 0.02 else 1e4
            mu = tot.v.sum() / tot.w.sum()
            out[f'{cmp}_{pres}'] = ((tot.v + k * mu) / (tot.w + k)).reindex(out.index)
            if pres == 1:
                sds[cmp] = (tot.v / tot.w).std()
    pr = r[r.pres == 1].groupby(['pid', 'match_id']).x_main.agg(['sum', 'size'])
    pr = pr[pr['size'] >= 6]
    pos = (pr['sum'] > 0).groupby('pid').agg(['sum', 'count'])
    muc = pos['sum'].sum() / max(pos['count'].sum(), 1)
    out['consistency'] = ((pos['sum'] + 10 * muc) / (pos['count'] + 10) * 100).reindex(out.index)
    sds['consistency'] = out.consistency.std()
    out['delta'] = out.x_rae_1 - out.x_rae_0; sds['delta'] = out.delta.std()
    Wt = {'x_main_1': 0.35, 'x_rae_1': 0.20, 'x_surv_1': 0.15, 'consistency': 0.15, 'delta': 0.15}
    sdk = {'x_main_1': sds['x_main'], 'x_rae_1': sds['x_rae'], 'x_surv_1': sds['x_surv'], 'consistency': sds['consistency'], 'delta': sds['delta']}
    out = out.fillna(out.mean())
    return sum(wt * (out[k] - out[k].mean()) / sdk[k] for k, wt in Wt.items())


# ---------------- M8: hierarchical Bayesian (NumPyro) ----------------
def bayes_fit(F, var_ball, seed=SEED, draws=1000, warm=1000):
    """y0_i ~ N(theta_i, s/n0), y1_i ~ N(theta_i + delta_i, s/n1)
       theta_i = a + b*apm_z_i + c*age_z + c2*age_z^2 + sig_t * z_i     (overall skill, prior centred on public-data APM)
       delta_i = d0 + sig_d * u_i                                      (pressure-specific effect, partially pooled)"""
    import jax
    import numpyro
    import numpyro.distributions as dist
    from numpyro.infer import MCMC, NUTS
    numpyro.set_host_device_count(1)
    d = F.copy()
    apm_ = d.M6_apm.fillna(d.M6_apm.median()).fillna(0.0)
    az = ((apm_ - apm_.mean()) / apm_.std()).values if apm_.std() > 0 else np.zeros(len(d))
    age = d.age.fillna(d.age.median()); gz = ((age - 28) / 4).values
    n0 = d.n_n.clip(lower=0).values.astype(float); n1 = d.p_n.clip(lower=0).values.astype(float)
    y0 = np.where(n0 > 0, d.n_raw.fillna(0), 0.0); y1 = np.where(n1 > 0, d.p_raw.fillna(0), 0.0)
    s = np.sqrt(var_ball)
    se0 = np.where(n0 > 0, s / np.sqrt(np.maximum(n0, 1)), 1e3); se1 = np.where(n1 > 0, s / np.sqrt(np.maximum(n1, 1)), 1e3)

    def model():
        a = numpyro.sample('a', dist.Normal(0, 0.2)); b = numpyro.sample('b', dist.Normal(0, 0.2))
        c1 = numpyro.sample('c1', dist.Normal(0, 0.1)); c2 = numpyro.sample('c2', dist.Normal(0, 0.1))
        st = numpyro.sample('sig_t', dist.HalfNormal(0.2)); sd = numpyro.sample('sig_d', dist.HalfNormal(0.1))
        d0 = numpyro.sample('d0', dist.Normal(0, 0.1))
        with numpyro.plate('p', len(d)):
            z = numpyro.sample('z', dist.Normal(0, 1)); u = numpyro.sample('u', dist.Normal(0, 1))
            th = numpyro.deterministic('theta', a + b * az + c1 * gz + c2 * gz ** 2 + st * z)
            de = numpyro.deterministic('delta', d0 + sd * u)
            # players with no balls in a group get an uninformative (very wide) likelihood
            numpyro.sample('y0', dist.Normal(th, se0), obs=y0)
            numpyro.sample('y1', dist.Normal(th + de, se1), obs=y1)

    mc = MCMC(NUTS(model, target_accept_prob=0.9), num_warmup=warm, num_samples=draws, num_chains=1, progress_bar=False)
    mc.run(jax.random.PRNGKey(seed))
    smp = mc.get_samples()
    th = np.asarray(smp['theta']); de = np.asarray(smp['delta'])
    summ = {k: (float(np.mean(smp[k])), float(np.std(smp[k]))) for k in ['a', 'b', 'c1', 'c2', 'sig_t', 'sig_d', 'd0']}
    return th, de, summ
