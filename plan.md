# Plan — Lab Day 20: Model Serving & Inference Optimization (Track 2)

> **Tổng quan:** Build + tune inference stack với `llama.cpp` trên laptop cá nhân, đo TTFT/TPOT/P50/P95/P99, chạy load test, kết nối RAG pipeline, và viết reflection report.

> **Thời gian ước tính:** Core ~2.5h, Bonus +1–3h.

> **Nền tảng:** Windows + llama.cpp (đã cài qua `winget`). Không cần Docker.

---

## Tổng quan Rubric (100đ Core + 20đ Bonus)

| # | Track | Tiêu chí | Điểm |
|---|---|---|---:|
| 1 | 00-setup | `hardware.json` committed | 5 |
| 2 | 00-setup | `models/active.json` committed, GGUF path hợp lệ | 5 |
| 3 | 01-quickstart | Bảng P50/P95/P99 cho **cả** Q4_K_M và Q2_K | 10 |
| 4 | 01-quickstart | TTFT và TPOT tách riêng (không chỉ E2E) | 5 |
| 5 | 02-server | `llama-server` chạy + `/v1/chat/completions` thành công | 10 |
| 6 | 02-server | `/metrics` có `llamacpp:tokens_predicted_total` > 0 | 5 |
| 7 | 02-server | Locust `-u 10` 60s, P95 reported | 10 |
| 8 | 02-server | Locust `-u 50` 60s, P95 reported | 10 |
| 9 | 02-server | KV-cache peak `kv_cache_usage_ratio` viết trong REFLECTION | 5 |
| 10 | 03-integration | `pipeline.py` chạy e2e (3 queries) + context provenance | 10 |
| 11 | 03-integration | ≥3 piece N16–N19 wired hoặc stubbed có lý do | 5 |
| 12 | submission | REFLECTION.md đã điền — không còn placeholder | 10 |
| 13 | submission | §5 "Single change that mattered most" giải thích WHY | 10 |
| 14 | repo | Reproducibility: `make setup && make bench && make verify` → OK | 10 |
| | | **Tổng Core** | **100** |

---

## TASK 1: Setup Môi Trường (Track 00) — 10đ

### Mục tiêu
Nhận diện phần cứng, cài dependencies, tải model GGUF phù hợp với RAM.

### Các bước thực hiện

**1.1 Tạo virtualenv + cài dependencies**
```powershell
pwsh -ExecutionPolicy Bypass -File 00-setup\windows-setup.ps1
```
Script này sẽ:
- Tạo `.venv/` ở repo root
- Cài `requirements.txt` (huggingface_hub, locust, httpx, matplotlib...)
- Cài `llama-cpp-python` (CPU wheel mặc định trên Windows; nếu có NVIDIA GPU, set `$env:LLAMA_CUDA=1` trước)
- Chạy `detect-hardware.py` → ghi `hardware.json`
- Chạy `download-model.py` → tải 2 file GGUF (Q4_K_M + Q2_K) → ghi `models/active.json`

**Lưu ý (Windows):** Nếu bạn đã cài `llama.cpp` qua `winget`, thì bạn có sẵn `llama-server` native. Tuy nhiên, script setup vẫn cần chạy vì nó cài `llama-cpp-python` (thư viện Python) để Track 01 benchmark dùng.

