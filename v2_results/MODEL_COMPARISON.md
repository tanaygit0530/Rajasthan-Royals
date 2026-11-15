# Model comparison (all out of time)

## Win probability

|   innings | model               |   logloss |   brier |    auc |
|----------:|:--------------------|----------:|--------:|-------:|
|         1 | logistic            |    0.6343 |  0.221  | 0.7041 |
|         1 | lightgbm            |    0.6598 |  0.2293 | 0.6897 |
|         1 | B0_feats_all_data   |    0.6661 |  0.232  | 0.6784 |
|         1 | blend_gbm           |    0.6885 |  0.2382 | 0.6809 |
|         1 | B0_baseline_replica |    0.6949 |  0.2377 | 0.6766 |
|         1 | xgboost             |    0.7086 |  0.2427 | 0.6826 |
|         1 | hgb                 |    0.7235 |  0.2458 | 0.6669 |
|         2 | logistic            |    0.4019 |  0.1306 | 0.8996 |
|         2 | B0_feats_all_data   |    0.4198 |  0.1368 | 0.8942 |
|         2 | hgb                 |    0.4451 |  0.1426 | 0.8856 |
|         2 | blend_gbm           |    0.4539 |  0.1449 | 0.8836 |
|         2 | xgboost             |    0.4628 |  0.1464 | 0.8818 |
|         2 | B0_baseline_replica |    0.4633 |  0.143  | 0.8892 |
|         2 | lightgbm            |    0.487  |  0.1552 | 0.8718 |

## Expected outcomes

| model           |   bat_runs_mse |   bat_out_logloss |   bowl_runs_mse |   bowl_wkt_logloss |   outcome7_logloss |
|:----------------|---------------:|------------------:|----------------:|-------------------:|-------------------:|
| T0_cell_means   |        3.07995 |           0.21004 |         2.9919  |            0.20073 |          nan       |
| hgb_separate    |        3.0325  |           0.20984 |         2.94847 |            0.20051 |          nan       |
| lgbm_separate   |        3.03636 |           0.21016 |         2.95166 |            0.20081 |          nan       |
| lgbm_multiclass |        3.03491 |           0.21002 |         2.95166 |            0.20081 |            1.48972 |

## Pressure definitions

| definition         |   share_balls |   capture_eff_bat |   capture_eff_bowl |   bat_rel_wpa |   bat_n |   bat_rel_rv |   bat_rel_gap_rv |   bat_yty_rv |   bat_yty_pairs |   bowl_rel_wpa |   bowl_n |   bowl_rel_rv |   bowl_rel_gap_rv |   bowl_yty_rv |   bowl_yty_pairs |
|:-------------------|--------------:|------------------:|-------------------:|--------------:|--------:|-------------:|-----------------:|-------------:|----------------:|---------------:|---------:|--------------:|------------------:|--------------:|-----------------:|
| D1_leverage        |         0.25  |             1.983 |              1.981 |         0.183 |     180 |        0.176 |            0.056 |       -0.01  |             246 |          0.09  |      209 |         0.045 |             0.042 |         0.123 |              256 |
| D2_leverage_phase  |         0.25  |             1.937 |              1.939 |         0.136 |     187 |        0.158 |           -0.097 |        0.009 |             250 |          0.108 |      212 |         0.04  |             0.046 |         0.091 |              252 |
| D3_baseline_PI     |         0.25  |             1.934 |              1.936 |         0.151 |     187 |        0.156 |           -0.081 |        0.016 |             253 |          0.115 |      215 |         0.032 |             0.034 |         0.108 |              254 |
| D4_rrr_gap         |         0.119 |             0.901 |              0.897 |         0.104 |     107 |        0.367 |            0.065 |        0.173 |              59 |          0.242 |      123 |        -0.294 |            -0.379 |        -0.085 |              102 |
| D5_wicket_stress   |         0.25  |             0.758 |              0.757 |         0.097 |     235 |        0.075 |            0.276 |        0.042 |             221 |          0.056 |      214 |         0.283 |             0.075 |         0.079 |              257 |
| D6_close_game      |         0.437 |             1.354 |              1.357 |         0.149 |     263 |        0.116 |           -0.101 |       -0.012 |             408 |          0.168 |      296 |         0.093 |            -0.08  |         0.109 |              384 |
| D7_leverage_stakes |         0.25  |             1.969 |              1.968 |         0.138 |     193 |        0.22  |            0.015 |        0.073 |             245 |          0.216 |      211 |         0.123 |             0.163 |         0.119 |              256 |

## Player skill: next-season pressure run value

### Batters

