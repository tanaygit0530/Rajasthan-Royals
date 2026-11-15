# What drives pressure performance, player types, matchups (S4E)

## Top predictors of next-season pressure run value: batters

| feature       | meaning                                                    |   mean_abs_shap | effect           |
|:--------------|:-----------------------------------------------------------|----------------:|:-----------------|
| gap_eb        | pressure-minus-normal gap (shrunk)                         |          0.0508 | higher -> worse  |
| rv_chasing    | run value chasing                                          |          0.0266 | higher -> better |
| M4_eb_overall | overall run value (all situations, RR pack, shrunk)        |          0.0256 | higher -> better |
| rv_setting    | run value setting a total                                  |          0.0251 | higher -> worse  |
| dot_pct       | dot %                                                      |          0.0232 | higher -> worse  |
| pub_n         | balls in other leagues                                     |          0.0202 | higher -> better |
| p_n           | pressure balls seen                                        |          0.015  | higher -> worse  |
| M6_apm        | opponent/competition-adjusted skill from all leagues (APM) |          0.0146 | higher -> better |

## Top predictors of next-season pressure run value: bowlers

| feature    | meaning                                                    |   mean_abs_shap | effect           |
|:-----------|:-----------------------------------------------------------|----------------:|:-----------------|
| econ       | economy                                                    |          0.024  | higher -> worse  |
| rv_chasing | run value chasing                                          |          0.0201 | higher -> better |
| M6_apm     | opponent/competition-adjusted skill from all leagues (APM) |          0.02   | higher -> better |
| p_n        | pressure balls seen                                        |          0.0197 | higher -> worse  |
| rv_vs_rhb  | run value vs right-handers                                 |          0.0196 | higher -> better |
| rv_Death   | run value at the death                                     |          0.0172 | higher -> better |
| wkt_rate   | wicket rate                                                |          0.0171 | higher -> worse  |
| gap_eb     | pressure-minus-normal gap (shrunk)                         |          0.0147 | higher -> worse  |

Out-of-time check of the profile LightGBM (train on earlier folds, test on the next):

|                                          |   wcorr |   spearman |
|:-----------------------------------------|--------:|-----------:|
| ('bat', 'LightGBM on profile features')  |   0.077 |      0.141 |
| ('bat', 'M8_bayes (s12)')                |   0.209 |      0.154 |
| ('bowl', 'LightGBM on profile features') |   0.091 |      0.146 |
| ('bowl', 'M8_bayes (s12)')               |   0.202 |      0.204 |

- SHAP is descriptive: it shows what the profile model leans on. Ratings use the model that predicts best out of time (s12).

## Player types: batters (k = 4; >= 500 career balls)

|   cluster |     sr |   bdry |   dot |   bpd |   pos |   share_PP |   share_Middle |   share_Death |   n | label                 |
|----------:|-------:|-------:|------:|------:|------:|-----------:|---------------:|--------------:|----:|:----------------------|
|         0 | 138.46 |  19.54 | 39.01 |  3.01 |  1.93 |       0.57 |           0.37 |          0.06 | 247 | top-order aggressive  |
|         1 | 130.12 |  15.56 | 34.81 |  3.05 |  4.25 |       0.21 |           0.59 |          0.2  | 292 | middle-order balanced |
|         2 | 135.32 |  16.57 | 36.2  |  2.71 |  6.51 |       0.08 |           0.47 |          0.46 | 118 | finisher balanced     |
|         3 | 107.39 |  12.6  | 44.72 |  3.02 |  2.9  |       0.42 |           0.47 |          0.11 | 142 | top-order accumulator |

## Player types: bowlers (k = 3; >= 500 career balls)

|   cluster |   econ |   sr |   dot |   bdry |   share_PP |   share_Middle |   share_Death |   n | label                        |
|----------:|-------:|-----:|------:|-------:|-----------:|---------------:|--------------:|----:|:-----------------------------|
|         0 |   8.64 | 2.87 | 38.8  |  19.11 |       0.41 |           0.3  |          0.28 | 375 | new-ball + death expensive   |
|         1 |   7.58 | 3.05 | 35.3  |  13.58 |       0.17 |           0.72 |          0.12 | 272 | middle-overs average-economy |
|         2 |   6.45 | 2.88 | 48.58 |  12.2  |       0.43 |           0.38 |          0.19 | 180 | new-ball economical          |

## Matchups (RR pack)

League-wide run value per 100 balls for the batter vs the average ball (shrunk, k = 400), by batting hand x bowling type x phase:

|                                   |   Death |   Middle |    PP |
|:----------------------------------|--------:|---------:|------:|
| ('LHB', 'Left-arm Chinaman')      |    -5.8 |    -14   |   5.4 |
| ('LHB', 'Left-arm Fast')          |     6.8 |     -1   |   3.7 |
| ('LHB', 'Left-arm fast-medium')   |    -7.3 |      5.6 |  -7.6 |
| ('LHB', 'Left-arm medium')        |    -3.1 |     -3.5 |  -1   |
| ('LHB', 'Left-arm medium-fast')   |    -2.3 |     -0   |   8.1 |
| ('LHB', 'Right-arm Fast')         |     6.6 |     -5.7 |   1.2 |
| ('LHB', 'Right-arm Leg-Break')    |   -12.5 |     -0.6 |   0.7 |
| ('LHB', 'Right-arm fast-medium')  |     2.7 |      0.8 |   0.3 |
| ('LHB', 'Right-arm medium')       |     6.1 |      4.6 |   0.3 |
| ('LHB', 'Right-arm medium-fast')  |     4.4 |     -1.5 |   4.8 |
| ('LHB', 'Right-arm offbreak')     |    -1.2 |     -6.5 |  -7.1 |
| ('LHB', 'Slow left-arm orthodox') |    -9.1 |      9.1 |  13.8 |
| ('RHB', 'Left-arm Chinaman')      |   -13.4 |     -8.5 |  -2   |
| ('RHB', 'Left-arm Fast')          |   -12.3 |      6.8 |   6.2 |
| ('RHB', 'Left-arm fast-medium')   |     5.3 |      9.9 |  -0.4 |
| ('RHB', 'Left-arm medium')        |     4.4 |      2.2 |  -3.9 |
| ('RHB', 'Left-arm medium-fast')   |     6.6 |      5.7 |  -0.9 |
| ('RHB', 'Right-arm Fast')         |     4.9 |      2.5 |  -3.6 |
| ('RHB', 'Right-arm Leg-Break')    |    -7.7 |      0.9 | -15   |
| ('RHB', 'Right-arm fast-medium')  |    -1.4 |      7.7 |  -3.8 |
| ('RHB', 'Right-arm medium')       |     6   |      6.8 |   1.7 |
| ('RHB', 'Right-arm medium-fast')  |     4.8 |      0.9 |   5   |
| ('RHB', 'Right-arm offbreak')     |    -9.8 |      1.7 |   1.1 |
| ('RHB', 'Slow left-arm orthodox') |     5.5 |    -11.6 |  -5.1 |

Are player-specific matchup gaps real? Split-half reliability (odd/even matches, Spearman-Brown):

| effect                                         |   reliability |   players |
|:-----------------------------------------------|--------------:|----------:|
| batter: spin minus pace                        |         0.444 |       208 |
| batter: left-arm minus right-arm bowling       |        -0.092 |       133 |
| bowler: vs left-handers minus vs right-handers |         0.17  |       210 |

- Reliability near zero means an individual player's apparent matchup weakness is mostly noise at this sample size; scout cards only call out a player matchup when it is large AND the reliability of that effect type is meaningful.