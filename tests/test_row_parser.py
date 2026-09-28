"""TASK-06 선행 테스트 — RowParser (AC-02 오프라인, FR-05, NFR-01·AC-04 단위 부분 / DES-05).

img/ranking_1.png(공헌 랭킹 1~6위 참고 이미지)를 클라이언트 프레임으로 잘라 행별로 파싱한다.
AC-02 기준값: 지역 '사예'×6, 동맹 잠룡·잠룡·잠룡·맹수·잠룡·변수, 세력명 6개 상이.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from rankscan.nav import ui_ranking as ui
from rankscan.nav.list_scroller import detect_row_tops
from rankscan.store.datastore import DataStore
from rankscan.vision.row_parser import RowParser

IMG = Path(__file__).resolve().parents[1] / "img"
OX, OY, CW, CH = 1, 31, 2544, 657
AC02_USERS = ["演김부선", "演라미란", "자룡의사생활", "우럭초밥", "演도시혜수", "勇수정"]
AC02_ALLIANCES = ["잠룡", "잠룡", "잠룡", "맹수", "잠룡", "변수"]


def _client(name: str = "ranking_1") -> np.ndarray:
    frame = np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))
    return frame[OY:OY + CH, OX:OX + CW].copy()


def _blackout(client: np.ndarray, top: int, box: tuple[int, int, int, int]) -> None:
    x0, dy0, x1, dy1 = box
    client[top + dy0:top + dy1, x0:x1] = 0


class RowParserTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = DataStore(":memory:")
        self.parser = RowParser(self.store, self.root, suggest=lambda crop: None)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _parse_all(self, parser: RowParser, client: np.ndarray):
        tops = detect_row_tops(client)
        self.assertEqual(len(tops), 6)
        return [parser.parse(client, top, rank) for rank, top in enumerate(tops, start=1)]

    def test_ac02_ranking_1_rows(self):
        rows = self._parse_all(self.parser, _client())
        self.assertEqual([r.parse_status for r in rows], ["ok"] * 6)
        self.assertEqual([r.rank for r in rows], [1, 2, 3, 4, 5, 6])
        self.assertEqual([r.rank_read for r in rows], ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(len({r.region_id for r in rows}), 1)
        a = [r.alliance_id for r in rows]
        # 잠룡(1·2·3·5위)은 부화소 렌더링 차이로 ID가 갈릴 수 있다(임계 0.92, 2026-09-28 실측
        # 같은 프레임 0.875) — 서로 다른 동맹과는 섞이지 않아야 하고 이름은 라벨 확정으로 합친다
        jam = {a[0], a[1], a[2], a[4]}
        self.assertTrue(jam.isdisjoint({a[3], a[5]}))
        self.assertNotEqual(a[3], a[5])                                # 맹수 ≠ 변수
        self.assertEqual(len({r.user_id for r in rows}), 6)
        for r in rows:
            self.assertIsNotNone(r.user_score)
            self.assertIsNone(r.crop_path)                           # 저장은 walk(DES-04 4)
        n_ids = 6 + 1 + len(set(a))
        self.assertEqual(len(self.store.pending_identities()), n_ids)

        # FR-07: 라벨 확정 → 저장 레코드 조회에 이름 반영 (AC-02 "이름"은 확정 후 조회 기준)
        for r, user, alliance in zip(rows, AC02_USERS, AC02_ALLIANCES):
            self.store.confirm_label(r.user_id, user)
            self.store.confirm_label(r.alliance_id, alliance)
        self.store.confirm_label(rows[0].region_id, "사예")
        run = self.store.create_run()
        for r in rows:
            self.store.upsert_row(run, r)
        got = list(self.store.export_rows(run))
        self.assertEqual([g["user_label"] for g in got], AC02_USERS)
        self.assertEqual([g["alliance_label"] for g in got], AC02_ALLIANCES)
        self.assertEqual({g["region_label"] for g in got}, {"사예"})
        self.assertEqual(self.store.pending_identities(), [])

        # 멱등: 새 파서(저장소에서 템플릿 재적재)로 재파싱해도 신규 등록 0건, 세력명·지역 ID
        # 동일, 동맹은 확정 라벨 동일(같은 텍스트의 중복 ID 사이에서는 최고점이 바뀔 수 있다 —
        # 2026-09-28 실측: 2위 잠룡이 1차 ID 3 → 재파싱 ID 6. 라벨로 합쳐진다)
        again = self._parse_all(RowParser(self.store, self.root, suggest=lambda c: None), _client())
        self.assertEqual([(r.user_id, r.region_id) for r in again],
                         [(r.user_id, r.region_id) for r in rows])
        labels = {r["identity_id"]: r["label"] for r in self.store.iter_identities("alliance")}
        self.assertEqual([labels[r.alliance_id] for r in again], AC02_ALLIANCES)
        self.assertEqual(self.store.pending_identities(), [])
        self.assertEqual(sum(1 for ns in ("user", "region", "alliance")
                             for _ in self.store.iter_identities(ns)), n_ids)

    def test_blank_cell_is_null_without_registration(self):
        """빈 셀(동맹 없음 등)은 미인식 NULL이며 식별자를 등록하지 않는다(레지스트리 팽창 방지)."""
        client = _client()
        top = detect_row_tops(client)[0]
        _blackout(client, top, ui.CELL_ALLIANCE)
        row = self.parser.parse(client, top, 1)
        self.assertIsNone(row.alliance_id)
        self.assertIsNotNone(row.user_id)
        self.assertEqual(row.parse_status, "ok")
        self.assertEqual(list(self.store.iter_identities("alliance")), [])

    def test_rank_read_failure_is_partial(self):
        client = _client()
        top = detect_row_tops(client)[0]
        _blackout(client, top, ui.CELL_RANK)
        row = self.parser.parse(client, top, 1)
        self.assertEqual((row.rank, row.rank_read, row.parse_status), (1, "", "partial"))
        self.assertIsNotNone(row.user_id)

    def test_cell_exception_is_isolated_as_partial(self):
        """NFR-01·AC-04: 셀 하나의 예외는 행을 partial로 남기고 나머지 셀은 처리된다."""
        def boom(crop):
            raise RuntimeError("매칭 예외")
        self.parser.alliances.resolve = boom
        client = _client()
        row = self.parser.parse(client, detect_row_tops(client)[0], 1)
        self.assertEqual(row.parse_status, "partial")
        self.assertIsNone(row.alliance_id)
        self.assertIsNotNone(row.user_id)
        self.assertIsNotNone(row.region_id)
        self.assertEqual(row.rank_read, "1")


if __name__ == "__main__":
    unittest.main()
