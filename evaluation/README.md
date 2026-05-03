# Evaluation Folder Layout

This folder is organized to keep executable code separate from generated artifacts.

- `*.py`, `*.ps1`: evaluation pipeline code and scripts
- `results/`: benchmark result JSON outputs
- `reports/`: consolidated markdown/json reports
- `runtime_logs/`: JSONL retry/failure/API traces and run stdout/stderr logs
- `archive/`: older snapshot directories retained for reference

Use this pattern for future runs to keep the repository clean.
