# QueryShield Master Test Results Report

Generated on: 2026-05-03

This file consolidates **all benchmark/test result files discovered** in `queryshield/evaluation`, including:

1. Custom hard-query benchmarks
2. Fair same-prompt comparisons
3. Spider2 cloud/balanced/plan-based runs
4. Strict plan-enforced runs
5. Archive validation-layer experiments
6. Partial/in-progress runs

## 1) Global Summary

- Total result artifacts analyzed: **31**
- Completed artifacts: **28**
- Partial/In-progress artifacts: **3**
- Same-prompt fair artifacts: **7**
- Plan-based / plan-enforced artifacts: **5**
- Best completed system accuracy: **0.6538** in `queryshield/evaluation/results_mistral_all_fair.json`
- Lowest completed system accuracy: **0** in `queryshield/evaluation/spider2_ollama_planenforced_smoke_1q.json`

## 2) Run Registry (All Tests)

| File | Family | Fairness/Policy | Status | PlannedQ | DoneQ | BaselineAcc | SystemAcc | Improvement% | BExec | SExec | API Failures | Retry Success | Semantic Success | Plan Quality | Plan Validation Failures | Plan Correction Success | Runtime Total(s) | Runtime Avg(s) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `queryshield/evaluation/spider2_ollama_planenforced_24q.json` | spider2 | plan_enforced_system_vs_baseline | in_progress | 24 | 2 | 0.5 | 0.5 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 4937.072 | 2468.536 |
| `queryshield/evaluation/spider2_ollama_planenforced_smoke_1q.json` | spider2 | plan_enforced_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 809.642 | 809.642 |
| `queryshield/evaluation/spider2_cloud_planenforced_smoke_1q.json` | spider2 | plan_enforced_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0.9 | 0 | 0 | 152.679 | 152.679 |
| `queryshield/evaluation/spider2_cloud_planbased_24q.json` | spider2 | plan_based_system_vs_baseline | completed | 24 | 24 | 0.5 | 0.4167 | -8.33 | 0.8333 | 0.9583 | 0 | 0 | 0 | 1 | - | - | 1017.531 | 42.397 |
| `queryshield/evaluation/spider2_cloud_planbased_smoke_1q.json` | spider2 | plan_based_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | - | - | 64.803 | 64.803 |
| `queryshield/evaluation/spider2_cloud_balanced_24q.json` | spider2 | balanced_spider2_system_vs_baseline | completed | 24 | 24 | 0.5 | 0.5 | 0 | 0.7917 | 0.9583 | 0 | 0 | 0 | - | - | - | 756.399 | 31.517 |
| `queryshield/evaluation/spider2_cloud_smoke_1q.json` | spider2 | standard_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | - | 26.683 | 26.683 |
| `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json` | spider2 | same_prompt_fair | in_progress | 24 | 4 | 0.75 | 0.6667 | -8.33 | 1 | 0.75 | 1 | 0 | 0 | - | - | - | 2354.444 | 588.611 |
| `queryshield/evaluation/spider2_comparator_same_prompt_efficiency_v2.json` | spider2 | same_prompt_fair | completed | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | - | - | - | 8290.149 | 345.423 |
| `queryshield/evaluation/spider2_best_same_prompt_efficiency_v2.json` | spider2 | same_prompt_fair | completed | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | - | - | - | 3333.327 | 138.889 |
| `queryshield/evaluation/spider2_best_same_prompt_efficiency.json` | spider2 | same_prompt_fair | in_progress | 24 | 10 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | - | - | - | 3799.026 | 379.903 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_r3.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.1579 | 0.4375 | 27.96 | 0.375 | 0.5417 | 13 | 0.75 | 0.25 | - | - | - | 1425.77 | 59.407 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_strictvalidator.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.1667 | 0.35 | 18.33 | 0.375 | 0.5833 | 10 | 0.9048 | 0.6667 | - | - | - | 1031.973 | 42.999 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_rerun.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.2 | 0.5 | 30 | 0.4167 | 0.7083 | 8 | 0.9048 | 0.2857 | - | - | - | 997.216 | 41.551 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.2273 | 0.5455 | 31.82 | 0.4583 | 0.4583 | 15 | 0.7 | 0.4286 | - | - | - | 778.28 | 32.428 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_proxyfix.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | - | - | - | 15.494 | 15.494 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_run.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | - | - | - | 795.623 | 33.151 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_r2r1.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 32.754 | 32.754 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 74.942 | 74.942 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_70b.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 74.956 | 74.956 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_retry0.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 4.54 | 4.54 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_after_fix.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 18.606 | 18.606 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile.json` | spider2_archive | validation_layer_system_vs_baseline | completed | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | - | - | - | 37.636 | 37.636 |
| `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_robust.json` | custom_queries | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.2917 | 0.4348 | 14.31 | 0.5417 | 0.7083 | 1 | 1 | - | - | - | - | - | - |
| `queryshield/evaluation/validation_layer_best_20260403_200856/spider2_subset_results.json` | spider2_archive_best | validation_layer_system_vs_baseline | completed | 24 | 24 | 0.25 | 0.5714 | 32.14 | 0.2917 | 0.5833 | 22 | 0.7619 | - | - | - | - | - | - |
| `queryshield/evaluation/groq_hard_results_saved_copy.json` | custom_queries | same_prompt_fair | completed | 20 | 20 | 0.4 | 0.6 | 20 | - | - | 0 | 0 | - | - | - | - | - | - |
| `queryshield/evaluation/groq_hard_results.json` | custom_queries | standard_system_vs_baseline | completed | 20 | 20 | 0.35 | 0.6 | 25 | - | - | 0 | 1 | - | - | - | - | - | - |
| `queryshield/evaluation/results_mistral_all_fair.json` | custom_queries | same_prompt_fair | completed | 26 | 26 | 0.3846 | 0.6538 | 26.92 | - | - | 0 | 0.2727 | - | - | - | - | - | - |
| `queryshield/evaluation/results_groq_all_fair.json` | custom_queries | same_prompt_fair | completed | 26 | 26 | 0.6538 | 0.5385 | -11.54 | - | - | 0 | 1 | - | - | - | - | - | - |
| `queryshield/evaluation/results_mistral_all.json` | custom_queries | standard_system_vs_baseline | completed | 26 | 26 | 0.0769 | 0.6538 | 57.69 | - | - | 0 | 0.2727 | - | - | - | - | - | - |
| `queryshield/evaluation/results_groq_all.json` | custom_queries | standard_system_vs_baseline | completed | 26 | 26 | 0.0769 | 0.5 | 42.31 | - | - | 0 | 0.6667 | - | - | - | - | - | - |

## 3) Partial / In-Progress Runs (with current state)

### `queryshield/evaluation/spider2_ollama_planenforced_24q.json`

- Status: `in_progress`
- Progress: `2/24`
- Current baseline/system accuracy: `0.5/0.5`
- Current runtime avg sec: `2468.536`
- Current failure reason tag: `in_progress (2/24 queries completed)`
- Top observed errors so far: none logged.

### `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json`

- Status: `in_progress`
- Progress: `4/24`
- Current baseline/system accuracy: `0.75/0.6667`
- Current runtime avg sec: `588.611`
- Current failure reason tag: `in_progress (4/24 queries completed)`
- Top observed errors so far:
  - (1x) `api_error: Ollama request failed. Ensure Ollama is running and model is pulled (e.g., `ollama serve` and `ollama pull qwen2.5:3b`).`

### `queryshield/evaluation/spider2_best_same_prompt_efficiency.json`

- Status: `in_progress`
- Progress: `10/24`
- Current baseline/system accuracy: `0/0`
- Current runtime avg sec: `379.903`
- Current failure reason tag: `in_progress (10/24 queries completed)`
- Top observed errors so far:
  - (20x) `api_error: Groq request failed. Check network, API key, and model name.`

## 4) Tests With Major API/Execution Issues and Causes

### `queryshield/evaluation/spider2_cloud_planenforced_smoke_1q.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/spider2_cloud_smoke_1q.json`

- API failures (total): `0`
- Execution success baseline/system: `0/0`
- Inferred cause: `both baseline/system had execution failures; top error: no such column: bs.striker`
- Most frequent concrete error messages:
  - (1x) `no such column: bs.striker`
  - (1x) `no such column: bs.player_id`

### `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json`

- API failures (total): `1`
- Execution success baseline/system: `1/0.75`
- Inferred cause: `in_progress (4/24 queries completed)`
- Most frequent concrete error messages:
  - (1x) `api_error: Ollama request failed. Ensure Ollama is running and model is pulled (e.g., `ollama serve` and `ollama pull qwen2.5:3b`).`

### `queryshield/evaluation/spider2_comparator_same_prompt_efficiency_v2.json`

- API failures (total): `48`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/spider2_best_same_prompt_efficiency_v2.json`

