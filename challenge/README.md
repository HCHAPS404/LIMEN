# Challenge corpus

Official Tech Sphere Challenge materials are resolved in this order only:

1. `LIMEN_DATASET_PATH` (absolute mount/copy)
2. `./dataset/`
3. `./data/challenge/`
4. unavailable

Do **not** recursively scan the home directory.

```bash
export LIMEN_DATASET_PATH=/absolute/path/to/official/dataset
make verify-llm-bench
```

Expected filenames may include:

- `dataset_final.xlsx`
- `trayectorias_postop_silver.xlsx`
- `perfiles_clinicos_pacientes_silver_contest.xlsx`
- `perfiles_pacientes_co.xlsx`

When discovered, the benchmark records a **fingerprint** (filename, SHA256, row count, columns) for reproducibility. Do not commit ground-truth labels that would leak into runtime prompts. Do not hard-code case IDs into production code.
