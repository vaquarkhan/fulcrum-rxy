# Real-AWS production validation harness

Deploys a randomized 36-boundary Lambda estate, measures E/S/L and independent outcomes
(latency, errors, cost), and replicates the study. See `VALIDATION-REPORT.md` for results.

```bash
python gen_git_history.py          # S from co-change model -> s_scores.csv
python deploy_population.py        # deploy 36 boundaries to Lambda
python run_study.py                # measure + score (feature_table.csv, RESULTS.md)
python replicate_study.py --reps 5 # replicated AUC + aggregate_results.json
python make_aws_figure.py          # figures/figure10_aws_validation.png
python teardown_all.py             # delete all AWS resources when done
```

Use a dev AWS account with least-privilege credentials. Never commit account IDs or credentials.
