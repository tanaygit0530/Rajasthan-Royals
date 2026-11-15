# Cricket primer: what makes a T20 player reliable under pressure

The purpose of this note is to set the cricket background that the v2 model is built on, and to justify each modelling choice in cricket terms.

Two kinds of evidence are used:
- **[data]** marks numbers computed from the RR data pack by `v2_code/s01_primer_facts.py`. They are saved in `v2_results/primer/`.
- **[source n]** marks claims from public sources, listed at the end with access dates.

Media figures often use different samples, so where a media figure and our own data disagree, our data is used.

---

## 1. How T20 matches are won

### Phases
T20 cricket is usually split into three phases:
- **Powerplay (PP), overs 1–6.** Only two fielders are allowed outside the circle.
- **Middle, overs 7–15.**
- **Death, overs 16–20.**

The phases score and lose wickets in very different ways. In the IPL [data]:

| IPL | PP run rate | Middle run rate | Death run rate | Balls per wicket, Death | Balls per six, PP |
|---|---|---|---|---|---|
| 2022 | 7.82 | 8.08 | 10.45 | 11.9 | 23.8 |
| 2023 | 8.72 | 8.43 | 10.49 | 12.0 | 21.5 |
| 2024 | 9.47 | 8.83 | 11.21 | 12.2 | 15.5 |
| 2025 | 9.61 | 9.03 | 10.96 | 11.6 | 14.2 |
| 2026 | 10.10 | 9.31 | 10.79 | 12.9 | 11.6 |

### The scoring revolution of 2023–26
- The powerplay run rate rose by 2.3 runs per over between 2022 and 2026, and sixes in the powerplay doubled in frequency.
- The death-over run rate barely moved. It stays at about 10.5–11.2 [data], which matches analyst claims that death scoring is close to a ceiling [source 1].
- The median IPL first-innings total (full 20 overs) rose from **170 in 2022 to 200 in 2026**. The share of first innings reaching 200+ rose from 20% to 50% [data]. Media reports record 2024 and 2025 as record seasons for run rate and sixes, with 1,294 sixes in 2025 [sources 2, 3].
- **T20Is did not follow the IPL.** Their median first-innings total stayed at about 165–170 until 2026 [data]. That alone makes raw IPL and T20I numbers non-comparable.

### Impact Player rule (IPL only, from 2023)
- Each team can replace one player from its XI with a substitute during the match. The substitute can both bat and bowl [sources 4, 5].
- In practice this adds a specialist batter or bowler and lengthens the batting line-up. Top-order batters can take more risk because there are more batters to come. Analysts link the rule to a jump in powerplay scoring without a matching rise in wicket risk [source 1].
- The rule is reported to stay in place through the 2027 IPL [sources 5, 6].

### What a chase "par" means now
Chase success by first-innings total [data]:

| Target band | IPL 2022 | IPL 2023–26 | T20I 2023–26 |
|---|---|---|---|
| 160–179 | 47% (n=19) | 70% (n=54) | 38% (n=79) |
| 180–199 | 27% (n=15) | 48% (n=56) | 35% (n=57) |
| 200–219 | 17% (n=12) | 40% (n=63) | 26% (n=35) |

In the IPL since 2023, a target of about 180–200 is now close to a coin flip. In T20Is, a target that size is still well above par.

> **Modelling implications**
> 1. The win-probability model needs an **era term** and a **competition term**. The baseline only had `is_ipl` and a team-tier level. Without an era term, a 2022 chase of 190 and a 2026 chase of 190 get the same win probability, even though they are very different situations.
> 2. Expected-runs baselines also need era and competition terms. Otherwise a 2022 batter is judged against 2026 scoring rates.
> 3. "Pressure" must be relative to the match situation, not a fixed phase. Death overs are not automatically pressure, because many are played when the result is already decided.

---

## 2. Batting roles and what "good" looks like

| Role | Typical position | Job | Signs of a good player | Main pressure situation |
|---|---|---|---|---|
| Powerplay aggressor (opener) | 1–2 | Use the fielding restrictions | High strike rate (SR) and boundary %; fewer dots | Big chases where the powerplay sets the required rate |
| Anchor | 2–4 | Bat deep and avoid collapses | High balls per dismissal, plus enough boundary hitting not to fall behind | Early wickets lost |
| Middle-overs spin player | 3–5 | Keep scoring against spin, rotate the strike | SR against spin, low dot % | Overs 7–15 with a rising required rate |
| Finisher | 5–7 | Score fast at the death | Death-over SR, sixes per ball, chasing record | Last 5 overs of a close chase |
| Floater | Any | Matchup-based promotion | Flexible splits | Situation-dependent |

