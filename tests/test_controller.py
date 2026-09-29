"""TASK-01·07 선행 테스트 — 창 후보 선택(FR-09, AC-07 단위), run_scan 오케스트레이션·실행 요약·
라벨 확정(FR-06·FR-07·FR-08, DES-10), CLI 명령 노출·export 기본 run.

출처: sgz_statiz tests/test_controller.py (2026-09-28 ChooseWindowTest 이식, 2026-09-30
RunScan·LabelFlow·Summary 이식 — 순회는 test_list_scroller의 가짜 게임으로 픽스처 재생).
창 선택 입력 규약: 번호=선택(전면 표시 후 y/n 확인), q=중단. 후보 1개면 묻지 않는다.
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from rankscan.cli import main
from rankscan.controller import choose_window, label_pending, run_scan, summarize_run
from rankscan.nav.list_scroller import ListScroller
from rankscan.nav.navigator import ScreenJudge, WrongScreen
from rankscan.store.datastore import DataStore, RankRow
from rankscan.vision.row_parser import RowParser
from rankscan.win.session import WindowInfo
from test_list_scroller import CLIENT, FakeGame


def _win(hwnd: int) -> WindowInfo:
    return WindowInfo(hwnd=hwnd, title="삼국지-전략판", pid=1000 + hwnd,
                      rect=(10 * hwnd, 20, 2546, 689), client=(2544, 657),
                      elevated=True)


def _row(rank: int, status: str = "ok") -> RankRow:
    return RankRow(rank, None, None, None, None, None, None, str(rank), None, None, status)


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


class NavOk:
    def goto_contrib_tab(self):
        return None


class RunScanTest(unittest.TestCase):
    """run_scan — 내비게이터 스텁, 순회는 가짜 게임(픽스처 재생)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = DataStore(":memory:")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _factory(self, game: FakeGame, max_rank: int):
        judge = ScreenJudge(game, CLIENT)
        parser = RowParser(self.store, self.root, suggest=lambda c: None)
        return lambda run_id: ListScroller(judge, game, parser, self.store, run_id,
                                           max_rank=max_rank,
                                           captures_dir=self.root / "captures")

    def test_success_records_run_and_returns_zero(self):
        code, text = run_scan(self.store, NavOk(),
                              self._factory(FakeGame("p01_contrib_top"), 6), max_rank=6)
        self.assertEqual(code, 0)
        run = self.store.get_run(1)
        self.assertEqual((run["status"], run["max_rank"], run["processed"], run["saved"],
                          run["failed"]), ("done", 6, 6, 6, 0))
        for token in ("run #1 done", "1~6위", "처리 6", "저장 6", "실패 0",
                      "pending", "rankscan label"):
            self.assertIn(token, text)

    def test_navigation_failure_aborts_run_with_exit_2(self):
        class NavFail:
            def goto_contrib_tab(self):
                raise WrongScreen("테스트")

        code, text = run_scan(self.store, NavFail(),
                              self._factory(FakeGame("p01_contrib_top"), 6), max_rank=6)
        self.assertEqual(code, 2)
        run = self.store.get_run(1)
        self.assertEqual(run["status"], "aborted")
        self.assertIn("WrongScreen", run["note"])
        self.assertIn("테스트", run["note"])
        self.assertEqual(self.store.ranks_of(1), [])
        self.assertIn("aborted", text)

    def test_walk_abort_keeps_saved_rows_and_notes_reason(self):
        game = FakeGame("p01_contrib_top", on_wheel=["w11_conflict"])
        code, text = run_scan(self.store, NavOk(), self._factory(game, 600), max_rank=600)
        self.assertEqual(code, 2)
        run = self.store.get_run(1)
        self.assertEqual((run["status"], run["processed"]), ("aborted", 6))
        self.assertIn("순위 충돌", run["note"])
        self.assertEqual(self.store.ranks_of(1), [1, 2, 3, 4, 5, 6])
        self.assertIn("순위 충돌", text)                 # FR-08 연속성 이상 보고