- API failures (total): `48`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/spider2_best_same_prompt_efficiency.json`

- API failures (total): `20`
- Execution success baseline/system: `0/0`
- Inferred cause: `in_progress (10/24 queries completed)`
- Most frequent concrete error messages:
  - (20x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_r3.json`

- API failures (total): `13`
- Execution success baseline/system: `0.375/0.5417`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (13x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (5x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `no such column: T1.name`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_strictvalidator.json`

- API failures (total): `10`
- Execution success baseline/system: `0.375/0.5833`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (10x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (5x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: r.rental_duration`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_rerun.json`

- API failures (total): `8`
- Execution success baseline/system: `0.4167/0.7083`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (8x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (4x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix.json`

- API failures (total): `15`
- Execution success baseline/system: `0.4583/0.4583`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (15x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (3x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `no such column: T1.name`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_run.json`

- API failures (total): `48`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_r2r1.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_70b.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_retry0.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_after_fix.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile.json`

- API failures (total): `2`
- Execution success baseline/system: `0/0`
- Inferred cause: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Most frequent concrete error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_robust.json`

- API failures (total): `1`
- Execution success baseline/system: `0.5417/0.7083`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (6x) `near "FROM": syntax error`
  - (3x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `api_error: Groq request failed. Check network, API key, and model name.`

### `queryshield/evaluation/validation_layer_best_20260403_200856/spider2_subset_results.json`

- API failures (total): `22`
- Execution success baseline/system: `0.2917/0.5833`
- Inferred cause: `completed`
- Most frequent concrete error messages:
  - (22x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (2x) `near "FROM": syntax error`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `ambiguous column name: segment`
  - (1x) `ORDER BY clause should come after UNION ALL not before`

## 5) Fair vs Non-Fair Comparisons

Fairness policy labels used in this report:

1. `same_prompt_fair`: baseline and system explicitly run with same core prompt policy.
2. `plan_based_system_vs_baseline`: baseline remains simple; system uses planning pipeline.
3. `plan_enforced_system_vs_baseline`: system adds strict plan validator/regeneration.
4. `balanced_spider2_system_vs_baseline` and `validation_layer_system_vs_baseline`: benchmark-specific system pipelines.

### Same-Prompt Fair Runs

- `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json` -> BaselineAcc `0.75`, SystemAcc `0.6667`, Improvement% `-8.33`
- `queryshield/evaluation/spider2_comparator_same_prompt_efficiency_v2.json` -> BaselineAcc `0`, SystemAcc `0`, Improvement% `0`
- `queryshield/evaluation/spider2_best_same_prompt_efficiency_v2.json` -> BaselineAcc `0`, SystemAcc `0`, Improvement% `0`
- `queryshield/evaluation/spider2_best_same_prompt_efficiency.json` -> BaselineAcc `0`, SystemAcc `0`, Improvement% `0`
- `queryshield/evaluation/groq_hard_results_saved_copy.json` -> BaselineAcc `0.4`, SystemAcc `0.6`, Improvement% `20`
- `queryshield/evaluation/results_mistral_all_fair.json` -> BaselineAcc `0.3846`, SystemAcc `0.6538`, Improvement% `26.92`
- `queryshield/evaluation/results_groq_all_fair.json` -> BaselineAcc `0.6538`, SystemAcc `0.5385`, Improvement% `-11.54`

## 6) Per-Run Detailed Breakdown

### `queryshield/evaluation/spider2_ollama_planenforced_24q.json`

- Family: `spider2`
- Comparison policy: `plan_enforced_system_vs_baseline`
- Status: `in_progress`
- Planned/Completed queries: `24/2`
- Baseline accuracy: `0.5`
- System accuracy: `0.5`
- Final accuracy (if available): `0.5`
- Improvement percent: `0`
- Baseline execution success rate: `1`
- System execution success rate: `1`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `1`
- Semantic success rate: `0`
- Plan quality avg: `1`
- Plan validation failures: `0`
- Plan correction success rate: `0`
- Runtime total sec: `4937.072`
- Runtime avg sec: `2468.536`
- Failure tag: `in_progress (2/24 queries completed)`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `240`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - max_plan_validation_attempts: `3`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `20`
  - throttle_seconds: `0.0`
- Top error messages: none logged.
- Last modified: `2026-04-12T18:06:02.185735`

### `queryshield/evaluation/spider2_ollama_planenforced_smoke_1q.json`

- Family: `spider2`
- Comparison policy: `plan_enforced_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `0`
- Improvement percent: `0`
- Baseline execution success rate: `1`
- System execution success rate: `1`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `1`
- Plan validation failures: `0`
- Plan correction success rate: `0`
- Runtime total sec: `809.642`
- Runtime avg sec: `809.642`
- Failure tag: `completed`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `240`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - max_plan_validation_attempts: `3`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `20`
  - throttle_seconds: `0.0`
- Top error messages: none logged.
- Last modified: `2026-04-12T16:43:15.163128`

### `queryshield/evaluation/spider2_cloud_planenforced_smoke_1q.json`

- Family: `spider2`
- Comparison policy: `plan_enforced_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `0`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `0.9`
- Plan validation failures: `0`
- Plan correction success rate: `0`
- Runtime total sec: `152.679`
- Runtime avg sec: `152.679`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - max_plan_validation_attempts: `3`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `20`
  - throttle_seconds: `0.0`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-12T16:29:05.911010`

### `queryshield/evaluation/spider2_cloud_planbased_24q.json`

- Family: `spider2`
- Comparison policy: `plan_based_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.5`
- System accuracy: `0.4167`
- Final accuracy (if available): `-`
- Improvement percent: `-8.33`
- Baseline execution success rate: `0.8333`
- System execution success rate: `0.9583`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `1`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `1017.531`
- Runtime avg sec: `42.397`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `20`
  - throttle_seconds: `0.0`
- Top error messages:
  - (1x) `incomplete input`
  - (1x) `no such table: Championships`
  - (1x) `near "ALL": syntax error`
  - (1x) `near "QUALIFY": syntax error`
  - (1x) `near "(": syntax error`
- Stdout log: `queryshield/evaluation/spider2_cloud_planbased_24q.stdout.log`
- Stderr log: `queryshield/evaluation/spider2_cloud_planbased_24q.stderr.log`
- Last modified: `2026-04-12T15:56:09.507581`

### `queryshield/evaluation/spider2_cloud_planbased_smoke_1q.json`

- Family: `spider2`
- Comparison policy: `plan_based_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `1`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `1`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `64.803`
- Runtime avg sec: `64.803`
- Failure tag: `completed`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `0.0`
- Top error messages:
  - (1x) `no such column: bs.striker`
- Last modified: `2026-04-12T15:28:35.392552`

### `queryshield/evaluation/spider2_cloud_balanced_24q.json`

- Family: `spider2`
- Comparison policy: `balanced_spider2_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.5`
- System accuracy: `0.5`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0.7917`
- System execution success rate: `0.9583`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `756.399`
- Runtime avg sec: `31.517`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `1`
  - max_semantic_retries: `0`
  - use_semantic_loop: `True`
  - api_max_retries: `1`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `20`
  - throttle_seconds: `0.0`
- Top error messages:
  - (1x) `no such column: bs.striker`
  - (1x) `no such column: bs.player_id`
  - (1x) `no such column: team_api_id`
  - (1x) `near "ALL": syntax error`
  - (1x) `near "QUALIFY": syntax error`
  - (1x) `near "(": syntax error`
- Stdout log: `queryshield/evaluation/spider2_cloud_balanced_24q.stdout.log`
- Stderr log: `queryshield/evaluation/spider2_cloud_balanced_24q.stderr.log`
- Last modified: `2026-04-12T14:28:37.919277`

### `queryshield/evaluation/spider2_cloud_smoke_1q.json`

- Family: `spider2`
- Comparison policy: `standard_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `26.683`
- Runtime avg sec: `26.683`
- Failure tag: `both baseline/system had execution failures; top error: no such column: bs.striker`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `1`
  - max_semantic_retries: `2`
  - use_semantic_loop: `False`
  - api_max_retries: `0`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `0`
  - throttle_seconds: `0.0`
- Top error messages:
  - (1x) `no such column: bs.striker`
  - (1x) `no such column: bs.player_id`
- Last modified: `2026-04-12T14:12:56.134745`

### `queryshield/evaluation/spider2_gemma4e4b_same_prompt_maxacc.json`

- Family: `spider2`
- Comparison policy: `same_prompt_fair`
- Status: `in_progress`
- Planned/Completed queries: `24/4`
- Baseline accuracy: `0.75`
- System accuracy: `0.6667`
- Final accuracy (if available): `-`
- Improvement percent: `-8.33`
- Baseline execution success rate: `1`
- System execution success rate: `0.75`
- API failures baseline/system/total: `0/1/1`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `2354.444`
- Runtime avg sec: `588.611`
- Failure tag: `in_progress (4/24 queries completed)`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `180`
  - max_correction_retries: `2`
  - max_semantic_retries: `2`
  - use_semantic_loop: `True`
  - api_max_retries: `0`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `0`
  - throttle_seconds: `0.0`
- Top error messages:
  - (1x) `api_error: Ollama request failed. Ensure Ollama is running and model is pulled (e.g., `ollama serve` and `ollama pull qwen2.5:3b`).`
- Last modified: `2026-04-12T13:51:24.695007`

### `queryshield/evaluation/spider2_comparator_same_prompt_efficiency_v2.json`

- Family: `spider2`
- Comparison policy: `same_prompt_fair`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `24/24/48`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `8290.149`
- Runtime avg sec: `345.423`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `60`
  - max_correction_retries: `2`
  - max_semantic_retries: `0`
  - use_semantic_loop: `False`
  - api_max_retries: `2`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `2`
  - throttle_seconds: `2.5`
- Top error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-04T06:15:23.813776`

### `queryshield/evaluation/spider2_best_same_prompt_efficiency_v2.json`

- Family: `spider2`
- Comparison policy: `same_prompt_fair`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `24/24/48`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `3333.327`
- Runtime avg sec: `138.889`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `60`
  - max_correction_retries: `2`
  - max_semantic_retries: `1`
  - use_semantic_loop: `True`
  - api_max_retries: `2`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `2`
  - throttle_seconds: `2.5`
- Top error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-04T03:56:50.163127`

### `queryshield/evaluation/spider2_best_same_prompt_efficiency.json`

- Family: `spider2`
- Comparison policy: `same_prompt_fair`
- Status: `in_progress`
- Planned/Completed queries: `24/10`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `10/10/20`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `3799.026`
- Runtime avg sec: `379.903`
- Failure tag: `in_progress (10/24 queries completed)`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `90`
  - max_correction_retries: `2`
  - max_semantic_retries: `2`
  - use_semantic_loop: `True`
  - api_max_retries: `4`
  - api_recovery_rounds: `3`
  - api_recovery_cooldown_seconds: `2`
  - throttle_seconds: `2.5`
- Top error messages:
  - (20x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-04T03:00:56.171683`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_r3.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.1579`
- System accuracy: `0.4375`
- Final accuracy (if available): `-`
- Improvement percent: `27.96`
- Baseline execution success rate: `0.375`
- System execution success rate: `0.5417`
- API failures baseline/system/total: `5/8/13`
- Retry success rate: `0.75`
- Semantic success rate: `0.25`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `1425.77`
- Runtime avg sec: `59.407`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `3`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (13x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (5x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `no such column: T1.name`
  - (1x) `no such column: T1.team_long_name`
  - (1x) `no such column: bs.player_id`
- Last modified: `2026-04-03T09:56:19.362028`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_strictvalidator.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.1667`
- System accuracy: `0.35`
- Final accuracy (if available): `-`
- Improvement percent: `18.33`
- Baseline execution success rate: `0.375`
- System execution success rate: `0.5833`
- API failures baseline/system/total: `6/4/10`
- Retry success rate: `0.9048`
- Semantic success rate: `0.6667`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `1031.973`
- Runtime avg sec: `42.999`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (10x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (5x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: r.rental_duration`
  - (1x) `unrecognized token: "```sql
SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year,;"`
  - (1x) `no such column: T2.home_team_api_id`
- Last modified: `2026-04-03T09:31:32.338629`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix_rerun.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.2`
- System accuracy: `0.5`
- Final accuracy (if available): `-`
- Improvement percent: `30`
- Baseline execution success rate: `0.4167`
- System execution success rate: `0.7083`
- API failures baseline/system/total: `4/4/8`
- Retry success rate: `0.9048`
- Semantic success rate: `0.2857`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `997.216`
- Runtime avg sec: `41.551`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (8x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (4x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `unrecognized token: "```sql
SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year, primary_collision_factor
ORDER BY 
  db_year, count DESC
LIMIT 1 OFFSET 1

UNION ALL

SELECT 
  db_year,
  primary_collision_factor,
  COUNT(*) as count
FROM 
  case_ids
JOIN 
  collisions ON case_ids.case_id = collisions.case_id
GROUP BY 
  db_year,;"`
  - (1x) `no such column: bs.player_id`
- Last modified: `2026-04-03T09:13:25.103806`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_proxyfix.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.2273`
- System accuracy: `0.5455`
- Final accuracy (if available): `-`
- Improvement percent: `31.82`
- Baseline execution success rate: `0.4583`
- System execution success rate: `0.4583`
- API failures baseline/system/total: `2/13/15`
- Retry success rate: `0.7`
- Semantic success rate: `0.4286`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `778.28`
- Runtime avg sec: `32.428`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (15x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (3x) `near "FROM": syntax error`
  - (2x) `ORDER BY clause should come after UNION ALL not before`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `no such column: T1.name`
  - (1x) `no such column: T1.team_long_name`
  - (1x) `no such column: bs.player_id`
- Last modified: `2026-04-03T08:55:45.746654`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_proxyfix.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `1`
- System execution success rate: `1`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `15.494`
- Runtime avg sec: `15.494`
- Failure tag: `completed`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages: none logged.
- Last modified: `2026-04-03T08:42:19.989815`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_16db_30min_run.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `24/24/48`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `795.623`
- Runtime avg sec: `33.151`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (48x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:41:05.332190`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b_r2r1.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `32.754`
- Runtime avg sec: `32.754`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:25:50.559314`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_8b.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `74.942`
- Runtime avg sec: `74.942`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `45`
  - api_max_retries: `2`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:24:42.539459`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_smoke_70b.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `74.956`
- Runtime avg sec: `74.956`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `60`
  - api_max_retries: `2`
  - api_recovery_rounds: `2`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:22:33.455984`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_retry0.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `4.54`
- Runtime avg sec: `4.54`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `35`
  - api_max_retries: `0`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:14:19.828452`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile_after_fix.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `18.606`
- Runtime avg sec: `18.606`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `35`
  - api_max_retries: `1`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:13:32.835020`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_one_query_profile.json`

- Family: `spider2_archive`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `1/1`
- Baseline accuracy: `0`
- System accuracy: `0`
- Final accuracy (if available): `-`
- Improvement percent: `0`
- Baseline execution success rate: `0`
- System execution success rate: `0`
- API failures baseline/system/total: `1/1/2`
- Retry success rate: `0`
- Semantic success rate: `0`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `37.636`
- Runtime avg sec: `37.636`
- Failure tag: `high API failure load; top error: api_error: Groq request failed. Check network, API key, and model name.`
- Selected DB IDs (1): `IPL`
- Runtime config snapshot:
  - llm_timeout_seconds: `35`
  - api_max_retries: `1`
  - api_recovery_rounds: `1`
  - api_recovery_cooldown_seconds: `5`
  - throttle_seconds: `2.5`
- Top error messages:
  - (2x) `api_error: Groq request failed. Check network, API key, and model name.`
- Last modified: `2026-04-03T08:10:15.552748`

### `queryshield/evaluation/validation_layer_archive_20260403_200856/spider2_subset_results_robust.json`

- Family: `custom_queries`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.2917`
- System accuracy: `0.4348`
- Final accuracy (if available): `-`
- Improvement percent: `14.31`
- Baseline execution success rate: `0.5417`
- System execution success rate: `0.7083`
- API failures baseline/system/total: `0/1/1`
- Retry success rate: `1`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Top error messages:
  - (6x) `near "FROM": syntax error`
  - (3x) `ORDER BY clause should come after UNION ALL not before`
  - (2x) `no such function: YEAR`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `no such column: p.topping_name`
  - (1x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (1x) `no such column: T1.team_long_name`
  - (1x) `no such column: T2.home_team_api_id`
- Last modified: `2026-04-03T04:00:06.203311`

### `queryshield/evaluation/validation_layer_best_20260403_200856/spider2_subset_results.json`

- Family: `spider2_archive_best`
- Comparison policy: `validation_layer_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `24/24`
- Baseline accuracy: `0.25`
- System accuracy: `0.5714`
- Final accuracy (if available): `-`
- Improvement percent: `32.14`
- Baseline execution success rate: `0.2917`
- System execution success rate: `0.5833`
- API failures baseline/system/total: `12/10/22`
- Retry success rate: `0.7619`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Selected DB IDs (16): `IPL, E_commerce, sqlite-sakila, Pagila, modern_data, f1, California_Traffic_Collision, WWE, EU_soccer, Brazilian_E_Commerce, delivery_center, Baseball, education_business, bank_sales_trading, EntertainmentAgency, Db-IMDB`
- Top error messages:
  - (22x) `api_error: Groq request failed. Check network, API key, and model name.`
  - (2x) `near "FROM": syntax error`
  - (1x) `misuse of aggregate function COUNT()`
  - (1x) `ambiguous column name: segment`
  - (1x) `ORDER BY clause should come after UNION ALL not before`
- Last modified: `2026-04-03T03:35:43.418974`

### `queryshield/evaluation/groq_hard_results_saved_copy.json`

- Family: `custom_queries`
- Comparison policy: `same_prompt_fair`
- Status: `completed`
- Planned/Completed queries: `20/20`
- Baseline accuracy: `0.4`
- System accuracy: `0.6`
- Final accuracy (if available): `-`
- Improvement percent: `20`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `0`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (6x) `no such column: s.name`
  - (1x) `no such column: s.email`
  - (1x) `no such column: s.student_name`
  - (1x) `no such column: s.department`
  - (1x) `no such column: s.marks`
- Last modified: `2026-04-03T02:56:35.148731`

### `queryshield/evaluation/groq_hard_results.json`

- Family: `custom_queries`
- Comparison policy: `standard_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `20/20`
- Baseline accuracy: `0.35`
- System accuracy: `0.6`
- Final accuracy (if available): `-`
- Improvement percent: `25`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `0/0/0`
- Retry success rate: `1`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (4x) `no such column: s.name`
  - (2x) `no such column: s.email`
  - (1x) `no such column: s.department`
  - (1x) `no such column: s.marks`
  - (1x) `misuse of window function LAG()`
- Last modified: `2026-04-03T02:39:00.884089`

### `queryshield/evaluation/results_mistral_all_fair.json`

- Family: `custom_queries`
- Comparison policy: `same_prompt_fair`
- Status: `completed`
- Planned/Completed queries: `26/26`
- Baseline accuracy: `0.3846`
- System accuracy: `0.6538`
- Final accuracy (if available): `-`
- Improvement percent: `26.92`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `-/-/0`
- Retry success rate: `0.2727`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (10x) `no such column: s.marks`
  - (3x) `no such column: s.name`
  - (2x) `Blocked by safety layer: Safe mode allows only SELECT queries.`
  - (1x) `no such column: s.student_name`
  - (1x) `Blocked by safety layer: Blocked keyword detected: DROP`
  - (1x) `no such column: s.scores.marks`
  - (1x) `ambiguous column name: s.id`
  - (1x) `no such column: scores.marks`
- Last modified: `2026-04-01T06:11:10.944381`

### `queryshield/evaluation/results_groq_all_fair.json`

- Family: `custom_queries`
- Comparison policy: `same_prompt_fair`
- Status: `completed`
- Planned/Completed queries: `26/26`
- Baseline accuracy: `0.6538`
- System accuracy: `0.5385`
- Final accuracy (if available): `-`
- Improvement percent: `-11.54`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `-/-/0`
- Retry success rate: `1`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (16x) `SQL generation failed: Groq request failed. Check network, API key, and model name.`
  - (2x) `Blocked by safety layer: Safe mode allows only SELECT queries.`
  - (1x) `near "INTO": syntax error`
  - (1x) `no such column: s.name`
- Last modified: `2026-04-01T05:58:30.823519`

### `queryshield/evaluation/results_mistral_all.json`

- Family: `custom_queries`
- Comparison policy: `standard_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `26/26`
- Baseline accuracy: `0.0769`
- System accuracy: `0.6538`
- Final accuracy (if available): `-`
- Improvement percent: `57.69`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `-/-/0`
- Retry success rate: `0.2727`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (6x) `no such column: student_name`
  - (3x) `no such column: s.marks`
  - (3x) `no such table: enrollments`
  - (2x) `no such column: marks`
  - (2x) `Blocked by safety layer: Safe mode allows only SELECT queries.`
  - (1x) `no such table: student_scores`
  - (1x) `table students has no column named student_id`
  - (1x) `no such column: is_temporary`
- Last modified: `2026-04-01T05:40:18.324951`

### `queryshield/evaluation/results_groq_all.json`

- Family: `custom_queries`
- Comparison policy: `standard_system_vs_baseline`
- Status: `completed`
- Planned/Completed queries: `26/26`
- Baseline accuracy: `0.0769`
- System accuracy: `0.5`
- Final accuracy (if available): `-`
- Improvement percent: `42.31`
- Baseline execution success rate: `-`
- System execution success rate: `-`
- API failures baseline/system/total: `-/-/0`
- Retry success rate: `0.6667`
- Semantic success rate: `-`
- Plan quality avg: `-`
- Plan validation failures: `-`
- Plan correction success rate: `-`
- Runtime total sec: `-`
- Runtime avg sec: `-`
- Failure tag: `completed`
- Top error messages:
  - (17x) `SQL generation failed: Groq request failed. Check network, API key, and model name.`
  - (2x) `no such column: score`
  - (2x) `no such column: marks`
  - (2x) `no such column: student_name`
  - (2x) `Blocked by safety layer: Safe mode allows only SELECT queries.`
  - (2x) `no such table: marks`
  - (1x) `no such table: course`
  - (1x) `no such column: s.student_name`
- Last modified: `2026-04-01T05:30:44.650627`

## 7) Final Notes Before Full Final Run

1. This report includes completed and partial runs and explicitly calls out API/error-driven failure signatures.
2. For partial runs, the metrics shown are current snapshot metrics, not final project metrics.
3. A fresh full-run output should be written to a new file path to preserve historical reproducibility.

## 8) Final Full Run Execution (Completed After Report Generation)

Final run file:

- `queryshield/evaluation/spider2_ollama_gemma4e4b_planenforced_full_24q_final.json`

Run profile used:

1. Model/provider: `ollama` + `gemma4:e4b`
2. Dataset: Spider2 local subset (`16 DBs`, `24 queries`)
3. Pipeline: `plan_enforced_system_vs_baseline`
4. Timeout: `300s`
5. `max_correction_retries=2`
6. `max_semantic_retries=1`
7. `max_plan_validation_attempts=3`
8. `api_max_retries=2`
9. `api_recovery_rounds=2`
10. `throttle_seconds=0`

Final metrics:

1. `total_queries=24`
2. `baseline_accuracy=0.5455`
3. `system_accuracy=0.4167`
4. `final_accuracy=0.4167`
5. `improvement_percent=-12.88`
6. `baseline_execution_success_rate=0.4583`
7. `system_execution_success_rate=0.4583`
8. `api_failures=25` (`baseline_api_rows=13`, `system_api_rows=12`)
9. `total_runtime_sec=14561.185`
10. `avg_query_runtime_sec=606.716`
11. `plan_quality_avg=0.9458`
12. `plan_validation_failures=4`
13. `plan_correction_success_rate=1.0`
14. `semantic_corrections_used=3`
15. `semantic_success_rate=0.6667`

Failure/error breakdown for this run:

1. Baseline classifications: `api_error=13`, `wrong_results=5`, `success=6`
2. System classifications: `api_error=12`, `wrong_results=6`, `success=5`, `incorrect_sql=1`
3. Dominant concrete error:
   - `25x` `api_error: Ollama request failed. Ensure Ollama is running and model is pulled (e.g., ollama serve / ollama pull ...)`
4. Secondary SQL error:
   - `1x` `ORDER BY clause should come after UNION ALL not before`