**1.2 Nếu setup script lỗi, chạy từng bước thủ công:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install llama-cpp-python
python 00-setup\detect-hardware.py
python 00-setup\download-model.py
```

**1.3 Chụp screenshot**
- Chụp terminal khi `detect-hardware.py` chạy xong → lưu `submission/screenshots/01-hardware-probe.png`

### ✅ DoD (Definition of Done) — Task 1
- [ ] File `hardware.json` tồn tại ở repo root, nội dung hợp lệ (có cpu, ram_gb, gpu, recommendation)
- [ ] File `models/active.json` tồn tại, trỏ tới file `.gguf` thực tế trong `models/`
- [ ] File GGUF primary (Q4_K_M) tồn tại trên disk
- [ ] File GGUF compare (Q2_K) tồn tại trên disk
- [ ] Screenshot `submission/screenshots/01-hardware-probe.png` đã lưu
- [ ] `.venv/` hoạt động, `python -c "from llama_cpp import Llama"` không lỗi

---

## TASK 2: Benchmark Quickstart (Track 01) — 15đ

### Mục tiêu
Đo latency baseline với thư viện Python `llama-cpp-python`. So sánh Q4_K_M vs Q2_K.

### Các bước thực hiện

**2.1 Activate venv + chạy benchmark**
```powershell
.\.venv\Scripts\Activate.ps1
python 01-llama-cpp-quickstart\benchmark.py
```

Script `benchmark.py` sẽ:
- Load model Q4_K_M, chạy 10 prompts, đo TTFT/TPOT/E2E cho mỗi prompt
- Load model Q2_K, chạy lại 10 prompts tương tự
- Tính P50/P95/P99 cho mỗi metric
- Ghi kết quả ra `benchmarks/01-quickstart-results.md` + `.json`

**Tunable knobs** (qua biến môi trường):
| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LAB_N_THREADS` | physical cores | Số thread — thử `cores/2`, `cores`, `cores*2` |
| `LAB_N_CTX` | 2048 | Context window |
| `LAB_N_BATCH` | 512 | Prefill batch size |
| `LAB_N_GPU_LAYERS` | auto (99 nếu có GPU) | Số layer offload lên GPU |
| `LAB_MAX_TOKENS` | 64 | Số token tối đa sinh ra |

**2.2 Chụp screenshot**
- Chụp terminal hiển thị bảng kết quả → lưu `submission/screenshots/02-quickstart-bench.png`

**2.3 Sửa file kết quả**
- Mở `benchmarks/01-quickstart-results.md`, thêm quan sát cá nhân ở phần "Observations" (file nhắc bạn edit trước khi submit)

### ✅ DoD — Task 2
- [ ] File `benchmarks/01-quickstart-results.md` tồn tại, có bảng 2 dòng (Q4_K_M + Q2_K)
- [ ] Bảng chứa cột **TTFT P50/P95** và **TPOT P50/P95** (tách riêng, không chỉ E2E)
- [ ] Giá trị hợp lý: TTFT > 0, TPOT > 0
- [ ] File `benchmarks/01-quickstart-results.json` tồn tại (backup data)
- [ ] Screenshot `submission/screenshots/02-quickstart-bench.png` đã lưu
- [ ] Phần "Observations" trong results.md đã được edit với nhận xét cá nhân

---

## TASK 3: HTTP Server + Load Test (Track 02) — 40đ

### Mục tiêu
Chạy `llama-server` với OpenAI-compatible API, scrape Prometheus metrics, chạy load test 10/50 users.

### Các bước thực hiện

**3.1 Khởi động server** (Terminal 1)

Cách A — Dùng `llama-cpp-python` server (luôn hoạt động):
```powershell
.\.venv\Scripts\Activate.ps1
pwsh -ExecutionPolicy Bypass -File 02-llama-cpp-server\start-server.ps1
```

Cách B — Dùng `llama-server` native từ winget (nhanh hơn):
```powershell
# Đọc model path từ active.json
$model = python -c "import json; print(json.load(open('models/active.json'))['primary_model'])"
$threads = python -c "import json; hw=json.load(open('hardware.json')); print(hw['cpu'].get('cores_physical') or 4)"

llama-server -m $model --host 0.0.0.0 --port 8080 -t $threads -ngl 99 --parallel 4 --cont-batching --metrics
```

**3.2 Smoke test** (Terminal 2)
```powershell
.\.venv\Scripts\Activate.ps1
python 02-llama-cpp-server\smoke-test.py
```
- Xác nhận API `/v1/chat/completions` trả về response
- Xác nhận `/metrics` trả về Prometheus text

