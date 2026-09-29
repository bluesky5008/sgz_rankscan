"""TASK-05 선행 테스트 — DataStore (FR-06·FR-07, NFR-03, AC-05 오프라인 부분 / DES-09 스키마).

TASK-07(2026-09-30)에서 latest_run_id·status_counts·pending 네임스페이스 필터를 추가했다.
"""

import tempfile
import unittest
from pathlib import Path

from rankscan.store.datastore import DataStore, RankRow


def _row(rank: int, **overrides) -> RankRow:
    fields = dict(
        user_id=None, region_id=None, alliance_id=None,
        user_score=None, region_score=None, alliance_score=None,
        rank_read=str(rank), crop_path=f"captures/run_1/rank_{rank:03d}.png",
        frame_path=None)
    fields.update(overrides)
    return RankRow(rank=rank, **fields)


class DbPathTest(unittest.TestCase):
    def test_creates_missing_parent_dirs(self):
        """기본 경로 output/rankscan.db처럼 부모 디렉터리가 없어도 열려야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "output" / "rankscan.db"
            with DataStore(str(path)) as store:
                self.assertEqual(store.ranks_of(store.create_run()), [])
            self.assertTrue(path.is_file())


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.store = DataStore(":memory:")

    def tearDown(self):
        self.store.close()


class RunTest(StoreTestCase):
    def test_create_and_finish_run(self):
        run = self.store.create_run(max_rank=600)
        row = self.store.get_run(run)
        self.assertEqual((row["status"], row["max_rank"], row["finished_at"]),
                         ("running", 600, None))
        self.store.finish_run(run, "aborted", processed=12, saved=11, failed=1,
                              note="rank_conflict at 7")
        row = self.store.get_run(run)
        self.assertEqual(row["status"], "aborted")
        self.assertEqual((row["processed"], row["saved"], row["failed"]), (12, 11, 1))
        self.assertEqual(row["note"], "rank_conflict at 7")
        self.assertIsNotNone(row["finished_at"])

    def test_latest_run_id(self):
        """export --run 생략 시 대상(DES-10): run이 없으면 None, 있으면 최신 run."""
        self.assertIsNone(self.store.latest_run_id())
        self.store.create_run()
        run2 = self.store.create_run()
        self.assertEqual(self.store.latest_run_id(), run2)


class RankRowTest(StoreTestCase):
    def test_upsert_same_rank_in_run_keeps_one_row_with_latest_values(self):
        """FR-06: 같은 run 안 같은 순위는 1건 — 재취득 프레임의 값이 이긴다."""
        run = self.store.create_run()
        self.store.upsert_row(run, _row(7, parse_status="partial"))
        self.store.upsert_row(run, _row(7, parse_status="ok"))
        self.assertEqual(self.store.ranks_of(run), [7])
        self.assertEqual([r["parse_status"] for r in self.store.export_rows(run)], ["ok"])

    def test_same_rank_in_different_runs_is_preserved(self):
        """FR-06: run이 다르면 모두 보존(주기 실행 이력)."""
        run1 = self.store.create_run()
        run2 = self.store.create_run()
        self.store.upsert_row(run1, _row(1))
        self.store.upsert_row(run2, _row(1))
        self.assertEqual(self.store.ranks_of(run1), [1])
        self.assertEqual(self.store.ranks_of(run2), [1])

    def test_ranks_of_is_sorted(self):
        run = self.store.create_run()
        for rank in (3, 1, 2):
            self.store.upsert_row(run, _row(rank))
        self.assertEqual(self.store.ranks_of(run), [1, 2, 3])

    def test_row_keeps_evidence_paths_and_read(self):
        """NFR-03: 행 레코드는 근거 크롭 경로를 가진다. 판독 문자열('?' 포함)도 보존."""
        run = self.store.create_run()
        self.store.upsert_row(run, _row(
            4, rank_read="?", crop_path="captures/run_1/rank_004.png",
            frame_path="captures/run_1/frames/step_0001.png"))
        row = list(self.store.export_rows(run))[0]
        self.assertEqual(row["crop_path"], "captures/run_1/rank_004.png")
        self.assertEqual(row["frame_path"], "captures/run_1/frames/step_0001.png")
        self.assertEqual(row["rank_read"], "?")
        self.assertTrue(row["captured_at"])

    def test_status_counts_per_run(self):
        """FR-08 실행 요약의 실패 사유 집계(parse_status별 건수)."""
        run = self.store.create_run()
        for rank, status in ((1, "ok"), (2, "partial"), (3, "partial"), (4, "failed")):
            self.store.upsert_row(run, _row(rank, parse_status=status))
        self.assertEqual(self.store.status_counts(run), {"ok": 1, "partial": 2, "failed": 1})
        self.assertEqual(self.store.status_counts(self.store.create_run()), {})


class IdentityTest(StoreTestCase):
    def test_identity_lifecycle(self):
        iid = self.store.create_identity("user", "演김부선?", "user/user_000001.png")
        pend = self.store.pending_identities()
        self.assertEqual([(r["identity_id"], r["namespace"], r["label"]) for r in pend],
                         [(iid, "user", "演김부선?")])
        self.store.confirm_label(iid, "演김부선")
        self.assertEqual(self.store.pending_identities(), [])
        rows = list(self.store.iter_identities("user"))
        self.assertEqual((rows[0]["label"], rows[0]["label_status"]),
                         ("演김부선", "confirmed"))
        self.assertEqual(list(self.store.iter_identities("region")), [])
        self.assertEqual(self.store.templates_of(iid), ["user/user_000001.png"])

    def test_confirmed_label_reflected_in_existing_rows(self):
        """FR-07·AC-05: 라벨 확정이 기존 레코드 조회에 반영된다."""
        run = self.store.create_run()
        uid = self.store.create_identity("user", "제안", "user/u1.png")
        self.store.upsert_row(run, _row(1, user_id=uid))
        before = list(self.store.export_rows(run))[0]
        self.assertEqual((before["user_label"], before["user_status"]), ("제안", "pending"))
        self.store.confirm_label(uid, "확정")
        after = list(self.store.export_rows(run))[0]
        self.assertEqual((after["user_label"], after["user_status"]), ("확정", "confirmed"))

    def test_pending_filtered_by_namespace(self):
        """label --namespace: 지정 네임스페이스의 pending만 순회한다."""
        self.store.create_identity("user", None, "user/u1.png")
        aid = self.store.create_identity("alliance", None, "alliance/a1.png")
        self.assertEqual([r["identity_id"] for r in self.store.pending_identities("alliance")],
                         [aid])
        self.assertEqual(len(self.store.pending_identities()), 2)


if __name__ == "__main__":
    unittest.main()
