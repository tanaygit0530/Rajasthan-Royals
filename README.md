# SupeRR Selector Season 2 – Most Reliable Players Under Pressure

Everything for the Round 1 submission in one place: the brief, the data pack, the code,
every output table, the charts and the methodology report.

> The RR data pack in `02_data/` is for this competition only and must not be shared or published.
> Keep this folder private; submit only the report and your picks on Unstop.

> **v2 (Nov 2026):** a rebuilt, out-of-time-validated version lives in `v2_code/` and `v2_results/`
> (start with `v2_results/README.md` and `v2_results/report/`). The sections below describe the v1 baseline.

## Folder map

| Folder | What is inside |
| --- | --- |
| `01_problem_statement/` | The Round 1 brief (PDF) |
| `02_data/` | The data pack, renamed to plain file names (ball_by_ball, matches, competitions, teams, competition_team_player_mapping, playing_eleven) |
| `03_code/` | The four Python scripts that produce every number, plus `requirements.txt` |
| `04_outputs/` | All results as CSV files (see below) |
| `05_charts/` | The two charts used in the report (PNG) |
| `06_report/` | The methodology report as PDF (to submit) and Word (to edit) |

## Final picks (open ranking, 40-seed model, 300 bootstrap resamples)

| Rank | Batter | Bowler |
| --- | --- | --- |
| 1 | Vaibhav Sooryavanshi | Sunil Narine |
| 2 | Tim David | Jasprit Bumrah |
| 3 | Phil Salt | Varun Chakravarthy |
| 4 | Abhishek Sharma | Mujeeb Ur Rahman |
| 5 | Shreyas Iyer | Josh Hazlewood |
| 6 | Heinrich Klaasen | Rashid Khan |
| 7 | Yashasvi Jaiswal | Mohammad Nawaz* |
| 8 | Reeza Hendricks | Krunal Pandya |
| 9 | Virat Kohli | Matheesha Pathirana |
| 10 | Suryakumar Yadav | Mahedi Hasan |

\* Not eligible for the IPL (Pakistan national). For an all-IPL-eligible bowling list, drop him,
move #8–#10 up and add Bhuvneshwar Kumar at #10.

The "RR can buy" lists (RR's own and ineligible players removed) are in `04_outputs/top10_*_RR_can_buy.csv`
and Section 6 of the report. Availability is as of 14 Nov 2026; retentions are due 17 Nov 2026.

## Method in one paragraph

1. A win-probability model (gradient boosting, averaged over 40 seeds) gives each ball a chance of
   the batting side winning.
2. Pressure = leverage: how much the win probability can swing on the next ball. The top 25% of balls
   are the pressure balls, and they carry 54% of all win-probability movement.
3. Each player is scored only on pressure balls, against context-neutral expectations:
   - win probability added or saved (35%)
   - runs above or saved vs expected (20%)
   - dismissals avoided or wickets above expected (15%)
   - consistency across pressure spells (15%)
   - rise vs his own normal-ball level (15%)
4. Balls are weighted by opposition strength and recency.
5. Shrinkage set by split-half reliability protects against small samples.
6. A 300-resample match bootstrap and nine sensitivity variants test how firm the ranking is.

Full details are in the report.

## Outputs (`04_outputs/`)

| File | Contents |
| --- | --- |
| `top10_batters_open_ranking.csv`, `top10_bowlers_open_ranking.csv` | The two top-10 lists with all supporting numbers |
| `top10_batters_RR_can_buy.csv`, `top10_bowlers_RR_can_buy.csv` | Top 10 among players RR could sign at the IPL 2027 auction |
| `open_market_*_best_available.csv` | Best-rated players not on any 2026 IPL roster |
| `rr_squad_*_pressure_ranks.csv` | Where RR's current players rank under pressure |
| `bat_full_rankings_all_eligible_players.csv`, `bowl_full_rankings_all_eligible_players.csv` | Every eligible player (103 batters, 99 bowlers) with all components |
| `sensitivity_checks.csv` | How the top 10 changes under 9 alternative settings |
| `reliability_and_shrinkage.csv` | Split-half reliability and shrinkage strength per component |
| `win_probability_model_validation.csv` | Out-of-fold accuracy of the win-probability models |
| `leverage_by_over.csv` | Average leverage per over, first innings vs chase |

Column guide for the full rankings:

| Column | Meaning |
| --- | --- |
| `rating` | Pressure Rating; 0 = average eligible player |
| `p_top10` | Share of bootstrap resamples in which the player made the top 10 |
| `rank_lo`, `rank_hi` | 80% rank range |
| `x_main` | WPA per 100 pressure balls |
| `x_rae` | Runs above expected (batting) or runs saved (bowling) per 100 balls |
| `x_surv` | Dismissals avoided (batting) or wickets above expected (bowling) |
| `consistency` | % of pressure spells with positive impact |
| `delta` | Pressure minus normal-ball performance |

## How to re-run everything

From inside `03_code/`:

    pip install -r requirements.txt
    python pipeline.py        # ~15-25 min: cleaning, 40-seed models, pressure index
    python ratings.py 300     # a few min: ratings + bootstrap
    python sens.py            # ~1 min: sensitivity checks (optional)
    python final.py           # seconds: availability tags + CSV export

- The scripts read the data from `../02_data/` automatically and write to `03_code/out/`.
- Results are identical on every run.
- For a quick test, run `N_SEEDS=2 python pipeline.py` (on Windows: `set N_SEEDS=2` first). This is
  faster but slightly noisier.
- Contract status is hard-coded in `final.py` (as of 14 Nov 2026). Update it after the 17 Nov
  retention lists.

## Sources used beyond the data pack

- [IPL 2027 confirmed trades – CricTracker](https://www.crictracker.com/cricket-news/ipl-2027-full-list-of-confirmed-trades-ahead-of-the-auction/)
- [Auction date and retention deadline – Outlook India](https://www.outlookindia.com/sports/cricket/ipl-2027-mini-auction-date-venue-announced-goa-retention-deadline-report)
- [Retention deadline moved to 17 Nov – NewsBytes](https://www.newsbytesapp.com/news/sports/ipl-2027-retention-deadline-moved-to-november-17/story)
- [Harry Brook IPL ban – Telangana Today / IANS](https://telanganatoday.com/harry-brook-opens-up-on-ipl-criticism-and-two-year-ban)
- [Andre Russell retires from IPL – ESPNcricinfo](https://www.espncricinfo.com/ci/content/story/1513852.html)
- [Possible overseas releases – MyKhel](https://www.mykhel.com/cricket/ipl-2027-retentions-kkr-srh-rr-alert-5-overseas-players-who-could-be-released-ahead-ipl-auction-456967.html)
