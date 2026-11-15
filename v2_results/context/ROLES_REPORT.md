# Roles, pressure building, survivorship (S2.8)

- Derived batting position equals the RR batting_order in 99.9% of RR innings (differences: openers swapping ends on ball 1).

## Role counts (players with >= 200 balls faced / bowled, 2022-26)

| bat_role         |   count |
|:-----------------|--------:|
| Middle (4-5)     |     397 |
| Opener           |     391 |
| Finisher (6-7)   |     233 |
| No.3             |     206 |
| Lower order (8+) |      91 |

| bowl_role    |   Pace |   Spin |   nan |
|:-------------|-------:|-------:|------:|
| Death        |      8 |      0 |    19 |
| Middle overs |     19 |    136 |   310 |
| Multi-phase  |    128 |     29 |   255 |
| Powerplay    |    112 |      9 |   300 |

## Pressure building: partner wickets in the next over (OLS, match-clustered SE)

- Overs used: 254,413 (complete overs followed by a different bowler).
- Each extra dot ball this over: +0.0034 partner wickets next over (SE 0.0010); each boundary conceded: -0.0006 (SE 0.0012); a wicket this over: -0.0176 (SE 0.0023).
- Base rate of a wicket in an over: 0.324. A 4-dot over vs a 1-dot over adds +0.0103 expected partner wickets (+3.2% relative).
- Split-half reliability (odd vs even matches, bowlers with >= 40 qualifying overs in each half, n=536): dot/boundary-based credit r = 0.83; bowler-specific "squeeze" residual beyond dots r = 0.02.
- Use: the credit (driven by dots and boundaries) enters S4 as a candidate bowler feature; it is kept only if it improves next-season prediction. A residual near zero reliability means no separate squeeze skill is claimed.

## Survivorship: share of IPL players (>= 60 balls) who play IPL again next season, by quartile, 2019-25

| role                 |   Q1 worst |   Q2 |   Q3 |   Q4 best |
|:---------------------|-----------:|-----:|-----:|----------:|
| batter (strike rate) |       0.75 |  0.9 | 0.92 |      0.94 |
| bowler (economy)     |       0.69 |  0.8 | 0.82 |      0.9  |

- Consequence for S4: the next-season target is missing more often for poor performers (selection on the outcome), so scoring models only on retained players understates how badly any model rates the dropped players. S4 therefore (1) reports dropout by predicted-rating decile for every model, (2) re-scores models with inverse-probability-of-retention weights, and (3) also scores on all-competition next-season balls (players dropped from the IPL often still play T20Is or other leagues).