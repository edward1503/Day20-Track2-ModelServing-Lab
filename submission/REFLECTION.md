# Reflection — Lab 20 (Personal Report)

> **Đây là báo cáo cá nhân.** Mỗi học viên chạy lab trên laptop của mình, với spec của mình. Số liệu của bạn không so sánh được với bạn cùng lớp — chỉ so sánh **before vs after trên chính máy bạn**. Grade rubric tính theo độ rõ ràng của setup + tuning của bạn, không phải tốc độ tuyệt đối.

---

**Họ Tên:** Nguyễn Đôn Đức
**Cohort:** A20-K1
**Ngày submit:** 2026-05-06
**ID:** 2A202600145
---

## 1. Hardware spec (từ `00-setup/detect-hardware.py`)

- **OS:** Windows 11 (AMD64)
- **CPU:** Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz
- **Cores:** 4 physical / 8 logical
- **CPU extensions:** AVX2 (Comet Lake microarchitecture)
- **RAM:** 15.8 GB DDR4
- **Accelerator:** NVIDIA GeForce GTX 1650 with Max-Q Design, 4096 MiB GDDR6
- **llama.cpp backend đã chọn:** CUDA (nhưng Track 01 chạy qua llama-cpp-python CPU wheel)
- **Recommended model tier:** TinyLlama-1.1B (Q4_K_M) — chọn thấp hơn recommended (Qwen2.5-1.5B) vì mạng yếu

**Setup story:** Cài llama.cpp native qua `winget`. llama-cpp-python không build được từ source trên Windows (thiếu MSVC compiler), cài prebuilt CPU wheel thay thế. Script `start-server.ps1` lỗi quoting trên PowerShell 5.1, phải chạy lệnh trực tiếp. Dùng `llama-server` native cho Track 02 để có `/metrics` endpoint (Python wrapper không hỗ trợ Prometheus).

---

## 2. Track 01 — Quickstart numbers (từ `benchmarks/01-quickstart-results.md`)

Settings: `n_threads=4`, `n_ctx=2048`, `n_batch=512`, `n_gpu_layers=99`.

| Model | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode rate (tok/s) |
|---|--:|--:|--:|--:|--:|
| Q4_K_M (637 MB) | 764 | 143 / 172 | 32.6 / 72.3 | 2166 / 2226 / 2234 | 30.6 |
| Q2_K (461 MB)   | 161 | 222 / 318 | 30.5 / 32.8 | 2084 / 2280 / 2315 | 32.8 |

**Một quan sát:** Kết quả bất ngờ — Q2_K decode *nhanh hơn* Q4_K_M (32.8 vs 30.6 tok/s) dù quality kém hơn. Lý do: Q2_K file nhỏ hơn (461 vs 637 MB) → ít bytes cần đọc từ RAM mỗi token → TPOT thấp hơn. Tuy nhiên TTFT của Q2_K cao hơn gấp đôi (222 vs 143 ms) — prefill cần nhiều dequantization compute hơn ở quantization thấp. Với model nhỏ 1.1B này, sự khác biệt decode rate không đáng kể, nhưng quality text của Q2_K tệ hơn rõ rệt. Q4_K_M vẫn là lựa chọn đúng cho production.

---

## 3. Track 02 — llama-server load test

Server: `llama-server` native (winget), TinyLlama-1.1B Q4_K_M, `--parallel 4 --cont-batching --metrics`, `-t 4 -ngl 0` (CPU).

**Raw Locust Output (Concurrency 50):**
```text
Type     Name           50%    66%    75%    80%    90%    95%    98%    99%  99.9% 99.99%   100% # reqs
--------|------------|--------|------|------|------|------|------|------|------|------|------|------|------
POST     long-rag     21000  22000  24000  29000  29000  29000  29000  29000  29000  29000  29000      9
POST     short        24000  29000  33000  33000  35000  37000  37000  37000  37000  37000  37000     20
--------|------------|--------|------|------|------|------|------|------|------|------|------|------|------
         Aggregated   22000  27000  29000  30000  34000  35000  37000  37000  37000  37000  37000     29
```

| Concurrency | Total # reqs | P50 (ms) | P95 (ms) | P99 (ms) | P100 (ms) |
|--:|--:|--:|--:|--:|--:|
| 10 | 29 | 14000 | 20000 | 20000 | 20000 |
| 50 | 29 | 22000 | 35000 | 37000 | 37000 |

**Nhận xét:** Tăng concurrency từ 10 → 50 làm P50 tăng từ 14s lên 22s (~57%) và P95 từ 20s lên 37s (~85%). Với `--parallel 4`, server chỉ xử lý 4 requests đồng thời — 50 users tạo ra hàng đợi dài, tăng latency đáng kể. Throughput (29 requests / 60s ≈ 0.48 RPS) không thay đổi vì server đã bão hòa — thêm users chỉ tăng queuing delay, không tăng output. Đây chính là hiện tượng "throughput at saturation ignores SLO" từ deck.

**KV-cache observation** (từ `record-metrics.py`):

Từ CSV: Peak `llamacpp:kv_cache_usage_ratio` đạt **1.00** (100% capacity) xuyên suốt quá trình test. Điều này khớp hoàn toàn với số slot đang xử lý (`reqs_proc=4`) — với `--parallel 4`, toàn bộ 4/4 slots trong KV Cache đều được lấp đầy liên tục bởi 50 users bắn vào. Hàng đợi request lúc nào cũng có từ 4-6 request phải chờ (`deferred=6`). Peak `tokens_predicted_total` tăng trưởng liên tục đạt > 1200 tokens trong vỏn vẹn 30s lấy mẫu đo.

