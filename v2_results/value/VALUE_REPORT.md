# Value hunting: uncapped and low-priced pressure performers (S5B)

- Auction prices parsed: 623 sales 2022-26; matched to modelled players: 537 (86%; exact 520, fuzzy 17). Sales per year: {2022: 204, 2023: 80, 2024: 82, 2025: 180, 2026: 77}.

## Price model (out-of-time)

|   test_auction |   n |   mae_log_model |   mae_log_baseline |   corr_model |
|---------------:|----:|----------------:|-------------------:|-------------:|
|           2024 |  62 |           1.178 |              1.165 |        0.414 |
|           2025 | 164 |           0.83  |              1.168 |        0.645 |
|           2026 |  59 |           0.833 |              0.802 |        0.513 |

- Coefficients on log price (all auctions 2023-26): {'capped': 0.794, 'overseas': -0.23, 'age': -0.011, 'age2': 0.002, 'bowler': -0.052, 'skill': 0.034, 'skill_max': 0.003, 'has_skill': 1.068, 'log_prev': 0.284, 'has_prev': -0.109, 'mega': 0.15}.
- `mae_log` = mean absolute error of log price (0.69 = off by a factor of 2 on average). Auction prices depend on team needs and bidding wars, so the model is a rough guide to the likely price band, not a forecast of the hammer price.

## Upside backtest: do early estimates for uncapped players hold up?

|                                |       n |   corr_theta_vs_later |   corr_raw_pressure_vs_later |
|:-------------------------------|--------:|----------------------:|-----------------------------:|
| ('bat', 'capped at cutoff')    |  94.667 |                 0.199 |                        0.037 |
| ('bat', 'uncapped at cutoff')  |  10     |                 0.214 |                        0.132 |
| ('bowl', 'capped at cutoff')   | 111.667 |                 0.334 |                        0.106 |
| ('bowl', 'uncapped at cutoff') |  14     |                -0.149 |                        0.086 |

- Correlation of the model estimate at cutoff c with the player's pressure run value in all later RR seasons. Uncapped samples are small (tens of players), so treat differences between groups as indicative only.

## Uncapped & Value Targets: batters (top 10)

|   value_rank | name            | nation               | cap_status   | tier                              | status                                 |   score |   score_lo |   score_hi |   p_n |   age |   pred_price_cr |   value_per_cr |
|-------------:|:----------------|:---------------------|:-------------|:----------------------------------|:---------------------------------------|--------:|-----------:|-----------:|------:|------:|----------------:|---------------:|
|            1 | Shai Hope       | West Indies          | capped       | established (150+ pressure balls) | Open market (not on a 2026 IPL roster) |    7.69 |     -15.43 |      30.04 |   330 | 33.39 |            2.32 |           4.56 |
|            2 | Mark Chapman    | New Zealand          | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    6.23 |     -17.27 |      30.71 |   129 | 32.76 |            2.64 |           3.45 |
|            3 | Sikandar Raza   | Zimbabwe             | capped       | established (150+ pressure balls) | Open market (not on a 2026 IPL roster) |    5.67 |     -17.67 |      29.05 |   189 | 40.94 |            2.38 |           3.59 |
|            4 | George Dockrell | Ireland              | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    5.23 |     -23.18 |      34.74 |    73 | 34.69 |            2.62 |           3.1  |
|            5 | Asif Khan       | United Arab Emirates | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    4.32 |     -31.15 |      39.16 |    87 | 37.12 |            2.69 |           2.68 |
|            6 | Jaker Ali Anik  | Bangladesh           | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    4.06 |     -23.48 |      31.02 |    63 | 29.1  |            2.41 |           2.89 |
|            7 | Ben Duckett     | England              | capped       | emerging (40-149 pressure balls)  | In auction pool (released by DC)       |    3.73 |     -27.69 |      33.7  |    60 | 32.45 |            2.63 |           2.52 |
|            8 | Towhid Hridoy   | Bangladesh           | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    2.37 |     -21.96 |      26.63 |   148 | 28.3  |            2.27 |           2.31 |
|            9 | Kusal Mendis    | Sri Lanka            | capped       | established (150+ pressure balls) | Open market (not on a 2026 IPL roster) |    2.26 |     -19.3  |      24.1  |   477 | 32.16 |            2.28 |           2.27 |
|           10 | Babar Hayat     | Hong Kong            | capped       | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    1.88 |     -30.64 |      34.66 |    56 | 35.24 |            2.35 |           2.03 |

## Uncapped & Value Targets: bowlers (top 10)

|   value_rank | name              | nation       | cap_status                                          | tier                              | status                                 |   score |   score_lo |   score_hi |   p_n |   age |   pred_price_cr |   value_per_cr |
|-------------:|:------------------|:-------------|:----------------------------------------------------|:----------------------------------|:---------------------------------------|--------:|-----------:|-----------:|------:|------:|----------------:|---------------:|
|            1 | Roston Chase      | West Indies  | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    7.35 |     -11.78 |      27.37 |   140 | 35.03 |            2.71 |           4.02 |
|            2 | Dunith Wellalage  | Sri Lanka    | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    6.84 |     -13.79 |      27.43 |    99 | 24.22 |            2.69 |           3.86 |
|            3 | Matthew Humphreys | Ireland      | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    6.56 |     -14.08 |      28.38 |    97 | 24.51 |            2.64 |           3.81 |
|            4 | Ottneil Baartman  | South Africa | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    5.77 |     -15.74 |      26.53 |    94 | 34.04 |            2.51 |           3.7  |
|            5 | Brad Evans        | Zimbabwe     | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    4.61 |     -16.82 |      25.89 |   118 | 33.02 |            2.37 |           3.43 |
|            6 | Lockie Ferguson   | New Zealand  | capped                                              | established (150+ pressure balls) | In auction pool (released by PBKS)     |    4.36 |     -12.81 |      21.88 |   285 | 35.8  |            2.7  |           2.92 |
|            7 | Spencer Johnson   | Australia    | capped                                              | established (150+ pressure balls) | In auction pool (released by CSK)      |    3.38 |     -18.06 |      24.67 |   150 | 31.29 |            2.69 |           2.57 |
|            8 | Chetan Sakariya   | India        | uncapped (Indian, last international > 5 years ago) | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    2.99 |     -19.49 |      25.12 |    54 | 28.61 |            0.92 |           7.07 |
|            9 | Adil Rashid       | England      | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster) |    2.87 |     -14.48 |      20.11 |   123 | 39.12 |            2.82 |           2.26 |
|           10 | Adam Zampa        | Australia    | capped                                              | established (150+ pressure balls) | Open market (not on a 2026 IPL roster) |    2.58 |     -15.22 |      19.52 |   164 | 35    |            2.62 |           2.33 |

## Phase 7 pool format (`phase7_pool_{bat,bowl}.csv`)

| column | meaning |
|---|---|
| uid | player id (Cricsheet identifier or rr<id>) |
| score, score_lo, score_hi | predicted run value per 100 pressure balls, 80% credible interval |
| p_top10 | posterior probability of a top-10 rank among established players |
| tier | established (150+ RR pressure balls) or emerging (40-149) |
| cap_status | IPL 2027 capped/uncapped (5-year rule applied to Indian players) |
| status, team27, buyable | 2027 availability after the 17 Nov 2026 retentions (config/retentions_2027.csv) |
| last_price_cr, pred_price_cr | last auction price (Rs crore, Wikipedia) and price-model estimate for 2027 |
| value_per_cr | (score - replacement level) / predicted price |
| price_known | False = under contract with no auction price on record (retained); excluded from value lists unless uncapped |