**3.3 Chụp screenshot server + metrics**
- Chụp terminal server đang chạy + kết quả smoke test → `submission/screenshots/03-server-running.png`
- Đảm bảo screenshot hiển thị `llamacpp:tokens_predicted_total` > 0

**3.4 Load test 10 users** (Terminal 2, server vẫn chạy ở Terminal 1)
```powershell
locust -f 02-llama-cpp-server\load-test.py --headless -u 10 -r 1 -t 1m --host http://localhost:8080
```
- Chụp screenshot bảng kết quả locust → `submission/screenshots/04-locust-10.png`

**3.5 Load test 50 users**
```powershell
locust -f 02-llama-cpp-server\load-test.py --headless -u 50 -r 1 -t 1m --host http://localhost:8080
```
- Chụp screenshot → `submission/screenshots/05-locust-50.png`

**3.6 Record metrics** (chạy đồng thời với locust, Terminal 3)
```powershell
python 02-llama-cpp-server\record-metrics.py --duration 60
```
- Ghi CSV ra `benchmarks/02-server-metrics.csv`
- Quan sát peak `llamacpp:kv_cache_usage_ratio`

**3.7 Knobs để thử (tùy chọn, tăng insight cho REFLECTION):**
| Flag | Thử gì | Đo gì |
|---|---|---|
| `--parallel 1,2,4,8` | Continuous batching width | Throughput thay đổi |
| `--cont-batching` | Bật/tắt | P95 ở -u 50 |
| `--ctx-size 4096` | Context lớn hơn | KV cache usage |
| `--cache-type-k q8_0 --cache-type-v q8_0` | Quantize KV cache | RAM tiết kiệm |

### ✅ DoD — Task 3
- [ ] Server chạy thành công trên `:8080`, phục vụ `/v1/chat/completions`
- [ ] Smoke test pass (200 OK response)
- [ ] `/metrics` trả về data, `llamacpp:tokens_predicted_total` > 0
- [ ] Locust `-u 10` chạy xong 60s, có bảng P50/P95/P99
- [ ] Locust `-u 50` chạy xong 60s, có bảng P50/P95/P99
- [ ] File `benchmarks/02-server-metrics.csv` HOẶC `benchmarks/02-server-results.md` tồn tại
- [ ] Ghi nhận peak `kv_cache_usage_ratio` dưới load
- [ ] Screenshot `03-server-running.png` đã lưu (server log + curl/metrics)
- [ ] Screenshot `04-locust-10.png` đã lưu (P50/P95/P99 visible)
- [ ] Screenshot `05-locust-50.png` đã lưu (P50/P95/P99 visible)

---

## TASK 4: RAG Pipeline Integration (Track 03) — 15đ

### Mục tiêu
Kết nối `llama-server` vào pipeline RAG, chạy 3 queries e2e, hiển thị context provenance.

### Các bước thực hiện

**4.1 Chạy pipeline** (server phải đang chạy ở `:8080`)
```powershell
python 03-milestone-integration\pipeline.py
```

Script `pipeline.py` đã có sẵn skeleton hoạt động được với TOY_DOCS (in-memory data):
- `retrieve(query, k=3)` → STUB: keyword overlap trên TOY_DOCS
- `build_prompt(query, contexts)` → tạo OpenAI messages
- `call_llm(messages)` → POST tới localhost:8080
- `answer(query)` → orchestrate + đo timing

Chạy 3 queries mặc định:
1. "Why is goodput more useful than throughput?"
2. "What problem does PagedAttention actually solve?"
3. "When should I think about disaggregated serving?"

