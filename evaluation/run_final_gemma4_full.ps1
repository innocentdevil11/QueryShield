$ErrorActionPreference = 'Stop'
Set-Location 'c:\Users\Asus\TextToSQL'
$env:LLM_PROVIDER = 'ollama'
$env:OLLAMA_MODEL = 'gemma4:e4b'
python -m queryshield.evaluation.spider_runner --dataset-json queryshield/data/spider2/spider2_local_subset.json --db-root queryshield/data/spider2/local_sqlite_dbs --num-dbs 16 --num-queries 24 --llm-timeout-seconds 300 --api-max-retries 2 --api-recovery-rounds 2 --api-recovery-cooldown-seconds 20 --max-correction-retries 2 --max-semantic-retries 1 --max-plan-validation-attempts 3 --throttle-seconds 0 --output queryshield/evaluation/results/spider2_ollama_gemma4e4b_planenforced_full_24q_final.json
