"""TASK-01 선행 테스트 — 창 후보 선택 절차(FR-09, AC-07 단위).

출처: sgz_statiz tests/test_controller.py ChooseWindowTest (2026-09-28 이식).
입력 규약: 번호=선택(전면 표시 후 y/n 확인), q=중단. 후보 1개면 묻지 않는다.
"""

import unittest

from rankscan.controller import choose_window
from rankscan.win.session import WindowInfo


def _win(hwnd: int) -> WindowInfo:
    return WindowInfo(hwnd=hwnd, title="삼국지-전략판", pid=1000 + hwnd,
                      rect=(10 * hwnd, 20, 2546, 689), client=(2544, 657),
                      elevated=True)


class ChooseWindowTest(unittest.TestCase):
    def setUp(self):
        self.wins = [_win(1), _win(2)]
        self.raised: list[int] = []

    def _ask(self, answers: list[str]):
        it = iter(answers)
        prompts: list[str] = []

        def ask(prompt: str) -> str:
            prompts.append(prompt)
            return next(it)

        ask.prompts = prompts
        return ask

    def test_single_candidate_returned_without_prompt(self):
        def ask(prompt):
            raise AssertionError("후보 1개에서는 묻지 않아야 한다")
        self.assertIs(choose_window([self.wins[0]], ask, self.raised.append),
                      self.wins[0])
        self.assertEqual(self.raised, [])

    def test_select_confirm_returns_choice_and_brings_front(self):
        ask = self._ask(["2", "y"])
        got = choose_window(self.wins, ask, self.raised.append)
        self.assertIs(got, self.wins[1])
        self.assertEqual(self.raised, [2])          # 확인 전 전면 표시
        self.assertIn("0x1", ask.prompts[0])        # 후보 목록이 프롬프트에 나열
        self.assertIn("0x2", ask.prompts[0])

    def test_reject_confirmation_reprompts(self):
        ask = self._ask(["1", "n", "2", "y"])
        got = choose_window(self.wins, ask, self.raised.append)
        self.assertIs(got, self.wins[1])
        self.assertEqual(self.raised, [1, 2])

    def test_quit_returns_none(self):
        self.assertIsNone(choose_window(self.wins, self._ask(["q"]),
                                        self.raised.append))
        self.assertEqual(self.raised, [])

    def test_invalid_input_reprompts(self):
        ask = self._ask(["abc", "9", "2", "y"])
        got = choose_window(self.wins, ask, self.raised.append)
        self.assertIs(got, self.wins[1])
        self.assertEqual(self.raised, [2])

    def test_eof_means_noninteractive_abort(self):
        """stdin이 NUL 장치면 isatty()가 True인 Windows 특성으로 비대화형 가드가
        뚫린다 — EOF는 트레이스백 없이 중단(None)."""
        def ask(prompt):
            raise EOFError
        self.assertIsNone(choose_window(self.wins, ask, self.raised.append))


if __name__ == "__main__":
    unittest.main()