**4.2 (Tùy chọn) Kết nối thật với N16–N19**
Nếu bạn có code từ các lab trước:
- **N19 Vector Store:** Thay `retrieve()` bằng Qdrant/ChromaDB query
- **N18 Lakehouse:** Thay TOY_DOCS bằng data từ Delta Lake/Iceberg
- **N17 Data Pipeline:** Pipeline Airflow produce data
- **N16 Cloud/IaC:** Deploy trên k3d/docker-compose

Nếu chưa có, dùng STUB và ghi rõ lý do trong REFLECTION.md §4.

**4.3 Ghi chú kết quả**
- Copy output terminal (query + context IDs + timings) để paste vào REFLECTION.md §4
- Chụp screenshot → `submission/screenshots/09-pipeline-output.png` (optional nhưng nên có)

### ✅ DoD — Task 4
- [ ] `pipeline.py` chạy e2e không lỗi, in kết quả cho 3 queries
- [ ] Output hiển thị context IDs (provenance) cho mỗi query
- [ ] Output hiển thị timing breakdown (retrieve ms, llm ms, total ms)
- [ ] Xác định rõ phần nào connected thật, phần nào stubbed
- [ ] Kết quả sẵn sàng paste vào REFLECTION.md §4

---

## TASK 5: Viết Báo Cáo + Verify (Submission) — 20đ

### Mục tiêu
Điền đầy đủ REFLECTION.md, lưu screenshots, chạy verify pass.

### Các bước thực hiện

**5.1 Điền `submission/REFLECTION.md`**

File template có 7 sections — điền hết, **không để placeholder**:

| Section | Nội dung cần điền | Nguồn dữ liệu |
|---|---|---|
| §1 Hardware spec | OS, CPU, Cores, RAM, Accelerator, Backend, Model tier | Copy từ `hardware.json` + output `detect-hardware.py` |
| §2 Track 01 numbers | Bảng TTFT/TPOT/P50/P95/P99 cho Q4_K_M + Q2_K, nhận xét | Copy từ `benchmarks/01-quickstart-results.md` |
| §3 Track 02 load test | Bảng RPS/P50/P95/P99 ở concurrency 10 + 50, KV cache observation | Từ output locust + `record-metrics.py` |
| §4 Track 03 integration | Liệt kê N16–N19 pieces (real vs stub), bottleneck analysis | Từ output `pipeline.py` |
| §5 Single change **(QUAN TRỌNG NHẤT)** | Pick 1 thay đổi, before/after numbers, giải thích WHY | Từ bonus sweep hoặc tuning ở Track 02 |
| §6 Điều ngạc nhiên nhất (optional) | 1–2 câu | Cảm nhận cá nhân |
| §7 Self-graded checklist | Tick hết các checkbox | Kiểm tra repo |

**⚠️ §5 là phần grader đọc kỹ nhất (10đ).** Phải có:
- Tên thay đổi cụ thể (vd: "giảm `-t` từ 12 xuống 6 threads")
- Số liệu before/after
- Giải thích tại sao (mental model: memory bandwidth? compute? cache?)
- Không vibes-based — phải bám vào hardware model

**5.2 Kiểm tra screenshots đủ 6 ảnh tối thiểu:**
1. `01-hardware-probe.png` — output detect-hardware
2. `02-quickstart-bench.png` — output benchmark.py
3. `03-server-running.png` — server log + curl /metrics
4. `04-locust-10.png` — locust 10 users summary
5. `05-locust-50.png` — locust 50 users summary
6. `06-bonus-sweep.png` — 1 sweep chart/table từ bonus

**5.3 Chạy verify**
```powershell
python scripts\verify.py
```

Verify script kiểm tra:
- `hardware.json` tồn tại + không rỗng
- `models/active.json` hợp lệ + GGUF file path resolve được
- `benchmarks/01-quickstart-results.md` tồn tại
- `benchmarks/02-server-metrics.csv` HOẶC `02-server-results.md` tồn tại
- `submission/REFLECTION.md` đã edit (< 3 template placeholder còn lại)
- `submission/screenshots/` có ≥ 6 ảnh
- (Optional) llama-server trên :8080 reachable

