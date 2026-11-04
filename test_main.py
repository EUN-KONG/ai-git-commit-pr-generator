"""실제 임시 Git 저장소에서 변경 수집 동작을 확인합니다."""

import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from main import format_commit, generate_text, main


SCRIPT = Path(__file__).with_name("main.py")


class GitCollectionTests(unittest.TestCase):
    def setUp(self):
        # 사용자의 저장소를 건드리지 않고 테스트 전용 저장소를 만듭니다.
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True
        )

    def cli(self, folder=None, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=folder or self.root,
            capture_output=True, text=True,
        )

    def test_clean_repository(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("변경 사항이 없습니다", result.stdout)

    def test_untracked_file(self):
        (self.root / "새 파일.txt").write_text("hello", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("??", result.stdout)
        self.assertIn("git add", result.stdout)

    def test_staged_and_unstaged_changes(self):
        # 첫 커밋 없이도 새로 추가한 내용과 이후 수정한 내용을 모두 읽어야 합니다.
        file = self.root / "sample.txt"
        file.write_text("staged\n", encoding="utf-8")
        self.git("add", "sample.txt")
        file.write_text("staged\nunstaged\n", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("+staged", result.stdout)
        self.assertIn("+unstaged", result.stdout)

    def test_subdirectory_rejected(self):
        folder = self.root / "sub"
        folder.mkdir()
        result = self.cli(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("루트", result.stderr)

    def test_safe_mode_limits_large_diff(self):
        # 제한을 넘는 실제 diff에서 뒷부분이 빠지는지 확인합니다.
        file = self.root / "large.txt"
        file.write_text("".join(f"line-{i}\n" for i in range(250)), encoding="utf-8")
        self.git("add", "large.txt")
        normal = self.cli()
        safe = self.cli(None, "--safe-mode")
        self.assertEqual(safe.returncode, 0)
        self.assertIn("+line-249", normal.stdout)
        self.assertNotIn("+line-249", safe.stdout)
        diff = safe.stdout.split("--- 변경 내용 (Git diff) ---\n", 1)[1]
        self.assertEqual(len(diff.splitlines()), 200)

    def test_safe_mode_preserves_small_diff(self):
        (self.root / "small.txt").write_text("hello\n", encoding="utf-8")
        self.git("add", "small.txt")
        normal = self.cli()
        safe = self.cli(None, "-safe-mode")
        marker = "--- 변경 내용 (Git diff) ---\n"
        self.assertEqual(safe.returncode, 0)
        self.assertEqual(normal.stdout.split(marker)[1], safe.stdout.split(marker)[1])

    def test_safe_mode_clean_repository(self):
        result = self.cli(None, "--safe-mode")
        self.assertEqual(result.returncode, 0)
        self.assertIn("변경 사항이 없습니다", result.stdout)

    def test_commit_clean_repository(self):
        result = self.cli(None, "commit")
        self.assertEqual(result.returncode, 0)
        self.assertIn("변경 사항이 없습니다", result.stdout)

    def test_non_repository_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.cli(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[ERROR]", result.stderr)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(model="test-model", temperature=0.3, max_tokens=123)
        # 본인 키 대신 가짜 환경변수와 모의 HTTP 응답으로 무료 테스트합니다.
        env = patch.dict("os.environ", {"AI_API_KEY": "test-only"})
        env.start()
        self.addCleanup(env.stop)
        post = patch("main.requests.post")
        self.post = post.start()
        self.addCleanup(post.stop)

    def test_success_and_request_options(self):
        self.post.return_value = Mock(ok=True)
        self.post.return_value.json.return_value = {
            "choices": [{"message": {"content": " 변경 요약 "}, "finish_reason": "stop"}]
        }
        self.assertEqual(generate_text("M a", "+hello", self.args), "변경 요약")
        self.post.assert_called_once()
        body = self.post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["temperature"], 0.3)
        self.assertEqual(body["max_completion_tokens"], 123)
        self.assertIn("+hello", body["messages"][1]["content"])

    def test_missing_key(self):
        with patch.dict("os.environ", {"AI_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "환경변수"):
                generate_text("M a", "+hello", self.args)
        self.post.assert_not_called()

    def test_http_errors(self):
        for code in (400, 401, 429, 500):
            with self.subTest(code=code):
                self.post.return_value = Mock(ok=False, status_code=code)
                with self.assertRaisesRegex(ValueError, f"HTTP {code}"):
                    generate_text("M a", "+hello", self.args)

    def test_network_errors(self):
        for error, message in ((requests.Timeout(), "시간 초과"),
                               (requests.ConnectionError(), "네트워크")):
            with self.subTest(message=message):
                self.post.side_effect = error
                with self.assertRaisesRegex(ValueError, message):
                    generate_text("M a", "+hello", self.args)

    def test_invalid_and_empty_responses(self):
        self.post.return_value = Mock(ok=True)
        for data in ({}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}):
            with self.subTest(data=data):
                self.post.return_value.json.return_value = data
                with self.assertRaises(ValueError):
                    generate_text("M a", "+hello", self.args)

    def test_truncated_response(self):
        self.post.return_value = Mock(ok=True)
        self.post.return_value.json.return_value = {"choices": [{"finish_reason": "length"}]}
        with self.assertRaisesRegex(ValueError, "토큰 한도"):
            generate_text("M a", "+hello", self.args)

    def test_commit_command_with_safe_mode(self):
        self.post.return_value = Mock(ok=True)
        self.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "feat: 변경 수집 추가\n\n불필요한 본문"}}]
        }
        # CLI 입구부터 출력까지 실행하며, 전송한 diff 제한도 확인합니다.
        with patch("sys.argv", ["main.py", "commit", "--safe-mode"]), \
                patch("main.collect_changes", return_value=(" M a\n", "change\n" * 250)), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(), 0)
        self.post.assert_called_once()
        body = self.post.call_args.kwargs["json"]
        self.assertEqual(body["messages"][1]["content"].count("change\n"), 200)
        self.assertIn("커밋 제목 한 줄", body["messages"][0]["content"])
        self.assertIn("--- Commit Message ---\nfeat: 변경 수집 추가\n", output.getvalue())
        self.assertNotIn("불필요한 본문", output.getvalue())


class CommitFormatTests(unittest.TestCase):
    def test_title_only(self):
        self.assertEqual(format_commit('\n```text\n"feat: 기능 추가"\n본문\n```'), "feat: 기능 추가")

    def test_length_limits(self):
        for length in (50, 51, 72, 73, 100):
            with self.subTest(length=length), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(len(format_commit("가" * length)), min(length, 72))

    def test_empty_title_rejected(self):
        for text in ("", " \n", "```\n```", '""'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                format_commit(text)


if __name__ == "__main__":
    unittest.main()