- Strike rate and dismissal risk are a trade-off. Analysts prefer balls per dismissal and SR as two separate numbers, rather than batting average, which mixes them [source 7].
- Evidence on the value of the classic anchor is mixed. One analysis finds that slow 30+ innings now correlate with lower win rates [source 8]. Another finds no clear decline [source 9].

> **Modelling implication:** rate batters on **runs above expected** and **dismissals relative to expected** separately, and combine them through win-probability impact. Do not use average or SR alone.

## 3. Bowling roles and what "good" looks like

| Role | Phase | Signs of a good player |
|---|---|---|
| Powerplay swing/seam | 1–6 | Wickets above expected, dot %, limiting boundaries |
| Middle-overs spin (wrist, finger, mystery) | 7–15 | Economy relative to expected, dot %, wickets (wrist spin is usually the wicket-taker) |
| Death specialist | 16–20 | Economy relative to the *death* baseline, boundary % conceded, few extras |

- Raw death-over economy is misleading because every death bowler concedes runs. It has to be judged against the death-over baseline [sources 10, 11].
- A well-executed yorker concedes about 6 runs per over, but a missed one concedes about 11. The yorker is a high-variance tool [source 10].
- **Our data has no ball-tracking.** There are no lengths or yorker labels. `delivery_style` (for example "Full Toss", "Bouncer", "Off Cutter") and `bowl_speed` are partial proxies, and their quality is checked in the S2 audit.

> **Modelling implications**
> - Expected runs and wickets per ball must condition on phase, the wickets already fallen and the opposition. They cannot condition on line and length, because that data is unavailable.
> - Bowling consists of a few balls per match. That makes small samples worse for bowlers than for batters, which is why the baseline's split-half r for bowler pressure was only 0.03–0.06.

---

## 4. "Clutch": is it a repeatable skill?

