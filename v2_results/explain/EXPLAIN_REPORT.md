# What drives pressure performance, player types, matchups (S4E)

## Top predictors of next-season pressure run value: batters

| feature       | meaning                                             |   mean_abs_shap | effect           |
|:--------------|:----------------------------------------------------|----------------:|:-----------------|
| M4_eb_overall | overall run value (all situations, RR pack, shrunk) |          0.0412 | higher -> better |
| rv_setting    | run value setting a total                           |          0.0255 | higher -> worse  |
| pub_n         | balls in other leagues                              |          0.0247 | higher -> better |
| gap_eb        | pressure-minus-normal gap (shrunk)                  |          0.0243 | higher -> worse  |
| dot_pct       | dot %                                               |          0.0232 | higher -> worse  |
| rv_Death      | run value at the death                              |          0.0211 | higher -> worse  |
| rv_chasing    | run value chasing                                   |          0.0192 | higher -> better |
| rv_vs_spin    | run value vs spin                                   |          0.0187 | higher -> worse  |

## Top predictors of next-season pressure run value: bowlers

| feature       | meaning                                                    |   mean_abs_shap | effect           |
|:--------------|:-----------------------------------------------------------|----------------:|:-----------------|
| econ          | economy                                                    |          0.0428 | higher -> worse  |
| dot_rate      | dot-ball rate                                              |          0.0171 | higher -> better |
| rv_Death      | run value at the death                                     |          0.017  | higher -> better |
| rv_chasing    | run value chasing                                          |          0.0169 | higher -> better |
| age           | age                                                        |          0.0162 | higher -> better |
| p_n           | pressure balls seen                                        |          0.0153 | higher -> worse  |
| M4_eb_overall | overall run value (all situations, RR pack, shrunk)        |          0.0146 | higher -> better |
| M6_apm        | opponent/competition-adjusted skill from all leagues (APM) |          0.0134 | higher -> better |

Out-of-time check of the profile LightGBM (train on earlier folds, test on the next):

|                                          |   wcorr |   spearman |
|:-----------------------------------------|--------:|-----------:|
| ('bat', 'LightGBM on profile features')  |   0.029 |      0.035 |
| ('bat', 'M8_bayes (s12)')                |   0.2   |      0.153 |
| ('bowl', 'LightGBM on profile features') |   0.164 |      0.166 |
| ('bowl', 'M8_bayes (s12)')               |   0.229 |      0.243 |

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
| ('LHB', 'Left-arm Chinaman')      |    -5.6 |    -13.9 |   5.4 |
| ('LHB', 'Left-arm Fast')          |     7   |     -1.1 |   3.5 |
| ('LHB', 'Left-arm fast-medium')   |    -7.2 |      5.8 |  -7.3 |
| ('LHB', 'Left-arm medium')        |    -3.5 |     -3.6 |  -1   |
| ('LHB', 'Left-arm medium-fast')   |    -2.1 |     -0.3 |   8.2 |
| ('LHB', 'Right-arm Fast')         |     6.5 |     -5.8 |   1.3 |
| ('LHB', 'Right-arm Leg-Break')    |   -12.2 |     -0.7 |   0.6 |
| ('LHB', 'Right-arm fast-medium')  |     2.7 |      0.6 |   0.4 |
| ('LHB', 'Right-arm medium')       |     6   |      4.6 |   0.3 |
| ('LHB', 'Right-arm medium-fast')  |     4.5 |     -1.6 |   4.7 |
| ('LHB', 'Right-arm offbreak')     |    -1.3 |     -6.5 |  -7.3 |
| ('LHB', 'Slow left-arm orthodox') |    -9   |      9.1 |  13.8 |
| ('RHB', 'Left-arm Chinaman')      |   -13.3 |     -8.6 |  -1.9 |
| ('RHB', 'Left-arm Fast')          |   -12   |      6.4 |   6   |
| ('RHB', 'Left-arm fast-medium')   |     5.6 |      9.8 |  -0.1 |
| ('RHB', 'Left-arm medium')        |     4.1 |      2   |  -3.9 |
| ('RHB', 'Left-arm medium-fast')   |     6.5 |      5.4 |  -0.7 |
| ('RHB', 'Right-arm Fast')         |     4.9 |      2.4 |  -3.4 |
| ('RHB', 'Right-arm Leg-Break')    |    -7.5 |      0.7 | -14.9 |
| ('RHB', 'Right-arm fast-medium')  |    -1.2 |      7.5 |  -3.6 |
| ('RHB', 'Right-arm medium')       |     5.9 |      6.8 |   1.9 |
| ('RHB', 'Right-arm medium-fast')  |     4.8 |      1   |   5.1 |
| ('RHB', 'Right-arm offbreak')     |    -9.7 |      1.7 |   1.3 |
| ('RHB', 'Slow left-arm orthodox') |     5.3 |    -11.6 |  -5.3 |

Are player-specific matchup gaps real? Split-half reliability (odd/even matches, Spearman-Brown):

| effect                                         |   reliability |   players |
|:-----------------------------------------------|--------------:|----------:|
| batter: spin minus pace                        |         0.443 |       208 |
| batter: left-arm minus right-arm bowling       |        -0.091 |       133 |
| bowler: vs left-handers minus vs right-handers |         0.178 |       210 |

- Reliability near zero means an individual player's apparent matchup weakness is mostly noise at this sample size; scout cards only call out a player matchup when it is large AND the reliability of that effect type is meaningful.