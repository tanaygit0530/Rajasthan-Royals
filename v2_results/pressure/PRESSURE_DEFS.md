# Pressure-definition comparison (S3.2)

RR-pack balls 2022-26. Run value uses KW = 5.7 runs per wicket (OLS of batter WPA on runs and dismissals over expectation). Reliability = split-half (odd/even matches), Spearman-Brown corrected, players with >= 60 flagged balls. `rel_gap` = reliability of (flagged minus unflagged) run value, i.e. a pressure-specific skill. yty = season-to-season correlation (>= 30 flagged balls in both seasons).

| definition         |   share_balls |   capture_eff_bat |   capture_eff_bowl |   bat_rel_wpa |   bat_rel_rv |   bat_rel_gap_rv |   bat_yty_rv |   bowl_rel_wpa |   bowl_rel_rv |   bowl_rel_gap_rv |   bowl_yty_rv |
|:-------------------|--------------:|------------------:|-------------------:|--------------:|-------------:|-----------------:|-------------:|---------------:|--------------:|------------------:|--------------:|
| D1_leverage        |         0.25  |             2.002 |              2     |         0.188 |        0.28  |            0.161 |       -0.013 |          0.212 |         0.127 |             0.117 |         0.151 |
| D2_leverage_phase  |         0.25  |             1.96  |              1.963 |         0.182 |        0.23  |           -0.038 |        0.111 |          0.219 |         0.238 |             0.13  |         0.141 |
| D3_baseline_PI     |         0.25  |             1.958 |              1.962 |         0.194 |        0.232 |           -0.043 |        0.092 |          0.234 |         0.275 |             0.122 |         0.146 |
| D4_rrr_gap         |         0.119 |             0.909 |              0.903 |         0.112 |        0.375 |            0.07  |        0.17  |          0.22  |        -0.339 |            -0.424 |        -0.067 |
| D5_wicket_stress   |         0.25  |             0.75  |              0.748 |         0.098 |        0.074 |            0.279 |        0.041 |          0.037 |         0.293 |             0.082 |         0.081 |
| D6_close_game      |         0.439 |             1.345 |              1.348 |         0.141 |        0.102 |           -0.09  |       -0.027 |          0.149 |         0.072 |            -0.102 |         0.117 |
| D7_leverage_stakes |         0.25  |             1.987 |              1.986 |         0.196 |        0.264 |            0.001 |        0.066 |          0.323 |         0.276 |             0.345 |         0.147 |

- Rule fixed in advance: keep D1 (learned leverage) unless another definition is at least as good on both capture and reliability and strictly better on one. **Chosen: D1_leverage.** The others are kept as sensitivity checks (S4D).