class LabelFlowTest(unittest.TestCase):
    def setUp(self):
        self.store = DataStore(":memory:")
        self.a = self.store.create_identity("user", "演김부선?", "user/u1.png")
        self.b = self.store.create_identity("alliance", None, "alliance/a1.png")
        self.c = self.store.create_identity("region", "사예", "region/r1.png")

    def tearDown(self):
        self.store.close()

    def _labels(self):
        return {r["identity_id"]: (r["label"], r["label_status"])
                for ns in ("user", "region", "alliance")
                for r in self.store.iter_identities(ns)}

    def test_confirm_skip_and_remaining(self):
        inputs = iter(["演김부선", ""])            # 확정, 건너뜀 → 나머지 순회 종료
        done = label_pending(self.store, lambda prompt: next(inputs, "q"))
        self.assertEqual(done, 1)
        labels = self._labels()
        self.assertEqual(labels[self.a], ("演김부선", "confirmed"))
        self.assertEqual(labels[self.b][1], "pending")
        self.assertEqual(labels[self.c][1], "pending")

    def test_quit_immediately(self):
        done = label_pending(self.store, lambda prompt: "q")
        self.assertEqual(done, 0)
        self.assertEqual(len(self.store.pending_identities()), 3)

    def test_prompt_shows_suggestion_and_template(self):
        prompts = []

        def ask(prompt):
            prompts.append(prompt)
            return "q"

        label_pending(self.store, ask)
        self.assertIn("演김부선?", prompts[0])    # OCR 제안 라벨 노출
        self.assertIn("user/u1.png", prompts[0])  # 크롭(템플릿) 경로 노출

    def test_namespace_filter_limits_prompts(self):
        prompts = []

        def ask(prompt):
            prompts.append(prompt)
            return ""

        label_pending(self.store, ask, namespace="alliance")
        self.assertEqual(len(prompts), 1)
        self.assertIn(f"alliance#{self.b}", prompts[0])


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.store = DataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_reports_range_counts_missing_note_and_pending(self):
        """FR-08: 처리 순위 범위, 저장·실패 수와 사유(partial/failed), 순위 연속성 이상(결측·비고),
        pending 식별자 수."""
        run = self.store.create_run(max_rank=10)
        for rank, status in ((1, "ok"), (2, "ok"), (3, "partial"), (5, "failed")):
            self.store.upsert_row(run, _row(rank, status))
        self.store.create_identity("user", "제안?", "user/u.png")
        self.store.finish_run(run, "aborted", processed=4, saved=3, failed=1,
                              note="순위 충돌 재발: 6위 판독 '7'")
        text = summarize_run(self.store, run)
        for token in ("run #1 aborted", "1~5위", "처리 4", "저장 3", "실패 1", "partial 1",
                      "결측 1", "[4]", "순위 충돌 재발", "pending 1", "rankscan label"):
            self.assertIn(token, text)

    def test_empty_run(self):
        run = self.store.create_run()
        self.store.finish_run(run)
        text = summarize_run(self.store, run)
        self.assertIn("run #1 done", text)
        self.assertIn("없음", text)
        self.assertNotIn("결측", text)
        self.assertNotIn("pending", text)


class CliTest(unittest.TestCase):
    def test_help_lists_scan_probe_export_label(self):
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        for cmd in ("scan", "probe", "export", "label"):
            self.assertIn(cmd, buf.getvalue())

    def test_export_defaults_to_latest_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            db, out = str(Path(tmp) / "rankscan.db"), Path(tmp) / "export"
            with DataStore(db) as store:
                store.create_run()
                r2 = store.create_run()
                store.upsert_row(r2, _row(1))
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["export", "--db", db, "--out", str(out)])
            self.assertEqual(code, 0)
            files = [p.name for p in out.glob("*.csv")]
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].startswith(f"ranks_{r2}_"), files[0])
            self.assertIn(files[0], buf.getvalue())

    def test_export_without_runs_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db, out = str(Path(tmp) / "rankscan.db"), Path(tmp) / "export"
            DataStore(db).close()
            with redirect_stdout(io.StringIO()):
                code = main(["export", "--db", db, "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
