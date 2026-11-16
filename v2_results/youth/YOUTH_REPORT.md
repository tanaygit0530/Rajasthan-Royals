# Youth talent board (S5C)

Policy: cricket performance data and age only. Dates of birth (Wikidata) are used solely to compute age and are not published. No personal, family or social-media information is collected.

Pool: age <= 26 on 1 Apr 2027, >= 60 balls since 2024, >= 120 balls since 2022 outside associate-nation T20Is and less than half of their balls in associate T20Is (estimates built mainly on associate cricket are too weakly linked to the IPL to trust).

## Development model backtest (skill to 2021 -> skill from 2024-26 data only, 5-fold CV by player)

| role   | model                   | group                  |   n |       r |   mse_per100 |
|:-------|:------------------------|:-----------------------|----:|--------:|-------------:|
| bat    | (a) early skill only    | all aged <= 26 in 2021 | 130 |   0.647 |      185.789 |
| bat    | (a) early skill only    | aged <= 23 in 2021     |  45 |   0.603 |      233.777 |
| bat    | (b) + age               | all aged <= 26 in 2021 | 130 |   0.652 |      183.595 |
| bat    | (b) + age               | aged <= 23 in 2021     |  45 |   0.588 |      232.434 |
| bat    | (c) + age + sample size | all aged <= 26 in 2021 | 130 |   0.651 |      183.86  |
| bat    | (c) + age + sample size | aged <= 23 in 2021     |  45 |   0.588 |      232.464 |
| bat    | mean only               | all aged <= 26 in 2021 | 130 | nan     |      323.722 |
| bat    | mean only               | aged <= 23 in 2021     |  45 | nan     |      360.097 |
| bowl   | (a) early skill only    | all aged <= 26 in 2021 | 157 |   0.565 |      138.433 |
| bowl   | (a) early skill only    | aged <= 23 in 2021     |  58 |   0.507 |      137.682 |
| bowl   | (b) + age               | all aged <= 26 in 2021 | 157 |   0.559 |      140.072 |
| bowl   | (b) + age               | aged <= 23 in 2021     |  58 |   0.494 |      139.47  |
| bowl   | (c) + age + sample size | all aged <= 26 in 2021 | 157 |   0.551 |      141.784 |
| bowl   | (c) + age + sample size | aged <= 23 in 2021     |  58 |   0.479 |      142.392 |
| bowl   | mean only               | all aged <= 26 in 2021 | 157 | nan     |      204.772 |
| bowl   | mean only               | aged <= 23 in 2021     |  58 | nan     |      190.036 |

- Fitted (c) on all 130 batters / 157 bowlers: batting age coefficient -1.26 runs per 100 balls per year of age, bowling -0.71. Age and sample size did NOT improve on early skill alone for players aged 23 or under (rows (b), (c) vs (a)), so projections use model (a): 3-season projection = 9.9 + 0.79 x current (batters), 2.4 + 0.67 x current (bowlers), in runs per 100 balls.

- Season-to-season change by age (linear fit, all leagues, >= 120 balls in both seasons): bat: -2.21 at age 20, -2.03 at age 30 (runs per 100 balls per season); bowl: -3.40 at age 20, -2.44 at age 30 (runs per 100 balls per season). The change is negative at every age: that is regression to the mean among players picked after good seasons, not a development curve, so it is used only for the size of year-to-year noise, not as growth.

- Excluded from the bat board as not eligible for the IPL: Abbas Afridi, Saim Ayub, Khawaja Nafay, Shaheen Afridi, Yasir Khan, Haseebullah Khan, Sameer Minhas, Maaz Sadaqat....
## Youth board: batters aged <= 23 (top 15)

Skill and projections in runs per 100 balls vs average (competition / venue / opponent adjusted). Reference: established players (>= 1000 balls) median 30.0, 75th percentile 37.1.

