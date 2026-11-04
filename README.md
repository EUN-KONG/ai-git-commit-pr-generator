# ai-git-commit-pr-generator

Git 변경 내용을 OpenAI 호환 API에 전달하여 커밋 제목 또는 Pull Request(PR) 초안을 터미널에 출력하는 Python CLI 도구입니다. 생성된 문구는 사용자가 검토하고 복사해 사용합니다. 프로그램이 직접 커밋하거나 push하거나 GitHub에 PR을 게시하지 않습니다.

## 1. 설치

Python **3.10 이상**, Git, 실제 AI 생성 시 인터넷 연결과 새로 발급받은 OpenAI 호환 API Key가 필요합니다. 아래 명령은 macOS/Linux의 zsh 또는 bash 기준입니다.

```bash
git clone https://github.com/EUN-KONG/ai-git-commit-pr-generator.git
cd ai-git-commit-pr-generator
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`python3 --version`이 3.10 미만이면 Python 3.10 이상을 설치하고, 해당 실행 파일로 가상환경을 만드세요. 예를 들어 Python 3.12가 있다면 `python3.12 -m venv .venv`를 사용합니다. 이후 명령은 가상환경을 활성화한 상태에서 실행합니다.

## 2. API Key 환경변수 설정

API 서비스에서 호환 방식을 **OpenAI**로 선택해 발급받은 키를 **현재 터미널의 환경변수**로 설정합니다. 기본 API 주소는 `https://copa.codyssey.kr/v1`, 모델은 `gpt-5-mini`입니다. 실제 요청에는 API 서비스 계정의 사용 권한과 사용 가능한 크레딧이 필요합니다. OpenAI 공식 사이트의 잔액과는 별도입니다.

아래 방식은 키를 화면이나 명령 기록에 직접 남기지 않고 입력합니다. `API Key 입력:`이 표시되면 키를 붙여넣고 Enter를 누릅니다. 입력 내용이 보이지 않는 것은 정상입니다.

zsh:

```zsh
read -s "AI_API_KEY?API Key 입력: "; echo
export AI_API_KEY
```

bash:

```bash
read -s -p "API Key 입력: " AI_API_KEY; echo
export AI_API_KEY
```

터미널을 새로 열면 다시 설정해야 합니다. 프로그램은 `.env` 파일을 자동으로 읽지 않습니다. 키를 코드, README, 커밋, 채팅에 붙여넣지 마세요. 사용 후에는 `unset AI_API_KEY`로 해제할 수 있습니다.

## 3. 실행 방법

항상 이 프로젝트의 루트(`main.py`가 있는 폴더)에서 실행합니다. 현재 저장소의 **커밋하지 않은 변경 사항**을 읽으며, 이미 완료한 커밋이나 브랜치 전체의 차이는 분석하지 않습니다.

```bash
# 변경 파일과 diff만 확인: API Key와 비용이 필요하지 않습니다.
python main.py

# 커밋 제목 생성
python main.py commit --safe-mode

# PR 제목과 본문 생성
python main.py pr --safe-mode

# 변경 요약만 생성
python main.py --generate --safe-mode

# 옵션 도움말
python main.py --help
```

`git status`로 파일 목록을, `git diff`와 `git diff --cached`로 각각 Git에 추가하기 전후의 변경 내용을 수집합니다. 새 파일은 목록에만 표시되므로 내용을 분석하려면 먼저 확인 후 `git add <파일명>`을 실행하세요. 이는 커밋이 아니라 다음 커밋에 포함할 파일을 준비하는 작업입니다. 변경 사항이 없으면 API를 호출하지 않고 `[INFO] 변경 사항이 없습니다.`를 출력합니다.

### 호출 옵션

```bash
python main.py commit --safe-mode --model gpt-5-mini --max-tokens 4000
python main.py pr --safe-mode --max-tokens 4000
```

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--base-url` | `https://copa.codyssey.kr/v1` | OpenAI 호환 API 주소 |
| `--model` | `gpt-5-mini` | API 서비스에서 지원하는 모델 ID |
| `--temperature` | `1` | 지원 모델에서 표현의 변화 조절. gpt-5-mini에서는 1만 허용하고 전송 생략 |
| `--max-tokens` | `4000` | 출력·추론 토큰의 상한. 글자 수와는 다름 |
| `--safe-mode` | 꺼짐 | diff를 처음 200줄까지만 사용 |

