"""TASK-07 선행 테스트 — ListScroller.walk 순회 루프 (FR-02·FR-03·FR-04, NFR-01; AC-04·AC-08 오프라인 / DES-04 상세 1~7, ADR-002).

픽스처 프레임(img/, 창 2546×689)을 재생하는 가짜 게임(캡처+입력)으로 순회를 구동한다. 픽스처는
연속 스크롤이 아니므로 휠마다 다음 프레임으로 '점프'시키되 기하는 실측과 일치한다(2026-09-30):
contrib_top(1~6위, anchor 6위 top 559) → w11(5~9위): 6위 띠 재발견 top 318, 이동량 241, NCC 0.910;
contrib_top → b11_r132·end_r595_600: 6위 띠 미발견(NCC 0.28·0.36 → None, 겹침 상실);
w11 → w11: 이동량 0(목록 끝). 순위 충돌 프레임은 w11의 7위 순위 셀에 8위 셀을 덮어 합성한다(판독 '8').
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import ListScroller, WalkAborted
from rankscan.nav.navigator import ScreenJudge
from rankscan.store.datastore import DataStore
from rankscan.vision.row_parser import RowParser

IMG = Path(__file__).resolve().parents[1] / "img"
CLIENT = (2544, 657)
OX, OY = 1, 31   # 창 2546×689 → 클라이언트 (0,0) 오프셋 (img/README.md)
DOWN = (*ui.SCROLL_POINT, -ui.SCROLL_NOTCHES)            # 전진 스크롤 휠
REWIND = (*ui.SCROLL_POINT, ui.SCROLL_NOTCHES // 2)      # 겹침 상실 복구 되감기
REWIND_TOP = (*ui.SCROLL_POINT, ui.SCROLL_NOTCHES * 10)  # 시작 조건 되감기


def _load(name: str) -> np.ndarray:
    return np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))


def _size(path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def _copy_cell(frame: np.ndarray, src_top: int, dst_top: int, box) -> np.ndarray:
    """클라이언트 행 상단 src_top의 셀을 dst_top 행에 덮어쓴 창 프레임 사본."""
    x0, dy0, x1, dy1 = box
    f = frame.copy()
    f[dst_top + dy0 + OY:dst_top + dy1 + OY, x0 + OX:x1 + OX] = \
        frame[src_top + dy0 + OY:src_top + dy1 + OY, x0 + OX:x1 + OX]
    return f


def _blank_cell(frame: np.ndarray, top: int, box) -> np.ndarray:
    x0, dy0, x1, dy1 = box
    f = frame.copy()
    f[top + dy0 + OY:top + dy1 + OY, x0 + OX:x1 + OX] = 0
    return f


FRAMES = {n: _load(n) for n in ("p01_main", "p01_contrib_top", "p01_w1", "p01_w11",
                                "p01_b11_r132", "p01_end_r595_600")}
FRAMES["w11_conflict"] = _copy_cell(FRAMES["p01_w11"], 460, 389, ui.CELL_RANK)   # 7위 셀 ← 8위
FRAMES["top_rank3_blank"] = _blank_cell(FRAMES["p01_contrib_top"], 346, ui.CELL_RANK)


class FakeGame:
    """휠마다 다음 픽스처로 점프하는 가짜 게임 — grab_fresh(캡처)와 click·wheel(입력)을 함께 제공.

    on_wheel 항목: 상태명 또는 (일시 상태명, 그랩 수, 이후 상태명) — 재취득 전의 일시 프레임을
    재현한다(wait_stable은 정지 프레임에서 정확히 3회 grab한다). 메인 화면에서의 귀환 클릭도
    on_wheel의 다음 항목을 소비한다(화면 이탈 복구 재현).
    """

    def __init__(self, state: str, on_wheel=()):
        self.state = state
        self.on_wheel = list(on_wheel)
        self.transient: tuple[str, int] | None = None
        self.wheels: list[tuple[int, int, int]] = []
        self.clicks: list[tuple[int, int]] = []

    def grab_fresh(self) -> np.ndarray:
        if self.transient:
            name, n = self.transient
            self.transient = (name, n - 1) if n > 1 else None
            return FRAMES[name]
        return FRAMES[self.state]

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))
        if self.state == "p01_main" and (x, y) == ui.CLICK_RETURN and self.on_wheel:
            self.state = self.on_wheel.pop(0)

    def wheel(self, x: int, y: int, notches: int) -> None:
        self.wheels.append((x, y, notches))
        if not self.on_wheel:
            return
        nxt = self.on_wheel.pop(0)
        if isinstance(nxt, tuple):
            name, n, after = nxt
            self.transient, self.state = (name, n), after
        else:
            self.state = nxt


class WalkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = DataStore(":memory:")
        self.run = self.store.create_run(600)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _walker(self, game: FakeGame, max_rank: int = 600,
                parser: RowParser | None = None) -> ListScroller:
        parser = parser or RowParser(self.store, self.root, suggest=lambda c: None)
        return ListScroller(ScreenJudge(game, CLIENT), game, parser, self.store, self.run,
                            max_rank=max_rank, captures_dir=self.root / "captures")

    def _rows(self) -> dict[int, dict]:
        return {r["rank"]: dict(r) for r in self.store.export_rows(self.run)}

    def _run_dir(self) -> Path:
        return self.root / "captures" / f"run_{self.run}"

    # (a) AC-08 --max-rank: 첫 화면에서 종료 ---------------------------------

    def test_max_rank_reached_on_first_screen_stops_without_scroll(self):
        game = FakeGame("p01_contrib_top")
        s = self._walker(game, max_rank=6).walk()
        self.assertEqual((s.stop_reason, s.last_rank, s.processed, s.saved, s.failed,
                          s.partial, s.conflicts), ("max_rank", 6, 6, 6, 0, 0, 0))
        self.assertEqual(game.wheels, [])
        rows = self._rows()
        self.assertEqual(sorted(rows), [1, 2, 3, 4, 5, 6])
        self.assertEqual([rows[r]["rank_read"] for r in range(1, 7)],
                         ["1", "2", "3", "4", "5", "6"])
        self.assertEqual([rows[r]["parse_status"] for r in range(1, 7)], ["ok"] * 6)
        # FR-04·NFR-03: 행 크롭(목록 x 전폭 × ROW_HEIGHT)과 단계 프레임(LIST_REGION) 저장·경로 기입
        for r in range(1, 7):
            crop, frame = Path(rows[r]["crop_path"]), Path(rows[r]["frame_path"])
            self.assertEqual(crop, self._run_dir() / f"rank_{r:03d}.png")
            self.assertEqual(frame, self._run_dir() / "frames" / "step_0000.png")
            self.assertTrue(crop.is_file())
        self.assertEqual(_size(rows[1]["crop_path"]),
                         (ui.LIST_REGION[2] - ui.LIST_REGION[0], ui.ROW_HEIGHT))
        self.assertEqual(_size(rows[1]["frame_path"]),
                         (ui.LIST_REGION[2] - ui.LIST_REGION[0],
                          ui.LIST_REGION[3] - ui.LIST_REGION[1]))
        self.assertEqual(list(self._run_dir().glob("error_*.png")), [])   # 전체 프레임은 오류 시에만

    def test_rows_beyond_max_rank_are_not_processed(self):
        s = self._walker(FakeGame("p01_contrib_top"), max_rank=4).walk()
        self.assertEqual((s.stop_reason, s.last_rank, s.processed), ("max_rank", 4, 4))
        self.assertEqual(self.store.ranks_of(self.run), [1, 2, 3, 4])

    # (b) AC-08 상한 없음: 스크롤 후 이동량 0 → 목록 끝 --------------------------

    def test_unmoved_list_after_scroll_ends_walk(self):
        game = FakeGame("p01_contrib_top", on_wheel=["p01_w11", "p01_w11"])
        s = self._walker(game).walk()
        self.assertEqual((s.stop_reason, s.last_rank, s.processed, s.conflicts),
                         ("end", 9, 9, 0))
        self.assertEqual(game.wheels, [DOWN, DOWN])
        rows = self._rows()
        self.assertEqual(sorted(rows), list(range(1, 10)))
        self.assertEqual([rows[r]["rank_read"] for r in range(1, 10)],
                         [str(r) for r in range(1, 10)])
        self.assertEqual(Path(rows[7]["frame_path"]).name, "step_0001.png")

    # (c) 겹침 상실 → 되감기 → 재측정 ------------------------------------------

    def test_lost_overlap_rewinds_and_remeasures(self):
        game = FakeGame("p01_contrib_top", on_wheel=["p01_b11_r132", "p01_w11", "p01_w11"])
        s = self._walker(game).walk()
        self.assertEqual(game.wheels, [DOWN, REWIND, DOWN])
        self.assertEqual((s.stop_reason, s.last_rank), ("end", 9))
        self.assertEqual(self.store.ranks_of(self.run), list(range(1, 10)))

    def test_lost_overlap_twice_aborts_keeping_saved_rows(self):
        game = FakeGame("p01_contrib_top",
                        on_wheel=["p01_b11_r132", "p01_end_r595_600", "p01_b11_r132"])
        w = self._walker(game)
        with self.assertRaises(WalkAborted):
            w.walk()
        self.assertEqual(game.wheels, [DOWN, REWIND, REWIND])
        self.assertEqual(w.summary.stop_reason, "aborted")
        self.assertEqual(self.store.ranks_of(self.run), [1, 2, 3, 4, 5, 6])   # 저장분 유지
        errors = list(self._run_dir().glob("error_*.png"))
        self.assertEqual(len(errors), 1)
        self.assertEqual(_size(errors[0]), (2546, 689))                       # 중단 시 전체 프레임

    # (d) 순위 충돌 → 재취득 1회 → 재발 시 중단 -----------------------------------

    def test_rank_conflict_reacquires_frame_once(self):
        game = FakeGame("p01_contrib_top",
                        on_wheel=[("w11_conflict", 3, "p01_w11"), "p01_w11"])
        s = self._walker(game).walk()
        self.assertEqual((s.stop_reason, s.conflicts, s.last_rank), ("end", 1, 9))
        self.assertEqual(game.wheels, [DOWN, DOWN])
        self.assertEqual(self._rows()[7]["rank_read"], "7")

    def test_rank_conflict_twice_aborts(self):
        game = FakeGame("p01_contrib_top", on_wheel=["w11_conflict"])
        w = self._walker(game)
        with self.assertRaises(WalkAborted) as cm:
            w.walk()
        self.assertIn("7", str(cm.exception))
        self.assertIn("8", str(cm.exception))
        self.assertEqual((w.summary.stop_reason, w.summary.conflicts), ("aborted", 2))
        self.assertEqual(self.store.ranks_of(self.run), [1, 2, 3, 4, 5, 6])   # 충돌 행 미저장

    # (e) 시작 시 1위 아님 → 되감기 -------------------------------------------

    def test_start_below_rank_one_rewinds_to_top(self):
        game = FakeGame("p01_w1", on_wheel=["p01_contrib_top"])
        s = self._walker(game, max_rank=6).walk()
        self.assertEqual(game.wheels, [REWIND_TOP])
        self.assertEqual((s.stop_reason, s.last_rank), ("max_rank", 6))
        self.assertEqual(self.store.ranks_of(self.run), [1, 2, 3, 4, 5, 6])

    def test_start_rewind_fails_twice_aborts(self):
        game = FakeGame("p01_w1")
        w = self._walker(game)
        with self.assertRaises(WalkAborted):
            w.walk()
        self.assertEqual(game.wheels, [REWIND_TOP, REWIND_TOP])
        self.assertEqual(self.store.ranks_of(self.run), [])

    # (f) NFR-01·AC-04: 셀 실패 행은 partial/failed로 저장하고 계속 -------------------

    def test_cell_failure_rows_are_saved_and_walk_continues(self):
        parser = RowParser(self.store, self.root, suggest=lambda c: None)
        orig = parser.parse

        def parse(frame, top, rank):
            row = orig(frame, top, rank)
            if rank == 5:
                row.parse_status = "failed"     # 전 셀 실패 행 모사
            return row

        parser.parse = parse
        s = self._walker(FakeGame("top_rank3_blank"), max_rank=6, parser=parser).walk()
        self.assertEqual((s.processed, s.saved, s.failed, s.partial, s.stop_reason),
                         (6, 5, 1, 1, "max_rank"))
        rows = self._rows()
        self.assertEqual([rows[r]["parse_status"] for r in range(1, 7)],
                         ["ok", "ok", "partial", "ok", "failed", "ok"])
        self.assertEqual(rows[3]["rank_read"], "")
        for r in range(1, 7):
            self.assertTrue(Path(rows[r]["crop_path"]).is_file())        # 실패 행도 크롭 보존

    # 랭킹 화면 이탈 → 귀환 1회 ---------------------------------------------

    def test_screen_loss_recovers_with_one_return_click(self):
        game = FakeGame("p01_contrib_top", on_wheel=["p01_main", "p01_w11", "p01_w11"])
        s = self._walker(game).walk()
        self.assertEqual(game.clicks, [ui.CLICK_RETURN])
        self.assertEqual((s.stop_reason, s.last_rank), ("end", 9))

    def test_screen_loss_persisting_after_return_aborts(self):
        game = FakeGame("p01_contrib_top", on_wheel=["p01_main"])
        w = self._walker(game)
        with self.assertRaises(WalkAborted):
            w.walk()
        self.assertEqual(game.clicks, [ui.CLICK_RETURN])
        self.assertEqual(self.store.ranks_of(self.run), [1, 2, 3, 4, 5, 6])


if __name__ == "__main__":
    unittest.main()