|   board_rank | name                 |   age | cap_status                  | status_2027                             | label        |    n |   skill |   proj_1 |   proj_1_lo |   proj_1_hi | sample_flag               |
|-------------:|:---------------------|------:|:----------------------------|:----------------------------------------|:-------------|-----:|--------:|---------:|------------:|------------:|:--------------------------|
|            1 | Vaibhav Sooryavanshi |    16 | capped                      | Already RR                              | Buy now      |  703 |   106.3 |    106.3 |        85.2 |       127.4 |                           |
|            2 | Ayush Mhatre         |    19 | uncapped (no international) | Under contract (CSK); only if released  | Buy now      |  239 |    61.2 |     61.2 |        38.4 |        84   | small sample (<500 balls) |
|            3 | Dewald Brevis        |    23 | capped                      | Under contract (CSK); only if released  | Strong watch | 2367 |    48.5 |     48.5 |        28.3 |        68.7 |                           |
|            4 | Brian Bennett        |    23 | capped                      | Open market (not on a 2026 IPL roster)  | Strong watch | 1597 |    43.7 |     43.7 |        23.3 |        64.2 |                           |
|            5 | Hassan Eisakhil      |    20 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  151 |    35.9 |     35.9 |        12.1 |        59.7 | small sample (<500 balls) |
|            6 | Cooper Connolly      |    23 | capped                      | Under contract (PBKS); only if released | Strong watch |  997 |    35.3 |     35.3 |        14.6 |        56.1 |                           |
|            7 | Jacob Bethell        |    23 | capped                      | Under contract (RCB); only if released  | Strong watch | 1204 |    31.7 |     31.7 |        11.1 |        52.3 |                           |
|            8 | JM Coles             |    22 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  801 |    30.4 |     30.4 |         9.4 |        51.4 |                           |
|            9 | Nitish Reddy         |    23 | capped                      | Under contract (SRH); only if released  | Strong watch |  766 |    30.3 |     30.3 |         9.2 |        51.3 |                           |
|           10 | Sameer Rizvi         |    23 | uncapped (no international) | Under contract (DC); only if released   | Track        |  449 |    29.9 |     29.9 |         8.2 |        51.6 | small sample (<500 balls) |
|           11 | Joel Davies          |    23 | capped                      | Open market (not on a 2026 IPL roster)  | Track        |  135 |    29.5 |     29.5 |         5.5 |        53.5 | small sample (<500 balls) |
|           12 | Angkrish Raghuvanshi |    22 | uncapped (no international) | Under contract (KKR); only if released  | Track        |  677 |    28   |     28   |         6.8 |        49.1 |                           |
|           13 | JT Todd              |    23 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Track        |  244 |    27.6 |     27.6 |         4.8 |        50.3 | small sample (<500 balls) |
|           14 | JEK Rew              |    23 | capped                      | Open market (not on a 2026 IPL roster)  | Track        |  525 |    26.1 |     26.1 |         4.7 |        47.6 |                           |
|           15 | W Luxton             |    23 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Track        |  432 |    21.9 |     21.9 |         0.1 |        43.6 | small sample (<500 balls) |

- Excluded from the bowl board as not eligible for the IPL: Faisal Akram, Jahandad Khan, Zaman Khan, Abbas Afridi, Saim Ayub, Mehran Mumtaz, Hunain Shah, Shaheen Afridi....
## Youth board: bowlers aged <= 23 (top 15)

Skill and projections in runs per 100 balls vs average (competition / venue / opponent adjusted). Reference: established players (>= 1000 balls) median 14.6, 75th percentile 21.5.