**5.4 Commit + Push**
```powershell
git add -A
git commit -m "Complete Day 20 Lab - Model Serving"
git push origin main
```
- Đảm bảo repo **PUBLIC** trên GitHub
- Paste URL vào VinUni LMS

### ✅ DoD — Task 5
- [ ] REFLECTION.md không còn placeholder `<Họ Tên>`, `<YYYY-MM-DD>`, `_Answer here._`
- [ ] §1 có đầy đủ hardware spec
- [ ] §2 có bảng 2 dòng Q4_K_M + Q2_K với TTFT/TPOT tách riêng
- [ ] §3 có bảng load test 10 + 50 users, có KV cache observation
- [ ] §4 liệt kê N16–N19 pieces, có timing breakdown
- [ ] §5 có "single change" + before/after + WHY paragraph (≥2 đoạn)
- [ ] §7 self-graded checklist đã tick
- [ ] `submission/screenshots/` có ≥ 6 ảnh PNG/JPG
- [ ] `python scripts\verify.py` exit code 0
- [ ] Repo pushed, **public** trên GitHub
- [ ] URL pasted vào LMS

---

## TASK 6 (BONUS): Optimization Sweeps — tối đa +20đ

> Không bắt buộc. Nhưng **rất nên làm** vì:
> - Máy bạn (i5-10300H + GTX 1650 4GB) là setup lý tưởng — có GPU nhưng VRAM nhỏ → partial offload sẽ cho insight rất rõ
> - Bonus 16đ khả thi (MLX 4đ không áp dụng vì không phải Apple Silicon)
> - §5 REFLECTION (10đ core) **cần** kết quả bonus để viết mạnh — đây là phần grader đọc kỹ nhất

### Bonus scoring breakdown

| # | Tiêu chí | Bằng chứng | Điểm |
|---|---|---|---:|
| B1 | Build `llama.cpp` từ source | `llama-bench --version` chạy | 4 |
| B2 | ≥1 sweep committed | `benchmarks/bonus-*.md` non-trivial | 4 |
| B3 | Speedup quantified | before/after trong REFLECTION §5 | 4 |
| B4 | ≥1 challenge attempted | Writeup trong REFLECTION hoặc file riêng | 4 |
| B5 | MLX comparison | ❌ Không áp dụng (cần Apple Silicon) | — |
| | **Tổng bonus khả thi** | | **16** |

---

### BONUS STEP 1: Build llama.cpp từ source (4đ) — ~15 phút

**Yêu cầu:** CUDA Toolkit 12+, cmake, MSVC (Visual Studio Build Tools).

> ⚠️ Bạn cài `llama.cpp` qua `winget` chỉ là binary — chưa tính là "build from source".
> Grader cần thấy `BONUS-llama-cpp-optimization/llama.cpp/build/bin/llama-bench.exe` từ source build.

**Bước 1.1: Kiểm tra prerequisites**
```powershell
nvcc --version          # cần CUDA Toolkit 12+
cmake --version         # cần cmake 3.21+
cl                      # cần MSVC (từ Visual Studio Build Tools)
```

Nếu thiếu, cài:
- **CUDA Toolkit:** https://developer.nvidia.com/cuda-downloads
- **cmake:** `winget install Kitware.CMake`
- **MSVC:** `winget install Microsoft.VisualStudio.2022.BuildTools` → chọn "C++ build tools"

**Bước 1.2: Clone + Build**
```powershell
cd D:\VSCODE\VINAI\Day20-Track2-ModelServing-Lab\BONUS-llama-cpp-optimization
git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp

# Build CUDA + native CPU instructions (AVX2 trên i5-10300H)
cmake -B build -DGGML_CUDA=ON -DGGML_NATIVE=ON
cmake --build build -j --config Release
```

