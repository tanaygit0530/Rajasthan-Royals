# Expected-outcome model comparison (S4A)

Context-only models; rolling season-ahead folds (train <= c on all sources, test c+1 on RR-pack balls, c = 2022..2025).

| model           |   bat_runs_mse |   bat_out_logloss |   bowl_runs_mse |   bowl_wkt_logloss |   outcome7_logloss |
|:----------------|---------------:|------------------:|----------------:|-------------------:|-------------------:|
| T0_cell_means   |        3.07995 |           0.21004 |         2.9919  |            0.20073 |          nan       |
| hgb_separate    |        3.0325  |           0.20984 |         2.94847 |            0.20051 |          nan       |
| lgbm_separate   |        3.03636 |           0.21016 |         2.95166 |            0.20081 |          nan       |
| lgbm_multiclass |        3.03491 |           0.21002 |         2.95166 |            0.20081 |            1.48972 |

% change vs T0 cell means (negative = better):

| model           |   bat_runs_mse |   bat_out_logloss |   bowl_runs_mse |   bowl_wkt_logloss |
|:----------------|---------------:|------------------:|----------------:|-------------------:|
| T0_cell_means   |           0    |              0    |            0    |               0    |
| hgb_separate    |          -1.54 |             -0.1  |           -1.45 |              -0.11 |
| lgbm_separate   |          -1.42 |              0.06 |           -1.35 |               0.04 |
| lgbm_multiclass |          -1.46 |             -0.01 |           -1.35 |               0.04 |

- Chosen per target (a simpler family wins if within 0.1%): {'bat_runs_mse': 'hgb_separate', 'bat_out_logloss': 'T0_cell_means', 'bowl_runs_mse': 'hgb_separate', 'bowl_wkt_logloss': 'hgb_separate'}.
- The multinomial model also provides the next-ball outcome mix used for the leverage index (S4A iii).