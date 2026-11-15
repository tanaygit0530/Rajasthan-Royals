# Win-probability model comparison (S4A)

Rolling season-ahead folds: train on all sources up to season c, test on RR-pack balls of season c+1 (c = 2022..2025), mean over the four folds. ECE = expected calibration error over 10 probability bins.

|   innings | model               |   logloss |   brier |    auc |    ECE |
|----------:|:--------------------|----------:|--------:|-------:|-------:|
|         1 | logistic            |    0.6344 |  0.221  | 0.7039 | 0.0348 |
|         1 | lightgbm            |    0.6568 |  0.228  | 0.6914 | 0.066  |
|         1 | B0_feats_all_data   |    0.6661 |  0.232  | 0.6784 | 0.0533 |
|         1 | blend_gbm           |    0.683  |  0.2365 | 0.6826 | 0.0869 |
|         1 | B0_baseline_replica |    0.6949 |  0.2377 | 0.6766 | 0.0801 |
|         1 | xgboost             |    0.6999 |  0.2399 | 0.6848 | 0.0974 |
|         1 | hgb                 |    0.7151 |  0.2446 | 0.6692 | 0.095  |
|         2 | logistic            |    0.4019 |  0.1306 | 0.8996 | 0.0205 |
|         2 | B0_feats_all_data   |    0.4198 |  0.1368 | 0.8942 | 0.0396 |
|         2 | hgb                 |    0.4451 |  0.1426 | 0.8856 | 0.0425 |
|         2 | blend_gbm           |    0.4539 |  0.1449 | 0.8836 | 0.0536 |
|         2 | xgboost             |    0.4628 |  0.1464 | 0.8818 | 0.0563 |
|         2 | B0_baseline_replica |    0.4633 |  0.143  | 0.8892 | 0.0584 |
|         2 | lightgbm            |    0.487  |  0.1552 | 0.8718 | 0.0737 |

- Chosen (lowest log-loss; a simpler family wins if within 0.001): first innings **logistic**, chase **logistic**.
- `B0_baseline_replica` = the baseline's feature set and model class trained on the RR pack only; `B0_feats_all_data` = same features trained on RR + Cricsheet. The gap between B0 and the chosen model is the value of the v2 context features (par/era, venue, Elo) and the public data.
- Note: the baseline's own first-innings WP was a composite (resources model -> projected target -> chase WP); the replica uses a direct classifier on its features, so the first-innings comparison is approximate.