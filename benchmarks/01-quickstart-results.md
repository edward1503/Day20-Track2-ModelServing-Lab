# 01 — Quickstart Results

Settings: `n_threads=4`, `n_ctx=2048`, `n_batch=512`, `n_gpu_layers=99`.

| Model | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode rate (tok/s) |
|---|---:|---:|---:|---:|---:|
| tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf | 764 | 143 / 172 | 32.6 / 72.3 | 2166 / 2226 / 2234 | 30.6 |
| tinyllama-1.1b-chat-v1.0.Q2_K.gguf | 161 | 222 / 318 | 30.5 / 32.8 | 2084 / 2280 / 2315 | 32.8 |

## Observations

- TTFT is the prefill cost. With short prompts this is small; with long prompts it dominates.
- TPOT is per-token decode latency. The decode rate is `1000 / TPOT_p50`.
- The bigger quantization (Q4_K_M) is usually only ~30–60% slower than Q2_K but produces noticeably better text. Q2_K is for *truly* tight RAM.
- `n_threads = physical_cores` is usually best on CPU. Hyperthreading (`logical_cores`) often hurts because the work is bandwidth-bound.

Add png here