"""TASK-04 선행 테스트 — 순위 셀 숫자 판독 (FR-03; ADR-002 3, DES-08).

픽스처(img/, 창 2546×689 캡처)를 클라이언트 영역(2544×657)으로 잘라 행 상단을 검출하고
CELL_RANK 상자를 RankDigitReader에 넣는다. 기대 순위는 2026-09-28 순위 셀 몽타주 확인값
(작업 기록 TASK-03·04). 1~3위는 금·은·동 메달 숫자, 4위 이후는 흰색 숫자다.
"""

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import detect_row_tops
from rankscan.vision.digits import RankDigitReader

IMG = Path(__file__).resolve().parents[1] / "img"
OX, OY = 1, 31          # 창 2546×689 → 클라이언트 (0,0) 오프셋 (img/README.md)
CW, CH = 2544, 657

EXPECTED = {
    "p01_contrib_top": ["1", "2", "3", "4", "5", "6"],
    "p01_w2": ["2", "3", "4", "5", "6", "7"],
    "p01_w11": ["5", "6", "7", "8", "9"],
    "p01_b10_r121": ["121", "122", "123", "124", "125"],
    "p01_b11_r132": ["132", "133", "134", "135", "136"],
    "p01_end_r595_600": ["595", "596", "597", "598", "599", "600"],
}


def _client(name: str) -> np.ndarray:
    frame = np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))
    return frame[OY:OY + CH, OX:OX + CW]


def _rank_cell(client: np.ndarray, top: int) -> np.ndarray:
    x0, dy0, x1, dy1 = ui.CELL_RANK
    return client[top + dy0:top + dy1, x0:x1]


class RankCellReadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = RankDigitReader()

    def test_reads_every_fixture_rank_cell_exactly(self):
        for name, expected in EXPECTED.items():
            client = _client(name)
            tops = detect_row_tops(client)
            self.assertEqual(len(tops), len(expected), name)
            for top, exp in zip(tops, expected):
                with self.subTest(f"{name} rank {exp}"):
                    self.assertEqual(self.reader.read_rank(_rank_cell(client, top)), exp)

    def test_blank_cell_reads_empty(self):
        x0, dy0, x1, dy1 = ui.CELL_RANK
        self.assertEqual(self.reader.read_rank(np.zeros((dy1 - dy0, x1 - x0, 3), np.uint8)), "")


if __name__ == "__main__":
    unittest.main()
