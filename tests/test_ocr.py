"""TASK-06 선행 테스트 — OcrReader.suggest_label (DES-07, ADR-001 P-02 재현).

Windows OCR(winocr, ko)이 있을 때만 실행한다. 2026-09-28 실측: 4배 이진화가 지역 6/6을
정독하고, 4배 이진화가 빈 결과인 셀(4위 '맹수')은 4배 확대 폴백이 정독한다.
"""

import importlib.util
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import detect_row_tops
from rankscan.vision.ocr import OcrReader

IMG = Path(__file__).resolve().parents[1] / "img"
OX, OY, CW, CH = 1, 31, 2544, 657


def _cells(box: tuple[int, int, int, int]) -> list[np.ndarray]:
    frame = np.asarray(Image.open(IMG / "ranking_1.png").convert("RGB"))
    client = frame[OY:OY + CH, OX:OX + CW]
    x0, dy0, x1, dy1 = box
    return [np.ascontiguousarray(client[top + dy0:top + dy1, x0:x1])
            for top in detect_row_tops(client)]


@unittest.skipUnless(importlib.util.find_spec("winocr"), "winocr 미설치")
class OcrSuggestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr = OcrReader()

    def test_region_cells_suggest_exact_label(self):
        self.assertEqual([self.ocr.suggest_label(c) for c in _cells(ui.CELL_REGION)], ["사예"] * 6)

    def test_alliance_fallback_to_upscale_when_binarized_is_empty(self):
        cells = _cells(ui.CELL_ALLIANCE)
        self.assertEqual(self.ocr.suggest_label(cells[0]), "잠룡")
        self.assertEqual(self.ocr.suggest_label(cells[3]), "맹수")


if __name__ == "__main__":
    unittest.main()