**Dữ liệu thực tế từ `benchmarks/02-server-metrics.csv` (Trích xuất ngẫu nhiên 7 mẫu trong 30s load test):**

| Thời gian (t) | reqs_proc | deferred | kv_ratio | tok_pred |
|---|---|---|---|---|
| 1778045954.0 | 4.0 | 6.0 | 1.00 | 0.0 |
| 1778045958.4 | 4.0 | 6.0 | 1.00 | 160.0 |
| 1778045962.8 | 4.0 | 6.0 | 1.00 | 279.0 |
| 1778045967.2 | 4.0 | 6.0 | 1.00 | 629.0 |
| 1778045971.5 | 4.0 | 4.0 | 1.00 | 869.0 |
| 1778045975.9 | 4.0 | 5.0 | 1.00 | 1029.0 |
| 1778045980.3 | 4.0 | 6.0 | 1.00 | 1269.0 |

---

## 4. Track 03 — Milestone integration

- **N16 (Cloud/IaC):** stub: localhost only — chạy `llama-server` trực tiếp trên máy, không deploy lên cluster
- **N17 (Data pipeline):** stub: in-memory dict — dùng `TOY_DOCS` hardcoded trong `pipeline.py`
- **N18 (Lakehouse):** stub: không dùng — data là 5 documents cố định trong source code
- **N19 (Vector + Feature Store):** stub: keyword overlap search thay vì vector embedding — hàm `retrieve()` dùng set intersection trên từ, không dùng embedding model hay Qdrant/Feast

**Nơi tốn nhiều ms nhất** trong pipeline (đo bằng `time.perf_counter` trong `pipeline.py`):

- retrieve: ~0.1–0.3 ms (keyword matching cực nhanh)
- llama-server: ~4900–10948 ms (chiếm >99.9% tổng thời gian)
- total: ~4901–10948 ms

**Reflection:** Bottleneck hoàn toàn nằm ở llama-server inference, không phải retrieval. Điều này khớp với kỳ vọng — retrieve chỉ là keyword matching O(N) trên 5 documents, còn LLM decode phải sinh ~200 tokens × ~33ms/token. Nếu dùng vector embedding (sentence-transformers) cho retrieve, embed step sẽ thêm 50–200ms nhưng vẫn không đáng kể so với LLM. Trong production, cách cải thiện là giảm `max_tokens`, dùng model nhỏ hơn, hoặc GPU offload.

---

## 5. Bonus — The single change that mattered most

> **Most important section.** Pick **một** thay đổi đã tạo ra speedup lớn nhất trên máy bạn.

Model: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`  ·  threads: `4`

| -ngl | tg128 (tok/s) |
|--:|--:|
| 0 | 36.0 |
| 8 | 45.7 |
| 16 | 70.6 |
| 24 | 120.0 |
| 32 | 126.9 |
| 99 | 126.1 |

**Change:** Offload toàn bộ model lên GPU (GTX 1650 4GB VRAM) bằng flag `-ngl 99` thay vì chạy CPU-only (`-ngl 0`)

**Before vs after:**

```
before (CPU only, -ngl 0):   36.0 tok/s
after  (full GPU, -ngl 99):  126.1 tok/s
speedup: ~3.5×
```

**Tại sao nó work:**

TinyLlama-1.1B Q4_K_M chỉ ~637MB, fit hoàn toàn trong 4GB VRAM của GTX 1650 Max-Q. Khi `-ngl 0`, quá trình decode phải đọc toàn bộ model weights từ DDR4 RAM qua memory controller của i5-10300H. DDR4-2933 dual-channel cho bandwidth lý thuyết ~42 GB/s (thực tế thường thấp hơn do contention từ OS và các process khác).

Khi `-ngl 99`, decode đọc weights trực tiếp từ GDDR6 trên GPU. GTX 1650 Max-Q có memory bandwidth ~128 GB/s (TDP-limited variant) — gấp ~3× so với CPU RAM bandwidth. Vì LLM decode ở batch-size 1 là hoàn toàn **memory-bandwidth-bound** (mỗi token cần đọc toàn bộ model weights 1 lần qua matrix-vector multiply), speedup lý thuyết tương đương tỉ lệ bandwidth (ở đây speedup thực tế là ~3.5×).

Partial offload (`-ngl 8, 16`) không scale tuyến tính vì activation phải truyền qua bus PCIe 3.0 x16 (~16 GB/s) giữa CPU và GPU sau mỗi boundary layer, tạo thêm overhead. Full offload loại bỏ hoàn toàn chi phí cross-device transfer này.

---

## 6. (Optional) Điều ngạc nhiên nhất

Q2_K decode nhanh hơn Q4_K_M (32.8 vs 30.6 tok/s) trên CPU — ít bytes per weight = ít memory bandwidth cần = nhanh hơn, dù dequantization tốn thêm compute. Điều này minh họa rõ ràng rằng LLM decode thực sự là memory-bandwidth-bound, không phải compute-bound.

---

## 7. Self-graded checklist

- [x] `hardware.json` đã commit
- [x] `models/active.json` đã commit (hoặc paste path snapshot vào section 1)
- [x] `benchmarks/01-quickstart-results.md` đã commit
- [x] `benchmarks/02-server-metrics.csv` (CSV từ `record-metrics.py`) đã commit
- [x] `benchmarks/bonus-*.md` đã commit (ít nhất 1 sweep)
- [x] Ít nhất 6 screenshots trong `submission/screenshots/`
- [ ] `make verify` exit 0 (chạy ngay trước khi push) <!-- TODO: chạy verify cuối cùng -->
- [ ] Repo trên GitHub ở chế độ **public**
- [ ] Đã paste public repo URL vào VinUni LMS

---


