# Bonus — GPU-offload sweep

Model: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`  ·  threads: `4`

| -ngl | tg128 (tok/s) |
|--:|--:|
| 0 | 36.0 |
| 8 | 45.7 |
| 16 | 70.6 |
| 24 | 120.0 |
| 32 | 126.9 |
| 99 | 126.1 |

When the model fits in VRAM, `-ngl 99` (full offload) is fastest. When it doesn't, partial offload (`-ngl 16` or `-ngl 24`) keeps the most compute on the GPU while spilling weights to RAM — usually still beats CPU-only (`-ngl 0`). Watch for the curve flattening: after the layer count covers the model's actual depth, more `-ngl` does nothing.
