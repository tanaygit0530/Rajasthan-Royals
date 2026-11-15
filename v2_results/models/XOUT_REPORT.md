# Expected-outcome model comparison (S4A)

Context-only models; rolling season-ahead folds (train <= c on all sources, test c+1 on RR-pack balls, c = 2022..2025).

| model           |   bat_runs_mse |   bat_out_logloss |   bowl_runs_mse |   bowl_wkt_logloss |   outcome7_logloss |
|:----------------|---------------:|------------------:|----------------:|-------------------:|-------------------:|
| T0_cell_means   |        3.07995 |           0.21004 |         2.9919  |            0.20073 |          nan       |
| hgb_separate    |        3.03327 |           0.20971 |         2.94879 |            0.20043 |          nan       |
| lgbm_separate   |        3.03693 |           0.21006 |         2.95151 |            0.20078 |          nan       |
| lgbm_multiclass |        3.03444 |           0.20996 |         2.95151 |            0.20078 |            1.49006 |

% change vs T0 cell means (negative = better):

| model           |   bat_runs_mse |   bat_out_logloss |   bowl_runs_mse |   bowl_wkt_logloss |
|:----------------|---------------:|------------------:|----------------:|-------------------:|
| T0_cell_means   |           0    |              0    |            0    |               0    |
| hgb_separate    |          -1.52 |             -0.16 |           -1.44 |              -0.15 |
| lgbm_separate   |          -1.4  |              0.01 |           -1.35 |               0.03 |
| lgbm_multiclass |          -1.48 |             -0.04 |           -1.35 |               0.03 |

- Chosen per target (a simpler family wins if within 0.1%): {'bat_runs_mse': 'hgb_separate', 'bat_out_logloss': 'hgb_separate', 'bowl_runs_mse': 'hgb_separate', 'bowl_wkt_logloss': 'hgb_separate'}.
- The multinomial model also provides the next-ball outcome mix used for the leverage index (S4A iii).