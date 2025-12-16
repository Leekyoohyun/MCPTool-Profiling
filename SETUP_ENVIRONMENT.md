# Environment Setup Guide for WASM Tool Profiling

각 엣지 노드에서 WASM 도구 측정을 위한 환경 설정 가이드

---

## Prerequisites

### 1. 시스템 요구사항
- Python 3.8 이상
- Git
- wasmtime (WASM 런타임)

### 2. EdgeAgent WASM 빌드 완료
```bash
# EdgeAgent/wasm_mcp/ 디렉토리에 빌드된 WASM 파일들이 있어야 함
~/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release/*.wasm
```

---

## Step 1: Python 가상환경 설정

```bash
# 홈 디렉토리로 이동
cd ~

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

---

## Step 2: 필수 Python 패키지 설치

```bash
# langchain-mcp-adapters 설치
pip install langchain-mcp-adapters

# 기타 필수 패키지
pip install pyyaml

# 이미지 처리 (PIL/numpy)
# 방법 1: pip로 설치 (가상환경 내)
pip install Pillow numpy

# 방법 2: 시스템 패키지로 설치 (externally-managed 환경)
# sudo apt install python3-pil python3-numpy
```

---

## Step 3: 프로파일링 스크립트 복사

```bash
# 프로파일링 디렉토리 생성
mkdir -p ~/EdgeAgent-Profile-for-Schedule-v2
cd ~/EdgeAgent-Profile-for-Schedule-v2

# 스크립트 파일들을 scp로 복사 (MacBook에서 실행)
# scp -r EdgeAgent-Profile-for-Schedule-v2/* edge-nuc:~/EdgeAgent-Profile-for-Schedule-v2/
# scp -r EdgeAgent-Profile-for-Schedule-v2/* edge-orin:~/EdgeAgent-Profile-for-Schedule-v2/
# scp -r EdgeAgent-Profile-for-Schedule-v2/* device-rpi:~/EdgeAgent-Profile-for-Schedule-v2/
```

**또는 직접 생성:**
필요한 파일들:
- `1_benchmark_node.py` - 네트워크 측정
- `2b_measure_wasm_tools_mcp.py` - WASM 도구 측정 (전체)
- `2b_measure_simple_tools.py` - WASM 도구 측정 (git/filesystem 제외)
- `generate_test_data.py` - 테스트 데이터 생성
- `setup_test_data_for_wasm.sh` - 테스트 데이터 설정
- `utils/tool_definitions.py` - 도구 정의

---

## Step 4: wasmtime 설치

```bash
# wasmtime 설치
curl https://wasmtime.dev/install.sh -sSf | bash

# PATH에 추가 (쉘 재시작 또는 수동 추가)
source ~/.bashrc

# 확인
wasmtime --version
```

---

## Step 5: 테스트 데이터 생성

```bash
cd ~/EdgeAgent-Profile-for-Schedule-v2

# 가상환경 활성화 (아직 안 했다면)
source ~/venv/bin/activate

# utils 디렉토리 생성
mkdir -p utils

# tool_definitions.py 생성 (스크립트에 필요)
# (파일 내용은 별도로 제공)

# 테스트 데이터 생성
python3 generate_test_data.py

# /tmp로 복사 및 git 초기화
./setup_test_data_for_wasm.sh
```

---

## Step 6: API 키 설정 (Summarize 도구용, 선택사항)

**`.env` 파일 사용 (권장):**

```bash
cd ~/EdgeAgent-Profile-for-Schedule-v2

# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집
nano .env
```

**.env 파일 내용:**
```bash
# API Keys for Summarize Tools
OPENAI_API_KEY=sk-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**저장 후 확인:**
```bash
cat .env
```

**참고:**
- API 키가 없으면 summarize 도구는 실패하지만 다른 도구들은 정상 측정됩니다
- `.env` 파일은 스크립트 실행 시 자동으로 읽힙니다
- 환경변수 export 필요 없음!

---

## Step 7: 실행

### 7-1. 네트워크 측정

```bash
cd ~/EdgeAgent-Profile-for-Schedule-v2
source ~/venv/bin/activate

# Cloud로 측정 (예시)
python3 1_benchmark_node.py 13.124.203.227 80

# 다른 엣지 노드로 측정
python3 1_benchmark_node.py 172.16.1.1 80
```

**출력:** `node_<hostname>.yaml`

### 7-2. WASM 도구 측정 (Simple - 추천)

Git과 Filesystem을 제외한 간단한 도구들만 측정:

```bash
cd ~/EdgeAgent-Profile-for-Schedule-v2
source ~/venv/bin/activate

python3 2b_measure_simple_tools.py
```

**출력:** `simple_tool_exec_time_<hostname>.json`

### 7-3. WASM 도구 측정 (전체)

모든 도구 측정 (git, filesystem 포함):

```bash
cd ~/EdgeAgent-Profile-for-Schedule-v2
source ~/venv/bin/activate

python3 2b_measure_wasm_tools_mcp.py
```

**출력:** `wasm_tool_exec_time_<hostname>.json`

---

## 노드별 체크리스트

각 노드에서 실행해야 할 것:

### edge-nuc
- [ ] Python venv 생성 및 활성화
- [ ] langchain-mcp-adapters 설치
- [ ] 스크립트 파일 복사
- [ ] wasmtime 설치 확인
- [ ] 테스트 데이터 생성 (`setup_test_data_for_wasm.sh`)
- [ ] 네트워크 측정 실행
- [ ] WASM 도구 측정 실행

### edge-orin
- [ ] Python venv 생성 및 활성화
- [ ] langchain-mcp-adapters 설치
- [ ] 스크립트 파일 복사
- [ ] wasmtime 설치 확인
- [ ] 테스트 데이터 생성
- [ ] 네트워크 측정 실행
- [ ] WASM 도구 측정 실행

### device-rpi
- [ ] Python venv 생성 및 활성화
- [ ] langchain-mcp-adapters 설치
- [ ] 스크립트 파일 복사
- [ ] wasmtime 설치 확인
- [ ] 테스트 데이터 생성
- [ ] 네트워크 측정 실행
- [ ] WASM 도구 측정 실행

---

## 트러블슈팅

### 1. `ModuleNotFoundError: No module named 'langchain_mcp_adapters'`

**원인:** Python 패키지가 설치되지 않음

**해결:**
```bash
source ~/venv/bin/activate
pip install langchain-mcp-adapters
```

### 2. `externally-managed-environment` 에러

**원인:** 시스템 Python에 직접 설치 불가

**해결:** 가상환경 사용
```bash
python3 -m venv venv
source venv/bin/activate
pip install 패키지명
```

### 3. wasmtime not found

**해결:**
```bash
curl https://wasmtime.dev/install.sh -sSf | bash
source ~/.bashrc
```

### 4. WASM 파일 not found

**확인:**
```bash
ls ~/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release/*.wasm
```

**없으면 빌드:**
```bash
cd ~/EdgeAgent/wasm_mcp
cargo build --target wasm32-wasip2 --release
```

### 5. Git user not configured

**해결:**
```bash
cd /tmp/git_repo
git config user.name "Test User"
git config user.email "test@example.com"
```

### 6. Permission denied (os error 2)

**원인:** WASM 보안 제한

**해결:** 일부 도구는 측정 불가 (예상된 동작)

### 7. API key not set for provider: openai

**원인:** Summarize 도구에 API 키 필요

**해결:** API 키 설정 (Step 6) 또는 해당 도구 건너뜀

---

## 최종 확인

모든 설정이 완료되면:

```bash
# 가상환경 확인
which python
# 출력: /home/sysop/venv/bin/python

# 패키지 확인
pip list | grep langchain-mcp-adapters
# 출력: langchain-mcp-adapters  x.x.x

# wasmtime 확인
wasmtime --version
# 출력: wasmtime x.x.x

# WASM 파일 확인
ls ~/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release/*.wasm | wc -l
# 출력: 9 (또는 서버 개수)

# 테스트 데이터 확인
ls /tmp/*.png /tmp/*.txt /tmp/*.log 2>/dev/null | wc -l
# 출력: 10+ (테스트 파일들)

# Git repo 확인
cd /tmp/git_repo && git status
# 출력: clean working tree
```

---

## Quick Start (전체 명령어 요약)

```bash
# 1. 가상환경
cd ~
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 2. 패키지 설치
pip install langchain-mcp-adapters pyyaml Pillow numpy

# 3. wasmtime 설치
curl https://wasmtime.dev/install.sh -sSf | bash
source ~/.bashrc

# 4. 스크립트 디렉토리
mkdir -p ~/EdgeAgent-Profile-for-Schedule-v2
cd ~/EdgeAgent-Profile-for-Schedule-v2
# (파일들 scp로 복사)

# 5. 테스트 데이터
python3 generate_test_data.py
./setup_test_data_for_wasm.sh

# 6. 실행
python3 1_benchmark_node.py 13.124.203.227 80
python3 2b_measure_simple_tools.py
```

완료!
