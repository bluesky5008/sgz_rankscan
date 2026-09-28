"""TASK-02 선행 테스트 — 마커 판별 + RankingNavigator 단계 로직 (FR-01, NFR-02; AC-01 오프라인).

픽스처: img/p01_main(메인), p01_menu(더 보기 메뉴 열림), p01_contrib_top·ranking_1
(공헌 탭 활성). 랭킹 화면에서 다른 탭이 활성인 상태는 저장소 픽스처가 없어
contrib_top의 활성 탭 상자에 좌측 비활성 탭('동맹 랭킹') 띠를 덮어 합성한다
(플로우 테스트 전용 — 실기 판정은 TASK-08).
"""

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.navigator import ScreenJudge, WrongScreen, ui_template
from rankscan.nav.ranking import RankingNavigator

IMG = Path(__file__).resolve().parents[1] / "img"
CLIENT = (2544, 657)
OX, OY = 1, 31   # 창 2546×689 → 클라이언트 (0,0) 오프셋 (img/README.md)


def _load(name: str) -> np.ndarray:
    return np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))


def _ranking_other_tab(contrib: np.ndarray) -> np.ndarray:
    """공헌 탭 비활성 합성: 활성 탭 상자에 같은 폭만큼 좌측의 비활성 탭 띠를 복사."""
    f = contrib.copy()
    x0, y0, x1, y1 = ui.MARKER_CONTRIB_TAB[1]
    w = x1 - x0
    f[y0 + OY:y1 + OY, x0 + OX:x1 + OX] = contrib[y0 + OY:y1 + OY, x0 + OX - w:x1 + OX - w]
    return f


FRAMES = {n: _load(n) for n in ("p01_main", "p01_menu", "p01_contrib_top", "ranking_1")}
FRAMES["ranking_other_tab"] = _ranking_other_tab(FRAMES["p01_contrib_top"])
FRAMES["unknown"] = np.zeros_like(FRAMES["p01_main"])

MARKERS = {"MAIN": ui.MARKER_MAIN, "MENU": ui.MARKER_MENU,
           "RANKING": ui.MARKER_RANKING, "TAB": ui.MARKER_CONTRIB_TAB}
# 마커별 임계 이상이어야 하는 픽스처 — 그 외에는 임계 미만이어야 한다.
# MAIN(더 보기 버튼)은 메뉴 열림 중에도 보인다(sgz_statiz 2026-08-09 실기와 동일).
EXPECT_ON = {"MAIN": {"p01_main", "p01_menu"},
             "MENU": {"p01_menu"},
             "RANKING": {"p01_contrib_top", "ranking_1", "ranking_other_tab"},
             "TAB": {"p01_contrib_top", "ranking_1"}}


class FakeGame:
    """클릭 → 화면 전이 상태 기계. grab_fresh는 현재 화면 픽스처를 반환한다."""

    TRANSITIONS = {ui.CLICK_MORE: {"p01_main": "p01_menu"},
                   ui.CLICK_MENU_RANKING: {"p01_menu": "ranking_other_tab"},
                   ui.CLICK_CONTRIB_TAB: {"ranking_other_tab": "p01_contrib_top"}}

    def __init__(self, state: str):
        self.state = state
        self.clicks: list[tuple[int, int]] = []

    def grab_fresh(self) -> np.ndarray:
        return FRAMES[self.state]

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))
        nxt = self.TRANSITIONS.get((x, y), {}).get(self.state)
        if nxt:
            self.state = nxt


def _nav(state: str) -> tuple[RankingNavigator, FakeGame]:
    game = FakeGame(state)
    return RankingNavigator(ScreenJudge(game, CLIENT), game), game


class MarkerDiscriminationTest(unittest.TestCase):
    def test_each_marker_fires_only_on_its_screens(self):
        judge = ScreenJudge(capture=None, client_size=CLIENT)
        for mname, (fname, rect) in MARKERS.items():
            tpl = ui_template(fname)
            for n, frame in FRAMES.items():
                score = judge.marker_score(frame, rect, tpl)
                if n in EXPECT_ON[mname]:
                    self.assertGreaterEqual(score, ui.MARKER_NCC_THRESHOLD,
                                            f"{mname} on {n}")
                else:
                    self.assertLess(score, ui.MARKER_NCC_THRESHOLD,
                                    f"{mname} on {n}")


class NavigatorFlowTest(unittest.TestCase):
    def test_from_main_clicks_three_times(self):
        nav, game = _nav("p01_main")
        nav.goto_contrib_tab()
        self.assertEqual(game.state, "p01_contrib_top")
        self.assertEqual(game.clicks, [ui.CLICK_MORE, ui.CLICK_MENU_RANKING,
                                       ui.CLICK_CONTRIB_TAB])

    def test_from_open_menu_skips_more_click(self):
        nav, game = _nav("p01_menu")
        nav.goto_contrib_tab()
        self.assertEqual(game.state, "p01_contrib_top")
        self.assertEqual(game.clicks, [ui.CLICK_MENU_RANKING, ui.CLICK_CONTRIB_TAB])

    def test_from_ranking_other_tab_clicks_tab_only(self):
        nav, game = _nav("ranking_other_tab")
        nav.goto_contrib_tab()
        self.assertEqual(game.state, "p01_contrib_top")
        self.assertEqual(game.clicks, [ui.CLICK_CONTRIB_TAB])

    def test_already_on_contrib_tab_skips_navigation(self):
        nav, game = _nav("p01_contrib_top")
        frame = nav.goto_contrib_tab()
        self.assertEqual(game.clicks, [])
        self.assertTrue(np.array_equal(frame, FRAMES["p01_contrib_top"]))

    def test_swallowed_click_is_retried_once(self):
        game = FakeGame("p01_menu")
        swallow = {ui.CLICK_CONTRIB_TAB}
        orig_click = game.click

        def flaky_click(x, y):
            if (x, y) in swallow:
                swallow.discard((x, y))
                game.clicks.append((x, y))   # 클릭은 보냈지만 게임이 무시
                return
            orig_click(x, y)

        game.click = flaky_click
        nav = RankingNavigator(ScreenJudge(game, CLIENT), game)
        nav.step_timeout = 0.3               # 테스트용 짧은 대기
        nav.goto_contrib_tab()
        self.assertEqual(game.state, "p01_contrib_top")
        self.assertEqual(game.clicks.count(ui.CLICK_CONTRIB_TAB), 2)

    def test_wrong_screen_aborts_without_click(self):
        nav, game = _nav("unknown")
        with self.assertRaises(WrongScreen):
            nav.goto_contrib_tab()
        self.assertEqual(game.clicks, [])


if __name__ == "__main__":
    unittest.main()