**Bước 1.3: Verify**
```powershell
.\build\bin\Release\llama-bench.exe --version
# Hoặc:
.\build\bin\Release\llama-bench.exe -m ..\..\models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -t 4 -ngl 99 -n 64
```

**Chụp screenshot** → `submission/screenshots/06-bonus-sweep.png` (hoặc thêm vào sau khi chạy sweep)

### ✅ DoD — Step 1
- [ ] Thư mục `BONUS-llama-cpp-optimization/llama.cpp/build/` tồn tại
- [ ] `llama-bench.exe` chạy không lỗi
- [ ] Build log hiện `-DGGML_CUDA=ON -DGGML_NATIVE=ON`

---

### BONUS STEP 2: Chạy Sweep (4đ) — ~15-20 phút

**Chọn 2 sweep phù hợp nhất cho máy bạn:**

#### Sweep A: GPU Offload Sweep ⭐ (Khuyên dùng — insight mạnh nhất)

Máy bạn có GTX 1650 (4GB VRAM) + TinyLlama 1.1B (~0.7GB Q4_K_M) → model **vừa đủ fit** trong VRAM.
Sweep này cho thấy khi nào GPU offload giúp, khi nào không:

```powershell
python BONUS-llama-cpp-optimization\benchmarks\gpu-offload-sweep.py
```

Script sẽ chạy `llama-bench` với `-ngl 0, 8, 16, 24, 32, 99` và ghi kết quả vào `benchmarks/bonus-gpu-offload-sweep.md`.

**Kỳ vọng trên máy bạn:**
| -ngl | Ý nghĩa | Dự đoán |
|---:|---|---|
| 0 | 100% CPU | Baseline chậm nhất |
| 8–16 | Partial offload | Nhanh hơn 0, nhưng bus PCIe trở thành bottleneck |
| 24–32 | Gần full offload | Nhanh nhất nếu model fit |
| 99 | Full offload | Nhanh nhất — toàn bộ 1.1B fit trong 4GB VRAM |

**Insight cần viết:** Giải thích _tại sao_ `-ngl 99` thắng (model nhỏ fit hoàn toàn vào VRAM → không cần bus CPU↔GPU → decode chỉ bị memory bandwidth GPU giới hạn, mà GDDR6 @ ~192 GB/s >> DDR4 @ ~42 GB/s trên i5-10300H).

#### Sweep B: Thread Sweep (Bổ sung tốt)

Cho thấy peak ở physical cores (4) rồi drop khi vào hyperthreads (8):

```powershell
python BONUS-llama-cpp-optimization\benchmarks\thread-sweep.py
```

Ghi kết quả vào `benchmarks/bonus-thread-sweep.md`.

**Kỳ vọng:**
| Threads | Dự đoán |
|---:|---|
| 1–2 | Chậm, chưa dùng hết bandwidth |
| 4 (= physical) | **Peak** — 4 core thật, memory controller bão hòa |
| 8 (= logical) | **Drop** — hyperthreads tranh nhau memory channel |
| 16 (= 2× logical) | Chậm hơn nữa |

**Insight:** LLM decode là **memory-bandwidth-bound**, không phải compute-bound. Thêm thread vượt physical cores không giúp vì bottleneck là tốc độ đọc RAM, không phải tính toán.

### ✅ DoD — Step 2
- [ ] File `benchmarks/bonus-gpu-offload-sweep.md` tồn tại, có bảng ≥5 dòng
- [ ] HOẶC file `benchmarks/bonus-thread-sweep.md` tồn tại, có bảng ≥4 dòng
- [ ] Screenshot sweep output → `submission/screenshots/06-bonus-sweep.png`

---

### BONUS STEP 3: Quantify Speedup cho REFLECTION §5 (4đ)

Đây là bước **quan trọng nhất** — kết quả sweep ở Step 2 trở thành nội dung §5 REFLECTION.

**Template viết §5 (copy + điền số):**