`-model`, `-temperature`, `-max-tokens`, `-safe-mode`도 지원합니다. 기본 `gpt-5-mini`는 temperature 조절을 지원하지 않습니다. 조절이 필요하면 지원 모델로 `--model`을 바꾸고 `--temperature`를 지정하세요. 모델마다 지원 옵션과 접근 권한이 다를 수 있으므로 오류가 나면 모델과 옵션을 확인하세요. 출력 토큰이 부족하면 결과를 사용하지 않고 오류를 표시합니다. 필요할 때만 상한을 높이세요.

## 4. 출력 예시

다음은 출력 형태를 설명하는 예시이며, 실제 AI 호출 결과를 기록한 것은 아닙니다. 입력 diff에 따라 문구는 달라집니다. 생성 명령에서는 변경 파일·diff 줄 수·호출 횟수 안내 다음에 결과가 표시됩니다. 긴 diff 원문은 `python main.py`로 따로 확인합니다.

커밋 메시지:

```text
--- Commit Message ---
feat: Git 변경 사항 수집 기능 추가
----------------------
[INFO] 생성된 초안은 검토 후 복사하여 사용해 주세요.
```

커밋은 제목 한 줄만 생성합니다. 50자 이내를 권장하고 최대 72자로 제한하며, 초과 시 잘라낸 사실을 안내합니다. 잘린 제목의 의미가 자연스러운지 확인하세요.

PR 초안:

```text
--- PR Title ---
feat: Git 변경 사항 수집 기능 추가
--- PR Body ---
## Why
- 변경 내용을 설명하는 작업을 줄이기 위한 개선입니다. 배경 확인이 필요합니다.

## What
- 변경 파일 목록과 diff를 수집합니다.

## How to Test
- python main.py를 실행하여 변경 파일과 diff가 표시되는지 확인합니다.
----------------------
[INFO] 생성된 초안은 검토 후 복사하여 사용해 주세요.
```

PR 제목은 한 줄, 최대 80자로 제한합니다. 본문은 `Why`, `What`, `How to Test` 섹션과 각 섹션의 불릿을 포함합니다. AI가 내용을 누락하면 `정보 부족: 검토 후 직접 작성해 주세요.`로 표시하므로 반드시 보완하세요. 잘못된 JSON 등 처리할 수 없는 응답은 오류로 안내합니다. 제안된 테스트 방법은 실제 테스트 실행 증거가 아닙니다.

## 5. 보안·비용·오류 안내

- 파일 목록과 diff가 지정한 외부 API로 전송됩니다. 기본 전송 대상은 `copa.codyssey.kr`입니다. 전송 전 `python main.py`로 내용을 확인하고 비밀번호, 키, 개인정보를 제거하세요.
- `--safe-mode`는 **줄 수만 제한**합니다. 민감정보를 자동으로 가리지 않으며, 처음 200줄에 포함된 정보도 전송됩니다. 일부 변경이 빠져 요약이 불완전해질 수 있습니다.
- `.env`, `.env.*`, `.venv/`는 Git에서 제외합니다. 이미 Git이 추적하는 파일은 `.gitignore`만으로 제외되지 않습니다.
- 생성 명령 한 번당 API를 **1회** 호출하고 호출 횟수를 출력합니다. 자동 재시도와 형식 수정을 위한 재호출은 하지 않습니다. 반복 실행하면 비용이 추가될 수 있습니다.
- 키가 없으면 `AI_API_KEY 환경변수가 설정되지 않았습니다`를 표시합니다. HTTP 401은 키 인증, 429는 요청 한도 또는 잔액을 확인하세요. 네트워크 오류와 30초 응답 시간 초과도 안내합니다.
- AI 결과는 초안입니다. 변경 이유, 제목 의미, 테스트 방법을 검토한 뒤 사용하세요.

## 6. 테스트와 파일 구성

API Key 없이 다음 명령으로 테스트할 수 있습니다. 가짜 API 응답을 사용하므로 실제 API 호출이나 API 서비스 크레딧 차감은 발생하지 않습니다. 임시 Git 저장소는 테스트 후 자동으로 삭제됩니다.

```bash
python -m unittest -v
```

| 파일 | 역할 |
| --- | --- |
| `main.py` | Git 수집, 안전 모드, API 요청, 커밋·PR 출력 |
| `test_main.py` | 임시 저장소와 모의 API 응답을 이용한 자동 테스트 |
| `requirements.txt` | 설치할 외부 라이브러리 목록 |
| `.gitignore` | 비밀 설정과 임시 파일의 Git 추가 방지 |

모의 테스트 통과만으로 실제 API 연결을 확인한 것은 아닙니다. 최종 검증에서는 환경변수에 키를 설정하고, 민감정보 없는 변경으로 `commit`과 `pr` 명령이 실제 결과를 출력하는지 확인해야 합니다.
