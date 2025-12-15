# EdgeAgent Tool Profiling v2

**목표:** 각 노드에서 모든 MCP Tool(49개)의 성능을 **실측**하고 Roofline Model 기반으로 Alpha 값 계산

**⚠️ 중요: 모든 값은 실측값입니다. 추정/추측/가정 없음.**

## 측정 대상 노드

- **device-rpi**: Raspberry Pi 4 (DEVICE)
- **edge-nuc**: Intel NUC (EDGE)
- **edge-orin**: Jetson Orin Nano (EDGE)
- **cloud-aws**: AWS EC2 m5.xlarge (CLOUD)

## 측정 프로세스

### Phase 1: 노드 성능 측정
```bash
# 각 노드에서 실행
ssh <node>
cd EdgeAgent-Profile-for-Schedule-v2
make
python3 1_benchmark_node.py
```

**측정 결과:**
- Peak FLOPS (GFLOPS)
- Memory Bandwidth (GB/s)
- Ridge Point = FLOPS / Memory_BW
- **Network Bandwidth (Mbps)** ← 추가!
- Storage IOPS

**Network Bandwidth 측정:**
```bash
# iperf3 서버 시작 (cloud-aws 또는 reference node에서)
iperf3 -s -D

# 각 노드에서 (IPERF_SERVER 환경변수 설정)
export IPERF_SERVER=10.2.0.1
python3 1_benchmark_node.py
```

**출력:**
- `node_<hostname>.yaml` (network_bandwidth_mbps 포함)
- `roofline_<hostname>.png` (Roofline 그래프)

---

### Phase 2A: Native Tool 실행시간 측정
```bash
# device-rpi, cloud-aws에서 실행
ssh device-rpi
cd EdgeAgent-Profile-for-Schedule-v2
python3 2a_measure_native_tools.py
```

**측정 내용:**
- T_exec: 각 tool의 실행시간
- Input/Output 크기

**⚠️ 현재 상태: 프레임워크만 제공**
- MCP client 구현 필요
- 실제 Python 서버 연동 필요

**출력:**
- `native_tool_exec_time_<hostname>.json`

---

### Phase 2B: WASM Tool 실행시간 측정
```bash
# edge-nuc, edge-orin에서 실행
ssh edge-nuc
cd EdgeAgent-Profile-for-Schedule-v2
python3 2b_measure_wasm_tools.py
```

**측정 내용:**
- T_exec: 각 WASM tool의 실행시간
- Input/Output 크기
- wasmtime으로 실행

**요구사항:**
- wasmtime 설치
- WASM 서버 빌드 완료 (EdgeAgent/wasm_mcp/)

**출력:**
- `wasm_tool_exec_time_<hostname>.json`

---

### Phase 3: Alpha 계산
```bash
# MacBook에서 실행
python3 3_calculate_alpha_new.py
```

**공식:**
```
alpha = T_exec / (T_exec + T_comm_ref)

where:
  T_exec = 실제 tool 실행시간 (측정값)
  T_comm_ref = (Input_size + Output_size) / Bandwidth_node
```

**입력:**
- `node_*.yaml` (모든 노드, network_bandwidth_mbps 포함)
- `native_tool_exec_time_*.json` (Native 측정 결과)
- `wasm_tool_exec_time_*.json` (WASM 측정 결과)

**출력:**
- `profile_native.yaml` (Native tool profile)
- `profile_wasm.yaml` (WASM tool profile)

---

## 최종 결과물

### profile_native.yaml / profile_wasm.yaml
```yaml
tools:
  resize_image:
    description: "Resize image to max size"
    data_locality: local_data
    alpha: 0.856                      # T_exec / (T_exec + T_comm_ref)
    alpha_by_node:
      device-rpi: 0.823
      cloud-aws: 0.889
    t_exec_by_node:
      device-rpi: 2.145               # 실측 실행시간 (초)
      cloud-aws: 0.458
    avg_input_size_bytes: 5242880     # 평균 Input 크기
    avg_output_size_bytes: 524288     # 평균 Output 크기

  read_file:
    description: "Read file contents"
    data_locality: local_data
    alpha: 0.125                      # I/O bound
    alpha_by_node:
      device-rpi: 0.098
      cloud-aws: 0.152
    t_exec_by_node:
      device-rpi: 0.012
      cloud-aws: 0.008
    avg_input_size_bytes: 256
    avg_output_size_bytes: 10240

  # ... 총 49개 tool
```

**Alpha 계산 공식:**
```
alpha = T_exec / (T_exec + T_comm_ref)

T_comm_ref = (Input_size + Output_size) / Bandwidth_node
```

**모든 값이 실측:**
- ✅ `T_exec`: 각 노드에서 tool 실행하여 측정
- ✅ `Input/Output_size`: 실제 payload 크기 측정
- ✅ `Bandwidth_node`: iperf3로 측정
- ✅ `alpha`: 위 실측값들로부터 계산

### Roofline 그래프

**roofline_all_nodes.png:**
- X축: Operational Intensity (FLOPS/Byte)
- Y축: Performance (GFLOPS)
- 각 노드의 Roofline (4개 선)
- 각 Tool의 위치 (49개 점)
- Alpha 값에 따른 색상 구분:
  - 빨강 (α > 0.7): CPU-bound
  - 노랑 (0.3 ≤ α ≤ 0.7): Mixed
  - 파랑 (α < 0.3): Memory/IO-bound