```markdown
## 5. Bonus — The single change that mattered most

**Change:** Offload toàn bộ model lên GPU (GTX 1650 4GB) bằng flag `-ngl 99`

**Before vs after:**
before (CPU only, -ngl 0):   <X> tok/s
after  (full GPU, -ngl 99):  <Y> tok/s
speedup: ~<Y/X>×

**Tại sao nó work:**

TinyLlama-1.1B Q4_K_M chỉ ~0.7GB, fit hoàn toàn trong 4GB VRAM của GTX 1650.
Khi `-ngl 0`, decode phải đọc toàn bộ model weights từ DDR4 RAM qua memory 
controller của i5-10300H. DDR4-2933 dual-channel cho ~42 GB/s bandwidth.

Khi `-ngl 99`, decode đọc weights từ GDDR6 trên GPU. GTX 1650 Max-Q có 
memory bandwidth ~192 GB/s — gấp ~4.5× so với CPU RAM. Vì LLM decode ở
batch-size 1 là hoàn toàn memory-bandwidth-bound (mỗi token cần đọc toàn bộ 
model weights 1 lần), speedup gần bằng tỉ lệ bandwidth.

Tuy nhiên, partial offload (-ngl 8, 16) không scale tuyến tính vì thêm 
overhead truyền activation qua bus PCIe 3.0 x16 (~16 GB/s) giữa CPU và GPU 
sau mỗi layer. Full offload (-ngl 99) loại bỏ hoàn toàn chi phí này.
```

> 💡 **Tip:** Nếu kết quả khác kỳ vọng (vd: `-ngl 99` không nhanh hơn nhiều) → **viết rõ** tại sao. Grader thưởng điểm cho nhận xét trung thực + phân tích đúng, không phải speedup lớn.

### ✅ DoD — Step 3
- [ ] REFLECTION.md §5 có tên thay đổi cụ thể
- [ ] Có số liệu before/after (tok/s hoặc ms)
- [ ] Có speedup factor (vd: ~3.2×)
- [ ] Có ≥1 đoạn giải thích WHY dựa trên hardware model (bandwidth, compute, cache)
- [ ] Không vibes-based — có logic rõ ràng

---

### BONUS STEP 4: Attempt 1 Challenge (4đ) — ~30-60 phút

**Khuyên dùng cho máy bạn: C6 — Vulkan vs CUDA**

Bạn có NVIDIA GPU → build 2 lần (CUDA + Vulkan), so sánh tốc độ, giải thích tại sao vendor-specific kernels (CUDA) nhanh hơn generic compute API (Vulkan).

**Bước thực hiện:**

```powershell
# Build 1: đã có từ Step 1 (CUDA)
# Ghi nhận kết quả CUDA
.\BONUS-llama-cpp-optimization\llama.cpp\build\bin\Release\llama-bench.exe `
    -m models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -t 4 -ngl 99 -n 128 -r 3

# Build 2: Vulkan
cd BONUS-llama-cpp-optimization\llama.cpp
cmake -B build-vulkan -DGGML_VULKAN=ON -DGGML_NATIVE=ON
cmake --build build-vulkan -j --config Release
cd ..\..

# Ghi nhận kết quả Vulkan
.\BONUS-llama-cpp-optimization\llama.cpp\build-vulkan\bin\Release\llama-bench.exe `
    -m models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -t 4 -ngl 99 -n 128 -r 3
```

> ⚠️ Vulkan build cần Vulkan SDK. Cài: `winget install KhronosGroup.VulkanSDK`