- **Leverage index (LI).** This idea comes from baseball, formalised by Tom Tango. It measures how much the win probability can swing on the next event, scaled so that the average equals 1 [source 12]. The baseline's leverage index is the cricket version of this.
- **The evidence from baseball.** Decades of studies (Cramer 1977 and later) find that "clutch hitting" (performance in high-leverage spots compared with the same player's normal level) has **very little year-to-year correlation**. The standard view is that it is mostly chance. A minority argue that it becomes reliable with very large samples [sources 12, 13, 14].
- **The evidence from cricket.** I found **no published test** of whether T20 clutch performance repeats from year to year. Existing work proposes pressure measures (for example a pressure index for T20I chases [source 15], and clutch indices for ODI and T20 [source 16]) but does not report stability across seasons. A 2026 systematic review describes clutch metrics without validating them [source 17].
- **Shrinkage.** Bayesian hierarchical models of cricket batting are well established (Stevenson & Brewer [sources 18, 19]). Partial pooling is the standard way to handle small samples.

> **Implication.** This is the most important point for the whole project. The brief rewards players who "deliver most consistently when it matters". There are two possible interpretations:
> - **(a) Clutch.** The player rises above his own normal level under pressure.
> - **(b) Pressure reliability.** The player's expected output in high-leverage situations is high, whatever the reason.
>
> If (a) does not repeat, a ranking built on it is mostly luck. v2 therefore measures (b) as the main target and adds the pressure-specific effect (a) only in proportion to its out-of-time repeatability (S4C). The baseline found that pressure WPA has ρ≈0 between 2022–24 and 2025–26, which is consistent with the baseball result. The report will say this plainly.

## 5. How professionals evaluate players

- **Expected-value metrics.** CricViz-style "expected runs" and "expected wickets" compare a player's output with the average outcome in the same situation [sources 20, 21, 22]. Their exact formulas are not public. I found no CricViz methodology document, and I will not claim one.
- **Win probability added (WPA).** This is used by franchises and in ESPNcricinfo's Smart Stats [source 23]. Public implementations exist (GooglyPlusPlus, Boundary Line) [sources 24, 25]. A 2026 preprint (Misra & Rajaraman, "Delta") proposes a leverage-weighted, opposition-adjusted contribution measure [source 26].
- **Matchups.** Teams pick and order players against bowler types (pace or spin, left-arm or right-arm, wrist or finger spin). Our data pack has `bowling_type` (12 classes) and `batting_type` (left- or right-handed batter), so matchup splits are possible.

---

## 6. From primer to features (carried into FEATURES.md)

| Primer finding | Feature or modelling choice |
|---|---|
| Scoring shifted a lot in 2023–26, and differently in the IPL than in T20Is | `season`/era and competition terms in the WP and expected-outcome models; competition-strength model (S2) |
| Death scoring is flat while powerplay scoring rose | Phase-specific expected runs; phase profiles in player cards |
| Pressure depends on the situation, not the phase | Leverage-based pressure plus alternatives (required-rate gap, close-game window, wickets-in-hand stress) compared in S3 |
| Batters trade SR against dismissal risk | Separate runs-above-expected and dismissals-relative-to-expected components, combined through WPA |
| Raw death economy misleads | Economy and wickets measured against expected values for the phase |
| Clutch repeatability is doubtful | The S4C test decides how much weight the pressure-specific effect gets |
| Small samples, especially for bowlers | Hierarchical shrinkage with a prior from public leagues (Cricsheet) |
| Matchups matter | Batter hand × bowler type terms (M6), kept only if they validate out of time |

---

## Sources (accessed 15 Nov 2026)
1. Dan Weston, "How the impact sub revolutionised…", https://danweston.substack.com/p/how-the-impact-sub-revolutionised
2. Outlook India, "RCB's maiden win, high run-rates…", https://www.outlookindia.com/sports/cricket/rcb-maiden-win-high-run-rates-sai-sudharsan-run-scoring-numbers-that-defined-ipl-2025
3. Tribune India, "How IPL 2025 turned out to be a record-breaking runfest", https://www.tribuneindia.com/news/sports/how-ipl-2025-turned-out-to-be-a-record-breaking-runfest-a-look-into-statistics
4. RCB, "Everything you need to know: IPL's Impact Player rule", https://royalchallengers.com/rcb-cricket-news/news/everything-you-need-to-know-ipls-impact-player-rule
5. Outlook India, "Will BCCI continue the Impact Player rule for 2027?", https://www.outlookindia.com/sports/cricket/ipl-impact-player-rule-continue-2027-season-indian-premier-league
6. Deccan Herald, "IPL 2026: majority of captains express reservations…", https://www.deccanherald.com/sports/cricket/ipl-2026-majority-of-captains-express-reservations-on-contentious-impact-player-rule-3944415
7. Good Areas, "The types of T20 batters", https://www.goodareas.co/p/the-types-of-t20-batters
8. Wisden, "Why T20 anchors should aim to be less like Babar Azam…", https://wisden.com/cricket-news/why-t20-anchors-should-aim-to-be-less-like-babar-azam-and-more-like-kane-williamson
9. The Cricket Monthly, "Ten ways T20 has changed since the last World Cup", https://www.thecricketmonthly.com/story/1282046/ten-ways-t20-has-changed-since-the-last-world-cup
10. Scroll, "The yorker paradox in T20s", https://scroll.in/field/1015256/the-yorker-paradox-in-t20s-what-goes-into-constructing-a-good-death-over-and-whos-the-best-at-it
11. Wisden/CricViz, "Andre Russell's death bowling reinvention", https://wisden.com/stories/cricviz-why-andre-russells-death-bowling-reinvention-could-be-vital-to-kkrs-ipl-chances
12. Wikipedia, "Clutch hitter", https://en.wikipedia.org/wiki/Clutch_hitter
13. SABR, "Do clutch hitters exist?", https://sabr.org/journal/article/do-clutch-hitters-exist/
14. SABR, "Carleton: Believing in clutch hitting", https://sabr.org/?p=49886
15. Journal of Sports Analytics, JSA-240792, https://journals.sagepub.com/doi/10.3233/JSA-240792
16. South African Journal of Sports Medicine, clutch batting/bowling, https://www.journals.ac.za/sasj/article/download/4951/3115
17. Systematic review of limited-overs analysis (2026), https://oars.uos.ac.uk/5569/1/2026.%20Systematic%20Review%20Cricket.pdf
18. Stevenson & Brewer, "Bayesian survival analysis of batsmen in Test cricket", https://arxiv.org/abs/1609.04078
19. Stevenson & Brewer, "Modelling career trajectories of cricket players using Gaussian processes" (JRSS-C 2021), https://arxiv.org/abs/1908.11490
20. Cricketing View, "Runs above average replacement", https://cricketingview.substack.com/p/runs-above-average-replacement-raar
21. Dan Weston, "False shots & expected wickets in the IPL", https://danweston.substack.com/p/false-shots-and-expected-wickets
22. Good Areas, "The new way to explain cricket", https://www.goodareas.co/p/the-new-way-to-explain-cricket
23. The Cricket Monthly, "Which players win the most T20s?", https://www.thecricketmonthly.com/story/1350356/which-players-win-the-most-t20s-and-does-it-matter
24. R-bloggers, "GooglyPlusPlus: computing T20 player's win probability contribution", https://www.r-bloggers.com/2023/03/googlyplusplus-computing-t20-players-win-probability-contribution/
25. Boundary Line, "Evaluating player impact judiciously — T20", https://medium.com/boundary-line/evaluating-player-contribution-e2e7c9d2a5ce
26. Misra & Rajaraman (2026 preprint), "Delta", https://www.cs.columbia.edu/%7Emisra/delta-2026.pdf

**Not found / not used:** CricViz's own methodology documentation (proprietary). There is also no published study of whether T20 clutch performance repeats from year to year. v2 will produce that test itself (S4C).
