# Player profile database: data dictionary (S3B)

- `v2_work/profiles/player_profiles.parquet` (local, not committed; derived from the confidential RR pack): 3,482,733 rows, 6,748 players. Columns: pid (Cricsheet identifier, or rr<id> for RR-only players), role (bat/bowl), split, split_value, metric, value.
- `v2_work/profiles/player_identity.parquet`: name, date of birth (Wikidata, age only), batting hand, bowling type / arm / finger vs wrist spin, mystery-spinner flag (>= 10% googly/carrom/back-of-hand/chinaman deliveries), keeper share, captain matches, batting/bowling role, part-timer flag.
- `v2_results/profiles/player_profiles_summary.csv`: one row per player, headline career / IPL / last-12-months / pressure metrics.

## Splits

| split | meaning | source |
|---|---|---|
| all | career 2019-26 (Cricsheet) / 2022-26 (RR pack) | both |
| comp2 | competition (T20I split into full-member / associate games) | both |
| season, comp_season | calendar year | both |
| recent | last 12 months (from 2025-11-15) | both |
| phase | PP (1-6), Middle (7-15), Death (16-20) | both |
| pres | pressure ball (1) vs normal (0), definition D1_leverage, top 25% of RR legal balls 2022-26 | both |
| setting | setting (1st innings) vs chasing | both |
| knockout_v2 | knockout match (1) | both |
| pace_spin, bowl_type | bowler faced: pace/spin, 12 bowling types | RR pack only |
| speed_band | release speed band (pace 100-165, spin 60-115 km/h kept; other values treated as missing) | RR pack only |
| shot_group | risky (slog, slog sweep, reverse sweep, scoops, switch, upper cut, hook), defensive, orthodox attacking, nudge/other | RR pack only |
| bat_hand | batter faced (bowling) | RR pack only |
| dstyle | delivery-style mix (yorker, wide yorker, slower ball, cutter, bouncer, variation, full toss, stock) | RR pack only |
| dismissal_type | share of dismissals / wickets by type | both |

## Metrics by role and split

| role   | split          | metric                                                                                                                                                                                                                                              |
|:-------|:---------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| bat    | all            | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | bowl_type      | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, sixes, strike_rate                                                                                                                           |
| bat    | comp2          | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | comp_season    | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | dismissal_type | dismissal_share_pct                                                                                                                                                                                                                                 |
| bat    | knockout_v2    | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | pace_spin      | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, sixes, strike_rate                                                                                                                           |
| bat    | phase          | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, sixes, strike_rate                                                                                                                           |
| bat    | pres           | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, sixes, strike_rate                                                                                                                           |
| bat    | recent         | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | season         | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | setting        | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, ducks, fifties, fours, highest, hundreds, innings, not_outs, outs, pct_innings_30plus, run_value_per100, runs, score_sd, sixes, sr_after_20_balls, sr_first_10_balls, strike_rate |
| bat    | shot_group     | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, share_pct, sixes, strike_rate                                                                                                                |
| bat    | speed_band     | average, balls, balls_per_dismissal, boundary_pct, dot_pct, dots, fours, outs, run_value_per100, runs, sixes, strike_rate                                                                                                                           |
| bowl   | all            | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | bat_hand       | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, economy, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, wickets, wides                                                                                |
| bowl   | comp2          | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | comp_season    | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | dismissal_type | wicket_share_pct                                                                                                                                                                                                                                    |
| bowl   | dstyle         | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, economy, no_balls, run_value_per100, runs, share_pct, speed_median, speed_p90, strike_rate, wickets, wides                                                                     |
| bowl   | knockout_v2    | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | phase          | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, economy, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, wickets, wides                                                                                |
| bowl   | pres           | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, economy, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, wickets, wides                                                                                |
| bowl   | recent         | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | season         | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |
| bowl   | setting        | average, balls, boundaries, boundary_pct, deliveries, dot_pct, dots, econ_sd_runs, economy, four_w_plus, innings, no_balls, run_value_per100, runs, speed_median, speed_p90, strike_rate, three_w, wickets, wides                                   |

## Definitions

- Balls faced exclude wides; no-balls count. Bowler runs = runs off the bat + wides + no-ball runs (byes/leg-byes excluded). Bowler wickets exclude run outs, retired out, obstructing the field. Outs include non-striker run outs.
- run_value_per100 = 100 x mean over balls of (runs - expected runs) - KW x (dismissal - expected dismissal), KW = 5.7 runs per wicket (s11); bowlers: the mirror image.
- sr_first_10_balls / sr_after_20_balls: innings building (strike rate on balls 1-10 vs 21+ of an innings).
- score_sd, pct_innings_30plus: batting consistency; econ_sd_runs: spread of runs conceded per bowling innings.

## Not derivable from the available data

- Fielding (catches, run outs, stumpings by fielder): neither the RR pack nor Cricsheet csv2 names fielders (Cricsheet JSON does; not downloaded). Keeper status comes from the RR playing-XI flag.
- Caught in the deep vs infield, field settings, pitch type, weather.
- Batting hand and bowling type for players who appear only in Cricsheet (Cricsheet has no style fields).
- Bowling speed: RR pack only, missing or implausible on part of the balls (see DATA_AUDIT).
- Pace/spin is unknown for Cricsheet-only bowlers, so RR-only splits are blank for them.