**Writeup template (tạo file `benchmarks/bonus-challenge-c6.md`):**
```markdown
# Challenge C6 — Vulkan vs CUDA on GTX 1650

## Setup
- GPU: NVIDIA GeForce GTX 1650 Max-Q (4GB GDDR6)
- Model: TinyLlama-1.1B Q4_K_M  
- -ngl 99, -t 4, -n 128, -r 3

## Results
| Backend | tg128 (tok/s) | pp512 (tok/s) |
|---|---:|---:|
| CUDA | <X> | <A> |
| Vulkan | <Y> | <B> |
| Speedup (CUDA/Vulkan) | <X/Y>× | <A/B>× |

## Analysis
CUDA nhanh hơn Vulkan ~<Z>× vì ...
(giải thích: CUDA kernels được tối ưu riêng cho kiến trúc Turing/Ampere,
dùng Tensor Cores, shared memory layout tối ưu. Vulkan dùng compute 
shaders generic, không access được Tensor Cores, overhead dispatch cao hơn.
Đây chính là lý do vLLM/SGLang chỉ hỗ trợ CUDA — vendor-specific kernels
như FlashAttention, CUTLASS, cuBLAS cho hiệu năng cao hơn đáng kể.)
```

**Thay thế nếu không cài được Vulkan SDK:** Chọn **C2 — KV-cache quantization**

```powershell
# So sánh server có/không KV cache quantization
# Terminal 1: chạy server KHÔNG quantize KV
llama-server -m models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --port 8080 -ngl 99 --metrics

# Terminal 1 (lần 2): chạy server CÓ quantize KV  
llama-server -m models\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --port 8080 -ngl 99 --metrics `
    --cache-type-k q8_0 --cache-type-v q8_0
```

So sánh RAM usage + latency + quality trên cùng 5 prompts.

### ✅ DoD — Step 4
- [ ] Đã attempt ≥1 challenge (C2 hoặc C6)
- [ ] Có file writeup: `benchmarks/bonus-challenge-c6.md` HOẶC section trong REFLECTION
- [ ] Có bảng before/after numbers
- [ ] Có ≥1 đoạn phân tích (không chỉ paste số)

---

### Tổng kết Bonus — Priority Order

```
Ưu tiên cao → thấp:

Step 3: Viết §5 REFLECTION (4đ) ← DỄ NHẤT, ảnh hưởng cả 10đ core
Step 2: Chạy GPU offload sweep (4đ) ← chạy 1 lệnh, 15 phút
Step 1: Build from source (4đ) ← cần CUDA Toolkit + MSVC
Step 4: Challenge C6 hoặc C2 (4đ) ← tốn thời gian nhất, làm cuối
```

> **Nếu thời gian ít:** Chỉ cần làm Step 2 + Step 3 = **8đ bonus** + REFLECTION §5 mạnh hơn rất nhiều.
> Sweep scripts dùng `llama-bench` từ source build → cần Step 1 trước.

---

## Thứ tự thực hiện (Recommended Flow)

```
TASK 1 (Setup)
    ↓
TASK 2 (Benchmark)         ← cần model từ Task 1
    ↓
TASK 3 (Server + Load)     ← cần model + venv từ Task 1
    ↓
TASK 4 (Pipeline)          ← cần server đang chạy từ Task 3
    ↓
TASK 6 (Bonus sweeps)      ← tùy chọn, có thể làm song song với Task 3–4
    ↓
TASK 5 (Report + Verify)   ← tổng hợp tất cả kết quả, làm cuối cùng
```

---

## Lưu ý quan trọng cho Windows

1. **`make` không native trên Windows** — dùng `pwsh` chạy script trực tiếp hoặc cài `make` qua `choco install make`.
2. **llama.cpp đã cài qua winget** — bạn có `llama-server` sẵn, dùng cho Track 02 (Cách B) sẽ nhanh hơn `llama-cpp-python` server.
3. **Vẫn cần `llama-cpp-python`** — Track 01 benchmark dùng thư viện Python, không dùng binary.
4. **Đóng browser/IDE/Slack khi benchmark** — background processes ăn CPU + memory bandwidth, làm méo kết quả.
5. **Repo phải PUBLIC** — nếu private → 0 điểm. Kiểm tra trước khi nộp.
