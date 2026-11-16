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

|   value_rank | name            | nation       | cap_status                  | tier                              | status                                  |   score |   score_lo |   score_hi |   p_n |    age |   pred_price_cr |   value_per_cr |
|-------------:|:----------------|:-------------|:----------------------------|:----------------------------------|:----------------------------------------|--------:|-----------:|-----------:|------:|-------:|----------------:|---------------:|
|            1 | Priyansh Arya   | India        | uncapped (no international) | established (150+ pressure balls) | Under contract (PBKS); only if released |   10.99 |     -20.49 |      41.24 |   284 | nan    |            2.37 |           5.86 |
|            2 | Shashank Singh  | India        | uncapped (no international) | emerging (40-149 pressure balls)  | Under contract (PBKS); only if released |    9.81 |     -19.28 |      37.31 |    98 |  35.36 |            1.01 |          12.55 |
|            3 | Tristan Stubbs  | South Africa | capped                      | established (150+ pressure balls) | Under contract (DC); only if released   |    9.52 |     -10.84 |      30.23 |   264 |  26.63 |            2.2  |           5.64 |
|            4 | Ayush Mhatre    | India        | uncapped (no international) | emerging (40-149 pressure balls)  | Under contract (CSK); only if released  |    8.28 |     -30.06 |      46.27 |   141 |  19.71 |            1.95 |           5.72 |
|            5 | Rinku Singh     | India        | capped                      | established (150+ pressure balls) | Under contract (KKR); only if released  |    8.11 |     -12.98 |      30.3  |   192 |  29.47 |            2.65 |           4.15 |
|            6 | Shai Hope       | West Indies  | capped                      | established (150+ pressure balls) | Open market (not on a 2026 IPL roster)  |    7.69 |     -15.43 |      30.04 |   330 |  33.39 |            2.32 |           4.56 |
|            7 | Mark Chapman    | New Zealand  | capped                      | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    6.23 |     -17.27 |      30.71 |   129 |  32.76 |            2.64 |           3.45 |
|            8 | Ashutosh Sharma | India        | uncapped (no international) | emerging (40-149 pressure balls)  | Under contract (DC); only if released   |    5.81 |     -27.24 |      39.03 |   120 |  28.54 |            1.92 |           4.54 |
|            9 | Sikandar Raza   | Zimbabwe     | capped                      | established (150+ pressure balls) | Open market (not on a 2026 IPL roster)  |    5.67 |     -17.67 |      29.05 |   189 |  40.94 |            2.38 |           3.59 |
|           10 | George Dockrell | Ireland      | capped                      | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    5.23 |     -23.18 |      34.74 |    73 |  34.69 |            2.62 |           3.1  |

## Uncapped & Value Targets: bowlers (top 10)

|   value_rank | name              | nation       | cap_status                                          | tier                              | status                                  |   score |   score_lo |   score_hi |   p_n |   age |   pred_price_cr |   value_per_cr |
|-------------:|:------------------|:-------------|:----------------------------------------------------|:----------------------------------|:----------------------------------------|--------:|-----------:|-----------:|------:|------:|----------------:|---------------:|
|            1 | Mohsin Khan       | India        | uncapped (no international)                         | established (150+ pressure balls) | Under contract (LSG); only if released  |    9.31 |      -8.57 |      27.23 |   296 | 28.71 |            1.57 |           8.16 |
|            2 | Nathan Ellis      | Australia    | capped                                              | established (150+ pressure balls) | Under contract (SRH); only if released  |    8.29 |      -9.99 |      27.14 |   269 | 32.52 |            2.94 |           4.02 |
|            3 | Akeal Hosein      | West Indies  | capped                                              | established (150+ pressure balls) | Under contract (CSK); only if released  |    7.89 |      -9.32 |      25.31 |   649 | 33.93 |            2.95 |           3.86 |
|            4 | Roston Chase      | West Indies  | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    7.35 |     -11.78 |      27.37 |   140 | 35.03 |            2.71 |           4.02 |
|            5 | Eshan Malinga     | Sri Lanka    | capped                                              | established (150+ pressure balls) | Under contract (SRH); only if released  |    7.26 |     -10.8  |      25.32 |   189 | 26.15 |            2.49 |           4.34 |
|            6 | Dunith Wellalage  | Sri Lanka    | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    6.84 |     -13.79 |      27.43 |    99 | 24.22 |            2.69 |           3.86 |
|            7 | Krunal Pandya     | India        | uncapped (Indian, last international > 5 years ago) | established (150+ pressure balls) | Under contract (RCB); only if released  |    6.61 |     -11.06 |      24.99 |   334 | 36.02 |            2.26 |           4.49 |
|            8 | Matthew Humphreys | Ireland      | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    6.56 |     -14.08 |      28.38 |    97 | 24.51 |            2.64 |           3.81 |
|            9 | Ottneil Baartman  | South Africa | capped                                              | emerging (40-149 pressure balls)  | Open market (not on a 2026 IPL roster)  |    5.77 |     -15.74 |      26.53 |    94 | 34.04 |            2.51 |           3.7  |
|           10 | Harpreet Brar     | India        | uncapped (no international)                         | established (150+ pressure balls) | Under contract (PBKS); only if released |    5.71 |     -12.48 |      24.38 |   157 | 31.54 |            1.39 |           6.63 |

## Phase 7 pool format (`phase7_pool_{bat,bowl}.csv`)

| column | meaning |
|---|---|
| uid | player id (Cricsheet identifier or rr<id>) |
| score, score_lo, score_hi | predicted run value per 100 pressure balls, 80% credible interval |
| p_top10 | posterior probability of a top-10 rank among established players |
| tier | established (150+ RR pressure balls) or emerging (40-149) |
| cap_status | IPL 2027 capped/uncapped (5-year rule applied to Indian players) |
| status, team27, buyable | 2027 availability (trades to 15 Nov 2026; retentions not yet published) |
| last_price_cr, pred_price_cr | last auction price (Rs crore, Wikipedia) and price-model estimate for 2027 |
| value_per_cr | (score - replacement level) / predicted price |
| price_known | False = under contract with no auction price on record (retained); excluded from value lists unless uncapped |