|   board_rank | name            |   age | cap_status                  | status_2027                             | label        |    n |   skill |   proj_1 |   proj_1_lo |   proj_1_hi | sample_flag               |
|-------------:|:----------------|------:|:----------------------------|:----------------------------------------|:-------------|-----:|--------:|---------:|------------:|------------:|:--------------------------|
|            1 | Noor Ahmad      |    22 | capped                      | Under contract (CSK); only if released  | Strong watch | 3726 |    32.9 |     32.9 |        13.8 |        52.1 |                           |
|            2 | Allah Ghazanfar |    20 | capped                      | Under contract (MI); only if released   | Strong watch | 1240 |    32.6 |     32.6 |        12.9 |        52.3 |                           |
|            3 | Sakib Hussain   |    22 | uncapped (no international) | Under contract (SRH); only if released  | Strong watch |  276 |    29.3 |     29.3 |         7.6 |        51   | small sample (<500 balls) |
|            4 | Joel Davies     |    23 | capped                      | Open market (not on a 2026 IPL roster)  | Strong watch |  318 |    22.3 |     22.3 |         0.9 |        43.8 | small sample (<500 balls) |
|            5 | Cooper Connolly |    23 | capped                      | Under contract (PBKS); only if released | Strong watch |  582 |    21.1 |     21.1 |         0.6 |        41.6 |                           |
|            6 | Suyash Sharma   |    23 | uncapped (no international) | Under contract (RCB); only if released  | Strong watch | 1041 |    18.1 |     18.1 |        -1.8 |        37.9 |                           |
|            7 | F Singh         |    22 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  296 |    17.6 |     17.6 |        -4   |        39.1 | small sample (<500 balls) |
|            8 | AM Green        |    20 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  150 |    17.4 |     17.4 |        -5.6 |        40.4 | small sample (<500 balls) |
|            9 | SM Meherob      |    23 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  214 |    15   |     15   |        -7.2 |        37.2 | small sample (<500 balls) |
|           10 | Farhan Ahmed    |    19 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Strong watch |  138 |    15   |     15   |        -8.2 |        38.2 | small sample (<500 balls) |
|           11 | M Tharupathi    |    22 | uncapped (no international) | Open market (not on a 2026 IPL roster)  | Track        |  184 |    11.4 |     11.4 |       -11.2 |        33.9 | small sample (<500 balls) |
|           12 | Mahli Beardman  |    21 | capped                      | Open market (not on a 2026 IPL roster)  | Track        |  270 |    11.3 |     11.3 |       -10.5 |        33   | small sample (<500 balls) |
|           13 | Kwena Maphaka   |    20 | capped                      | Already RR                              | Track        |  969 |    11   |     11   |        -8.9 |        30.9 |                           |
|           14 | Rehan Ahmed     |    22 | capped                      | Under contract (DC); only if released   | Track        | 1626 |     8.6 |      8.6 |       -10.9 |        28.1 |                           |
|           15 | Jacob Bethell   |    23 | capped                      | Under contract (RCB); only if released  | Track        |  314 |     4.8 |      4.8 |       -16.6 |        26.3 | small sample (<500 balls) |

## All-rounders aged <= 23 (top 5; >= 300 balls in each discipline)

| name            |   age | cap_status                  | status_2027                             |    n |   n_bowl |   combined_proj |   combined_sd |
|:----------------|------:|:----------------------------|:----------------------------------------|-----:|---------:|----------------:|--------------:|
| Cooper Connolly |    23 | capped                      | Under contract (PBKS); only if released |  997 |      582 |            56.5 |          22.8 |
| Jacob Bethell   |    23 | capped                      | Under contract (RCB); only if released  | 1204 |      314 |            36.5 |          23.2 |
| JM Coles        |    22 | uncapped (no international) | Open market (not on a 2026 IPL roster)  |  801 |      877 |            34.7 |          22.6 |
| Nitish Reddy    |    23 | capped                      | Under contract (SRH); only if released  |  766 |      571 |            29.2 |          22.9 |
| Rehan Ahmed     |    22 | capped                      | Under contract (DC); only if released   |  774 |     1626 |            16.5 |          22.4 |

## Comparables

For each board player: the three historical players (2019-21) of the same age (+-1 year) with the closest adjusted skill, and their 2024-26 skill. A comparable who later has no 2024-26 data dropped out of the top level - an honest reminder of the attrition rate.

- See `comparables.csv` (86 rows). Share of comparables with no 2024-26 data: 0%.

## Lower-resolution sources

- U19, Vijay Hazare, state T20 leagues (TNPL, Maharaja Trophy, UP T20, DPL, Mumbai T20) and India A have no licensed ball-by-ball data; ESPNcricinfo/BCCI scorecards may not be scraped. For the shortlisted players, public reporting is summarised on the youth cards and labelled lower-resolution; it does not enter the projections.