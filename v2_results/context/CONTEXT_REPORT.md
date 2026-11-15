# Match context build (S2.6)

- Venues: RR venue ids named via paired matches: 93 of 98 (vote share >= 0.6); the rest keep an RR-only key. Cricsheet distinct venue names 298 -> keys 311 after normalisation and 26 known renames.
- Cricsheet knockouts identified: 399 matches. IPL by season: {2019: 4, 2020: 4, 2021: 4, 2022: 4, 2023: 4, 2024: 4, 2025: 4, 2026: 4} (expected 4 per season: Q1, Eliminator, Q2, Final).
- IPL qualification stakes (Monte Carlo, 4000 sims/match, coin-flip remaining results): league-game median 0.20; last 14 league games: share with stakes < 0.05 (dead rubber for that team) = 47%, share with stakes > 0.5 = 10%. Playoff games set to 1.0.
- Rain: 34 RR matches have reduced overs (the audit count); 23 have a revised target (the baseline/report count). The 11 in between are 9 no-result/abandoned games (no chase) plus 2 completed games with a shortened first innings and no recorded target: rr16753: target nan, chase balls 66.0; rr19959: target 132.0, chase balls 66.0. The baseline treated these as a full 120-ball chase of first-innings total + 1.

## Dew check (IPL 2022-26, RR pack): economy by innings and day/night

| pace_spin   | day_night   |   innings |   balls |   econ |   wkts_per_24 |
|:------------|:------------|----------:|--------:|-------:|--------------:|
| Pace        | day         |         1 |    5044 |   9.76 |          1.2  |
| Pace        | day         |         2 |    4490 |   9.41 |          1.14 |
| Pace        | night       |         1 |   23287 |   9.59 |          1.27 |
| Pace        | night       |         2 |   20907 |   9.48 |          1.29 |
| Spin        | day         |         1 |    2976 |   8.46 |          1.02 |
| Spin        | day         |         2 |    2998 |   8.6  |          1.23 |
| Spin        | night       |         1 |   12202 |   8.53 |          1.04 |
| Spin        | night       |         2 |   11838 |   8.51 |          1.14 |

## Impact Player era: first-innings runs scored after over 10, by wickets already lost (0 = pre-2023, 1 = 2023+)

|   wkts_before |   ('mean', 0) |   ('mean', 1) |   ('size', 0) |   ('size', 1) |
|--------------:|--------------:|--------------:|--------------:|--------------:|
|             0 |         102.3 |         105.4 |            18 |            25 |
|             1 |          96.8 |         111.9 |            71 |            55 |
|             2 |          92.6 |         104.7 |            83 |            85 |
|             3 |          92.7 |          96.9 |            41 |            65 |
|             4 |          83.9 |          89.7 |            31 |            38 |
|             5 |          57.3 |          79   |             7 |            18 |
|             6 |          41.2 |          37.2 |             4 |             6 |