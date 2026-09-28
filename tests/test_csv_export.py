"""TASK-05 선행 테스트 — CsvExport (FR-10, AC-05·AC-06 오프라인 부분 / DES-09 파일 산출물)."""

import csv
import tempfile
import unittest
from pathlib import Path

from rankscan.store.csv_export import HEADER, export_csv
from rankscan.store.datastore import DataStore, RankRow

EXPECTED_HEADER = ["run_id", "captured_at", "rank", "user", "region", "alliance",
                   "user_id", "region_id", "alliance_id", "parse_status", "rank_read",
                   "crop_path"]


def _row(rank: int, **overrides) -> RankRow:
    fields = dict(
        user_id=None, region_id=None, alliance_id=None,
        user_score=None, region_score=None, alliance_score=None,
        rank_read=str(rank), crop_path=f"captures/run_1/rank_{rank:03d}.png",
        frame_path=None)
    fields.update(overrides)
    return RankRow(rank=rank, **fields)


class CsvExportTest(unittest.TestCase):
    def setUp(self):
        self.store = DataStore(":memory:")
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "export"

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _export(self, run_id: int) -> list[dict]:
        """내보낸 CSV를 헤더 검증 후 열 이름 → 값 dict 목록으로 읽는다."""
        path = export_csv(self.store, self.out, run_id)
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(rows[0], EXPECTED_HEADER)
        return [dict(zip(rows[0], r)) for r in rows[1:]]

    def test_header_order_and_file_name(self):
        run = self.store.create_run()
        path = export_csv(self.store, self.out, run)
        with open(path, encoding="utf-8-sig", newline="") as fh:
            self.assertEqual(list(csv.reader(fh)), [EXPECTED_HEADER])
        self.assertEqual(HEADER, EXPECTED_HEADER)
        self.assertRegex(path.name, rf"^ranks_{run}_\d{{8}}\.csv$")
        self.assertEqual(path.parent, self.out)

    def test_utf8_bom(self):
        run = self.store.create_run()
        path = export_csv(self.store, self.out, run)
        self.assertEqual(path.read_bytes()[:3], b"\xef\xbb\xbf")

    def test_one_row_per_rank_with_labels(self):
        """AC-06: (run, 순위) 단위 1행, 세력명·지역·동맹 라벨과 크롭 경로 열.
        FR-10: 미확정 라벨은 `#<id>(<제안>)`, 미인식(NULL)은 빈 칸."""
        run = self.store.create_run()
        uid = self.store.create_identity("user", "演김부선?", "user/u1.png")
        rid = self.store.create_identity("region", "사예", "region/r1.png")
        aid = self.store.create_identity("alliance", "잠룡", "alliance/a1.png")
        self.store.confirm_label(rid, "사예")
        self.store.upsert_row(run, _row(
            1, user_id=uid, region_id=rid, alliance_id=aid,
            user_score=0.97, region_score=0.99, alliance_score=0.95,
            frame_path="captures/run_1/frames/step_0000.png"))
        self.store.upsert_row(run, _row(
            2, region_id=rid, rank_read="?", parse_status="partial"))

        rows = self._export(run)
        self.assertEqual(len(rows), 2)
        r1, r2 = rows
        self.assertEqual(r1["run_id"], str(run))
        self.assertTrue(r1["captured_at"])
        self.assertEqual(r1["rank"], "1")
        self.assertEqual(r1["user"], f"#{uid}(演김부선?)")
        self.assertEqual(r1["region"], "사예")
        self.assertEqual(r1["alliance"], f"#{aid}(잠룡)")
        self.assertEqual((r1["user_id"], r1["region_id"], r1["alliance_id"]),
                         (str(uid), str(rid), str(aid)))
        self.assertEqual(r1["parse_status"], "ok")
        self.assertEqual(r1["rank_read"], "1")
        self.assertEqual(r1["crop_path"], "captures/run_1/rank_001.png")
        self.assertEqual(r2["rank"], "2")
        self.assertEqual((r2["user"], r2["user_id"], r2["alliance"], r2["alliance_id"]),
                         ("", "", "", ""))
        self.assertEqual(r2["region"], "사예")
        self.assertEqual(r2["parse_status"], "partial")
        self.assertEqual(r2["rank_read"], "?")

    def test_confirmed_label_replaces_marker(self):
        """AC-05: 라벨 확정 후 CSV에 그 이름이 반영된다."""
        run = self.store.create_run()
        uid = self.store.create_identity("user", "제안", "user/u1.png")
        self.store.upsert_row(run, _row(1, user_id=uid))
        self.assertEqual(self._export(run)[0]["user"], f"#{uid}(제안)")
        self.store.confirm_label(uid, "확정")
        self.assertEqual(self._export(run)[0]["user"], "확정")

    def test_only_requested_run(self):
        run1 = self.store.create_run()
        run2 = self.store.create_run()
        self.store.upsert_row(run1, _row(1))
        self.store.upsert_row(run2, _row(1))
        self.store.upsert_row(run2, _row(2))
        rows = self._export(run1)
        self.assertEqual([(r["run_id"], r["rank"]) for r in rows], [(str(run1), "1")])


if __name__ == "__main__":
    unittest.main()
