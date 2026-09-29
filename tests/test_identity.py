"""TASK-06 선행 테스트 — IdentityMatcher (FR-05·FR-07, ADR-001, DES-06).

픽스처(img/, 창 2546×689)를 클라이언트 영역으로 잘라 행 상단을 검출하고 셀 상자를 자른다.
정답은 2026-09-28 셀 몽타주 육안 확인값(작업 기록 TASK-06): 1~9위는 모든 프레임이 같은
세션이라 순위가 곧 유저, 지역은 전부 '사예', 동맹은 1·2·3·5·8위 잠룡, 598위 삼룡.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import detect_row_tops
from rankscan.store.datastore import DataStore
from rankscan.vision.identity import IdentityMatcher

IMG = Path(__file__).resolve().parents[1] / "img"
OX, OY, CW, CH = 1, 31, 2544, 657
RANKS = {
    "p01_contrib_top": [1, 2, 3, 4, 5, 6],
    "p01_w11": [5, 6, 7, 8, 9],
    "p01_end_r595_600": [595, 596, 597, 598, 599, 600],
}


def _client(name: str) -> np.ndarray:
    frame = np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))
    return frame[OY:OY + CH, OX:OX + CW]


def _cells(name: str, box: tuple[int, int, int, int]) -> dict[int, np.ndarray]:
    """{순위: 셀 크롭} — 프레임의 완전 가시 행 전부."""
    client = _client(name)
    x0, dy0, x1, dy1 = box
    return {rank: np.ascontiguousarray(client[top + dy0:top + dy1, x0:x1])
            for top, rank in zip(detect_row_tops(client), RANKS[name])}


class IdentityMatcherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = DataStore(":memory:")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _matcher(self, namespace: str, threshold: float, suggest=None) -> IdentityMatcher:
        return IdentityMatcher(self.store, self.root, namespace, threshold=threshold,
                               suggest=suggest)

    def test_first_seen_registers_pending_with_suggested_label(self):
        m = self._matcher("user", ui.NAME_NCC_THRESHOLD, suggest=lambda crop: "제안?")
        iid, score, new = m.resolve(_cells("p01_contrib_top", ui.CELL_NAME)[1])
        self.assertTrue(new)
        pend = self.store.pending_identities()
        self.assertEqual([(r["identity_id"], r["namespace"], r["label"]) for r in pend],
                         [(iid, "user", "제안?")])
        tpl = self.store.templates_of(iid)
        self.assertEqual(tpl, ["assets/templates/user/user_000001.png"])
        self.assertTrue((self.root / tpl[0]).is_file())

    def test_suggest_failure_does_not_block_registration(self):
        def boom(crop):
            raise RuntimeError("OCR 없음")
        m = self._matcher("user", ui.NAME_NCC_THRESHOLD, suggest=boom)
        iid, _, new = m.resolve(_cells("p01_contrib_top", ui.CELL_NAME)[1])
        self.assertTrue(new)
        self.assertIsNone(self.store.pending_identities()[0]["label"])

    def test_same_user_other_frame_resolves_same_id(self):
        """행 y·배경이 다른 프레임(w11)의 같은 유저는 같은 ID. 저장소 재적재 후에도 동일."""
        m = self._matcher("user", ui.NAME_NCC_THRESHOLD)
        top = _cells("p01_contrib_top", ui.CELL_NAME)
        ids = {rank: m.resolve(cell)[0] for rank, cell in top.items()}
        self.assertEqual(len(set(ids.values())), 6)
        m2 = self._matcher("user", ui.NAME_NCC_THRESHOLD)   # 새 인스턴스 — 저장소에서 재적재
        for rank, cell in _cells("p01_w11", ui.CELL_NAME).items():
            iid, score, new = m2.resolve(cell)
            if rank in ids:                                    # 5·6위: 기존 ID
                self.assertEqual((iid, new), (ids[rank], False), rank)
                self.assertGreaterEqual(score, ui.NAME_NCC_THRESHOLD)
            else:                                              # 7·8·9위: 신규
                self.assertTrue(new, rank)
                self.assertNotIn(iid, ids.values())
        self.assertEqual(len(list(self.store.iter_identities("user"))), 6 + 3)

    def test_region_same_text_everywhere_is_one_id(self):
        m = self._matcher("region", ui.REGION_NCC_THRESHOLD)
        ids = {m.resolve(cell)[0] for name in RANKS
               for cell in _cells(name, ui.CELL_REGION).values()}
        self.assertEqual(len(ids), 1)

    def test_alliance_similar_text_is_not_merged(self):
        """잠룡(1·2·3·5위)을 등록한 뒤 삼룡(598위)은 새 ID여야 한다(획 1개 차이, NCC 0.908)."""
        m = self._matcher("alliance", ui.ALLIANCE_NCC_THRESHOLD)
        top = _cells("p01_contrib_top", ui.CELL_ALLIANCE)
        jam = {m.resolve(top[r])[0] for r in (1, 2, 3, 5)}
        sam, _, new = m.resolve(_cells("p01_end_r595_600", ui.CELL_ALLIANCE)[598])
        self.assertTrue(new)
        self.assertNotIn(sam, jam)

    def test_shared_suffix_names_are_distinct_but_same_name_rematches(self):
        """2026-09-30 실기 run_1(TASK-08): 3위 '자룡의사생활' vs 9위 '꽁구의사생활'(접미 4자 공유)
        NCC 0.811 — 임계 0.80에서 같은 ID로 오식별(작업 기록 TASK-08 발견). 같은 이름의 인접
        프레임 재매칭(0.972 이상)은 유지되어야 한다."""
        png = lambda n: np.asarray(Image.open(IMG / f"{n}.png").convert("RGB"))
        m = self._matcher("user", ui.NAME_NCC_THRESHOLD)
        id3, _, _ = m.resolve(png("p02_name_r03_f0"))
        id9, score9, new9 = m.resolve(png("p02_name_r09_f1"))
        self.assertTrue(new9, f"접미 공유 다른 이름이 같은 ID {id3}로 오식별 (점수 {score9:.3f})")
        id9b, score9b, new9b = m.resolve(png("p02_name_r09_f2"))
        self.assertEqual((id9b, new9b), (id9, False))
        self.assertGreaterEqual(score9b, 0.95)

if __name__ == "__main__":
    unittest.main()