| model                  |   wcorr |   spearman |   top10_hit |   ceiling |
|:-----------------------|--------:|-----------:|------------:|----------:|
| M8_bayes               |   0.205 |      0.124 |       0.225 |     0.444 |
| M6_apm                 |   0.194 |      0.114 |       0.225 |     0.444 |
| M4_eb_overall          |   0.191 |      0.127 |       0.225 |     0.444 |
| M5_eb_overall_plus_gap |   0.157 |      0.066 |       0.25  |     0.444 |
| M7_stack               |   0.119 |      0.055 |       0.2   |     0.444 |
| M0_raw_pressure        |   0.089 |     -0.003 |       0.175 |     0.444 |
| M1_recency_raw         |   0.086 |     -0.008 |       0.15  |     0.444 |
| M3_eb_pressure         |   0.078 |      0.019 |       0.15  |     0.444 |
| M2_baseline            |  -0.019 |     -0.008 |       0.075 |     0.444 |

### Bowlers

| model                  |   wcorr |   spearman |   top10_hit |   ceiling |
|:-----------------------|--------:|-----------:|------------:|----------:|
| M6_apm                 |   0.236 |      0.261 |       0.175 |     0.348 |
| M8_bayes               |   0.227 |      0.247 |       0.175 |     0.348 |
| M7_stack               |   0.221 |      0.256 |       0.233 |     0.348 |
| M4_eb_overall          |   0.162 |      0.154 |       0.2   |     0.348 |
| M5_eb_overall_plus_gap |   0.132 |      0.143 |       0.175 |     0.348 |
| M3_eb_pressure         |   0.092 |      0.1   |       0.15  |     0.348 |
| M0_raw_pressure        |   0.073 |      0.086 |       0.175 |     0.348 |
| M1_recency_raw         |   0.069 |      0.085 |       0.175 |     0.348 |
| M2_baseline            |  -0.124 |     -0.064 |       0.075 |     0.348 |

## Ablation

### Batters

| variant                                                  |   mean_corr |   diff_vs_full |    se |   folds_better |
|:---------------------------------------------------------|------------:|---------------:|------:|---------------:|
| APM from RR-pack only (no public data)                   |       0.266 |          0.06  | 0.031 |              3 |
| full                                                     |       0.206 |          0     | 0     |              0 |
| full + pressure-specific effect                          |       0.204 |         -0.001 | 0.006 |              1 |
| no APM prior (no public data, no competition adjustment) |       0.204 |         -0.002 | 0.064 |              2 |
| no age curve                                             |       0.206 |          0.001 | 0.001 |              3 |
| public-only APM prior (no double counting)               |       0.158 |         -0.047 | 0.07  |              2 |

### Bowlers

| variant                                                  |   mean_corr |   diff_vs_full |    se |   folds_better |
|:---------------------------------------------------------|------------:|---------------:|------:|---------------:|
| APM from RR-pack only (no public data)                   |       0.185 |         -0.047 | 0.032 |              1 |
| full                                                     |       0.232 |          0     | 0     |              0 |
| full + pressure-specific effect                          |       0.226 |         -0.006 | 0.006 |              1 |
| no APM prior (no public data, no competition adjustment) |       0.163 |         -0.068 | 0.054 |              1 |
| no age curve                                             |       0.233 |          0.001 | 0.001 |              2 |
| public-only APM prior (no double counting)               |       0.231 |         -0.001 | 0.014 |              2 |

## Interval coverage (80% predictive intervals)

| role   |   cutoff |   coverage_80 |   n |
|:-------|---------:|--------------:|----:|
| bat    |     2022 |         0.597 |  67 |
| bat    |     2023 |         0.723 |  83 |
| bat    |     2024 |         0.717 |  92 |
| bat    |     2025 |         0.667 |  78 |
| bowl   |     2022 |         0.767 |  60 |
| bowl   |     2023 |         0.717 | 106 |
| bowl   |     2024 |         0.748 | 111 |
| bowl   |     2025 |         0.711 |  83 |

## Profile-feature LightGBM vs the Bayesian model

|                                          |   wcorr |   spearman |
|:-----------------------------------------|--------:|-----------:|
| ('bat', 'LightGBM on profile features')  |   0.029 |      0.035 |
| ('bat', 'M8_bayes (s12)')                |   0.2   |      0.153 |
| ('bowl', 'LightGBM on profile features') |   0.164 |      0.166 |
| ('bowl', 'M8_bayes (s12)')               |   0.229 |      0.243 |

## Decisions

- WP: logistic (simplest and best). Expected outcomes: sklearn HGB. Pressure: learned leverage.
- Skill: hierarchical Bayes, overall skill only; bowlers with a public-league prior, batters without a prior; no age curve. Every fancier variant that did not beat its simpler alternative out of time was dropped (hard rule 6).