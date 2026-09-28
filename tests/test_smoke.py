"""TASK-01 선행 테스트 — 패키지 설치·플랫폼 계층 임포트·창 탐색 계약(FR-09, DES-01)."""

import unittest


class SmokeTest(unittest.TestCase):
    def test_import_package(self):
        import rankscan  # noqa: F401

    def test_import_win_layer(self):
        from rankscan.win import capture, input, session, win32  # noqa: F401

    def test_find_client_windows_returns_list(self):
        from rankscan.win.session import find_client_windows
        self.assertIsInstance(find_client_windows(), list)


if __name__ == "__main__":
    unittest.main()
