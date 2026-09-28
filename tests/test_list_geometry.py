"""TASK-03 선행 테스트 — 행 검출·이동량 측정·순위 이어붙임 (FR-02·FR-03; ADR-002 1·2·6, DES-04 2·3·6).

픽스처(img/, 창 2546×689 캡처)를 클라이언트 영역(2544×657)으로 잘라 순수 함수에 넣는다.
기대값은 계획 TASK-03 검증 방법과 2026-09-28 픽스처 실측(작업 기록 TASK-03 참조).
행 상단선은 부화소 렌더링으로 2px에 걸칠 수 있어(예: contrib_top 6위 559/560,
w1 6위 526/527) 프레임 간 위치 비교는 ±1을 허용하고, 한 프레임 안의 검출값은 정확히 고정한다.
"""

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import (anchor_band, assign_ranks, detect_row_tops,
                                        measure_shift)

IMG = Path(__file__).resolve().parents[1] / "img"
OX, OY = 1, 31          # 창 2546×689 → 클라이언트 (0,0) 오프셋 (img/README.md)
CW, CH = 2544, 657


def _client(name: str) -> np.ndarray:
    frame = np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))
    return frame[OY:OY + CH, OX:OX + CW]


FIX = {n: _client(n) for n in ("p01_contrib_top", "p01_w1", "p01_w2", "p01_w11",
                               "p01_b10_r121", "p01_b11_r132", "p01_end_r595_600")}


class RowTopDetectionTest(unittest.TestCase):
    def test_contrib_top_has_six_full_rows(self):
        self.assertEqual(detect_row_tops(FIX["p01_contrib_top"]),
                         [203, 275, 346, 417, 488, 559])

    def test_end_screen_has_six_full_rows(self):
        self.assertEqual(detect_row_tops(FIX["p01_end_r595_600"]),
                         [202, 273, 344, 415, 486, 558])

    def test_w1_excludes_bottom_clipped_row(self):
        # 1위는 상단 밖(170), 7위 상단선은 598에 보이지만 하단이 목록 영역 밖 → 완전 가시 5행
        self.assertEqual(detect_row_tops(FIX["p01_w1"]), [242, 313, 384, 455, 527])

    def test_every_fixture_rows_fit_region_one_pitch_apart(self):
        for name, client in FIX.items():
            tops = detect_row_tops(client)
            with self.subTest(name):
                self.assertGreaterEqual(len(tops), 5)
                self.assertGreaterEqual(tops[0], ui.LIST_REGION[1])
                self.assertLessEqual(tops[-1] + ui.ROW_HEIGHT, ui.LIST_REGION[3])
                for a, b in zip(tops, tops[1:]):
                    self.assertAlmostEqual(b - a, ui.ROW_PITCH, delta=1)

    def test_blank_frame_has_no_rows(self):
        self.assertEqual(detect_row_tops(np.zeros((CH, CW, 3), np.uint8)), [])


class ShiftMeasurementTest(unittest.TestCase):
    def test_one_notch_moves_rows_up_33px(self):
        for prev, nxt in (("p01_contrib_top", "p01_w1"), ("p01_w1", "p01_w2")):
            top = detect_row_tops(FIX[prev])[-1]          # anchor = 마지막 완전 가시 행
            with self.subTest(f"{prev}->{nxt}"):
                shift = measure_shift(anchor_band(FIX[prev], top), top, FIX[nxt])
                self.assertEqual(shift, 33)

    def test_lost_overlap_returns_none(self):
        # 50노치 버스트: 121~125위 → 132~136위. anchor(125위) 행이 새 프레임에 없다.
        b10 = FIX["p01_b10_r121"]
        top = detect_row_tops(b10)[-1]
        self.assertIsNone(measure_shift(anchor_band(b10, top), top, FIX["p01_b11_r132"]))

    def test_unchanged_frame_measures_zero(self):
        w1 = FIX["p01_w1"]
        top = detect_row_tops(w1)[-1]
        self.assertEqual(measure_shift(anchor_band(w1, top), top, w1), 0)


class RankAssignmentTest(unittest.TestCase):
    def test_first_frame_anchor_is_rank_one(self):
        tops = [203, 275, 346, 417, 488, 559]
        self.assertEqual(assign_ranks((1, 203), tops), list(zip(range(1, 7), tops)))

    def test_rows_above_anchor_count_down_from_anchor_rank(self):
        # contrib_top 6위(559)가 w1에서 33px 위(526)로 재발견된 뒤 — w1 완전 가시 행은 2~6위
        tops = [242, 313, 384, 455, 527]
        self.assertEqual([r for r, _ in assign_ranks((6, 526), tops)], [2, 3, 4, 5, 6])

    def test_rounding_absorbs_fractional_pitch(self):
        # 실측 행 간격 71.2 → 5행 아래는 356px(정수 ROW_PITCH 71×5와 1px 차)
        self.assertEqual(assign_ranks((1, 203), [203 + 356]), [(6, 559)])


if __name__ == "__main__":
    unittest.main()
