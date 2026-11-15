# Pressure-definition comparison (S3.2)

RR-pack balls 2022-26. Run value uses KW = 5.6 runs per wicket (OLS of batter WPA on runs and dismissals over expectation). Reliability = split-half (odd/even matches), Spearman-Brown corrected, players with >= 60 flagged balls. `rel_gap` = reliability of (flagged minus unflagged) run value, i.e. a pressure-specific skill. yty = season-to-season correlation (>= 30 flagged balls in both seasons).

| definition         |   share_balls |   capture_eff_bat |   capture_eff_bowl |   bat_rel_wpa |   bat_rel_rv |   bat_rel_gap_rv |   bat_yty_rv |   bowl_rel_wpa |   bowl_rel_rv |   bowl_rel_gap_rv |   bowl_yty_rv |
|:-------------------|--------------:|------------------:|-------------------:|--------------:|-------------:|-----------------:|-------------:|---------------:|--------------:|------------------:|--------------:|
| D1_leverage        |         0.25  |             1.983 |              1.981 |         0.183 |        0.176 |            0.056 |       -0.01  |          0.09  |         0.045 |             0.042 |         0.123 |
| D2_leverage_phase  |         0.25  |             1.937 |              1.939 |         0.136 |        0.158 |           -0.097 |        0.009 |          0.108 |         0.04  |             0.046 |         0.091 |
| D3_baseline_PI     |         0.25  |             1.934 |              1.936 |         0.151 |        0.156 |           -0.081 |        0.016 |          0.115 |         0.032 |             0.034 |         0.108 |
| D4_rrr_gap         |         0.119 |             0.901 |              0.897 |         0.104 |        0.367 |            0.065 |        0.173 |          0.242 |        -0.294 |            -0.379 |        -0.085 |
| D5_wicket_stress   |         0.25  |             0.758 |              0.757 |         0.097 |        0.075 |            0.276 |        0.042 |          0.056 |         0.283 |             0.075 |         0.079 |
| D6_close_game      |         0.437 |             1.354 |              1.357 |         0.149 |        0.116 |           -0.101 |       -0.012 |          0.168 |         0.093 |            -0.08  |         0.109 |
| D7_leverage_stakes |         0.25  |             1.969 |              1.968 |         0.138 |        0.22  |            0.015 |        0.073 |          0.216 |         0.123 |             0.163 |         0.119 |

- Rule fixed in advance: keep D1 (learned leverage) unless another definition is at least as good on both capture and reliability and strictly better on one. **Chosen: D1_leverage.** The others are kept as sensitivity checks (S4D).