---

## Tool 목록 (49개)

**출처:** `/Users/leekyoohyun/DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent-Profiling/output/tool_schema_for_9_server/all_tool_schemas.json`

### Filesystem (14개)
- read_file
- read_text_file
- read_media_file
- read_multiple_files
- write_file
- edit_file
- create_directory
- list_directory
- list_directory_with_sizes
- directory_tree
- move_file
- search_files
- get_file_info
- list_allowed_directories

### Git (12개)
- git_status
- git_diff_unstaged
- git_diff_staged
- git_diff
- git_commit
- git_add
- git_reset
- git_log
- git_create_branch
- git_checkout
- git_show
- git_branch

### Fetch (1개)
- fetch

### Sequential Thinking (1개)
- sequentialthinking

### Time (2개)
- get_current_time
- convert_time

### Summarize (3개)
- summarize_text
- summarize_documents
- get_provider_info

### Log Parser (5개)
- parse_logs
- filter_entries
- compute_log_statistics
- search_entries
- extract_time_range

### Data Aggregate (5개)
- aggregate_list
- merge_summaries
- combine_research_results
- deduplicate
- compute_trends

### Image Resize (6개)
- get_image_info
- resize_image
- scan_directory
- compute_image_hash
- compare_hashes
- batch_resize

---

## 디렉토리 구조

```
EdgeAgent-Profile-for-Schedule-v2/
├── README.md
├── Makefile                          # 벤치마크 컴파일
├── peak_flops.c                      # CPU 벤치마크
├── memory_bandwidth.c                # 메모리 벤치마크
├── storage_benchmark.sh              # 스토리지 벤치마크
│
├── 1_benchmark_node.py               # Phase 1: 노드 성능 측정
├── 2_measure_tool_oi.py              # Phase 2: Tool OI 측정
├── 3_calculate_alpha.py              # Phase 3: Alpha 계산
│
├── utils/
│   ├── tool_definitions.py           # 49개 tool 정의
│   ├── roofline_plot.py              # Roofline 그래프 생성
│   └── perf_wrapper.py               # perf 측정 헬퍼
│
├── node_device_rpi.yaml              # 출력: 노드 성능
├── node_edge_nuc.yaml
├── node_edge_orin.yaml
├── node_cloud_aws.yaml
│
├── roofline_device_rpi.png           # 출력: 노드별 Roofline
├── roofline_edge_nuc.png
├── roofline_edge_orin.png
├── roofline_cloud_aws.png
│
├── tool_oi_measurements.json         # 출력: Tool OI
├── profile.yaml                      # 출력: 최종 프로파일
└── roofline_all_nodes.png            # 출력: 전체 Roofline
```

---

## Alpha 계산 공식

### 1. Roofline 기반 (Local Tools)

```python
α = sigmoid(log(OI) - log(ridge_point), k=2.0)

# OI >> ridge_point → α ≈ 1.0 (CPU-bound)
# OI << ridge_point → α ≈ 0.0 (Memory-bound)
```

### 2. Computation Importance (Network Tools)

```python
α = T_exec / (T_exec + T_comm_ref)
T_comm_ref = D_in / bandwidth

# T_exec 크면 → α ≈ 1.0 (계산 중심)
# T_comm_ref 크면 → α ≈ 0.0 (통신 중심)
```

---

## 실행 예시

```bash
# 1. device-rpi에서
ssh device-rpi
cd EdgeAgent-Profile-for-Schedule-v2
make
python3 1_benchmark_node.py
# → node_device_rpi.yaml, roofline_device_rpi.png

# 2. edge-nuc에서
ssh edge-nuc
cd EdgeAgent-Profile-for-Schedule-v2
make
python3 1_benchmark_node.py
python3 2_measure_tool_oi.py
# → node_edge_nuc.yaml, roofline_edge_nuc.png, tool_oi_measurements.json

# 3. edge-orin에서
ssh edge-orin
cd EdgeAgent-Profile-for-Schedule-v2
make
python3 1_benchmark_node.py
# → node_edge_orin.yaml, roofline_edge_orin.png

# 4. cloud-aws에서
ssh cloud-aws
cd EdgeAgent-Profile-for-Schedule-v2
make
python3 1_benchmark_node.py
# → node_cloud_aws.yaml, roofline_cloud_aws.png

# 5. MacBook에서 (결과 수집 후)
scp device-rpi:~/EdgeAgent-Profile-for-Schedule-v2/node_*.yaml .
scp edge-nuc:~/EdgeAgent-Profile-for-Schedule-v2/node_*.yaml .
scp edge-nuc:~/EdgeAgent-Profile-for-Schedule-v2/tool_oi_measurements.json .
scp edge-orin:~/EdgeAgent-Profile-for-Schedule-v2/node_*.yaml .
scp cloud-aws:~/EdgeAgent-Profile-for-Schedule-v2/node_*.yaml .

python3 3_calculate_alpha.py
# → profile.yaml, roofline_all_nodes.png
```
