"""실제 임시 Git 저장소에서 변경 수집 동작을 확인합니다."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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

    def cli(self, folder=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT)], cwd=folder or self.root,
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

    def test_non_repository_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.cli(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[ERROR]", result.stderr)


if __name__ == "__main__":
    unittest.main()
