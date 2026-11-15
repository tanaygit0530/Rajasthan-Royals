# Baseline (v1) vs v2

| | v1 baseline | v2 |
|---|---|---|
| Data | RR pack only | RR pack + 1.6M public balls (prior, validation, competition strength) |
| Win probability | HGB, tier + is_ipl features, in-sample check | logistic with era, venue, Elo; 4 season-ahead folds |
| Pressure | leverage with phase-average outcome mix, x1.2 knockouts | leverage with situation-specific outcome mix; 7 definitions compared |
| Opposition / league | hand-set tiers 1 / 0.75 / 0.4 | ridge model of competition, venue, opponents with bootstrap SEs |
| Rating | weighted sum of 5 components, hand-set weights | hierarchical Bayes posterior; weights learned; intervals and P(top 10) |
| Validated on future seasons | no | yes; v1 formula correlation -0.02 (bat) / -0.12 (bowl) vs v2 ~0.19 / 0.24 |
| Clutch | rewarded (15% weight on pressure-vs-normal delta) | tested; not repeatable; not rewarded |

## Batters

|   baseline_rank | player               |   v2_rank |
|----------------:|:---------------------|----------:|
|               1 | Vaibhav Sooryavanshi |         1 |
|               2 | Tim David            |         2 |
|               3 | Phil Salt            |         7 |
|               4 | Abhishek Sharma      |         3 |
|               5 | Shreyas Iyer         |        24 |
|               6 | Heinrich Klaasen     |         6 |
|               7 | Yashasvi Jaiswal     |        29 |
|               8 | Reeza Hendricks      |        11 |
|               9 | Virat Kohli          |        44 |
|              10 | Suryakumar Yadav     |         5 |

- New in the v2 top 10: Finn Allen, Nicholas Pooran, Priyansh Arya, Tim Seifert.
- Overlap: 6 of 10.

## Bowlers

|   baseline_rank | player              |   v2_rank |
|----------------:|:--------------------|----------:|
|               1 | Sunil Narine        |         2 |
|               2 | Jasprit Bumrah      |         1 |
|               3 | Varun Chakravarthy  |         5 |
|               4 | Mujeeb Ur Rahman    |         7 |
|               5 | Josh Hazlewood      |        15 |
|               6 | Rashid Khan         |         3 |
|               7 | Mohammad Nawaz      |        33 |
|               8 | Krunal Pandya       |        22 |
|               9 | Matheesha Pathirana |        10 |
|              10 | Mahedi Hasan        |        51 |

- New in the v2 top 10: Wanindu Hasaranga, Noor Ahmad, Abrar Ahmed, Blessing Muzarabani.
- Overlap: 6 of 10.
