"""Git 변경 사항을 읽는 터미널 프로그램."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(*args):
    # 명령을 문자열로 합치지 않아 파일명이 명령으로 실행되지 않게 합니다.
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git 명령 실행에 실패했습니다.")
    return result.stdout


def collect_changes():
    # Git 상태의 상대 경로가 일관되도록 저장소 맨 위에서 실행합니다.
    root = run_git("rev-parse", "--show-toplevel").strip()
    if Path.cwd().resolve() != Path(root).resolve():
        raise ValueError("프로젝트 루트 디렉터리에서 실행해 주세요.")

    status = run_git("status", "--short", "--untracked-files=all")
    # git add 전후 변경을 모두 모읍니다. 외부 diff 프로그램은 실행하지 않습니다.
    diff = run_git("diff", "--no-ext-diff", "--no-textconv", "--no-color")
    staged = run_git(
        "diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color"
    )
    return status, diff + staged


def main():
    parser = argparse.ArgumentParser(description="Git 변경 사항을 확인합니다.")
    parser.add_argument(
        "--safe-mode", "-safe-mode", action="store_true",
        help="diff를 처음 200줄까지만 사용합니다. 민감정보를 자동 제거하지는 않습니다.",
    )
    args = parser.parse_args()
    try:
        status, diff = collect_changes()
        if not status:
            print("[INFO] 변경 사항이 없습니다.")
            return 0
        print("--- 변경된 파일 (Git status) ---")
        print(status, end="")
        if args.safe_mode:
            # 이후 AI에 보낼 내용도 이 diff를 사용하도록 출력 전에 제한합니다.
            lines = diff.splitlines(keepends=True)
            diff = "".join(lines[:200])
            print(f"[INFO] 안전 모드: diff {len(lines)}줄 중 {min(len(lines), 200)}줄 사용 (최대 200줄)")
        print("--- 변경 내용 (Git diff) ---")
        print(diff or "[INFO] 추적 중인 파일의 변경 내용이 없습니다.", end="" if diff else "\n")
        if any(line.startswith("??") for line in status.splitlines()):
            print("[INFO] 새 파일의 내용은 git add <파일명> 실행 후 수집됩니다.")
        return 0
    except (ValueError, OSError) as error:
        # 실패 원인을 보여주고 종료 코드로도 실패를 알립니다.
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
