# 출처: sgz_statiz C:\src\git\sgz_statiz\src\deckscan\store\datastore.py (2026-09-28 이식,
#       원류 map_search mapscan/store/datastore.py). 변경점: 스키마를 설계 DES-09로 교체
#       (runs에 max_rank·note 추가, battles·deck_slots → rank_rows), battle_key·대체 키·
#       add_template·덱 통계 조회 제거, RankRow·upsert_row·ranks_of·export_rows 추가.
"""SQLite 수집 원장 (설계 DES-09).

`rank_rows`의 기본키 `(run_id, rank)`가 FR-06의 "같은 run 안 같은 순위 1건"을 구조적으로
보장하고, run이 다르면 모두 보존된다(주기 실행 이력). 같은 run에서 같은 순위를 재처리하면
`INSERT OR REPLACE`로 덮어쓴다(재취득 프레임 처리).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at  TEXT NOT NULL,
  finished_at TEXT,
  status      TEXT NOT NULL DEFAULT 'running',   -- running|done|aborted
  max_rank    INTEGER,
  processed   INTEGER,
  saved       INTEGER,
  failed      INTEGER,
  note        TEXT                               -- 중단 사유·연속성 이상 요약
);

CREATE TABLE IF NOT EXISTS identities (
  identity_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  namespace    TEXT NOT NULL,                    -- user|region|alliance
  label        TEXT,
  label_status TEXT NOT NULL DEFAULT 'pending',  -- pending|confirmed
  first_seen   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_templates (
  identity_id   INTEGER NOT NULL REFERENCES identities(identity_id),
  template_path TEXT NOT NULL,
  PRIMARY KEY (identity_id, template_path)
);

CREATE TABLE IF NOT EXISTS rank_rows (
  run_id         INTEGER NOT NULL REFERENCES runs(run_id),
  rank           INTEGER NOT NULL,
  user_id        INTEGER,                        -- identities, 미인식 NULL
  region_id      INTEGER,
  alliance_id    INTEGER,
  user_score     REAL,
  region_score   REAL,
  alliance_score REAL,
  rank_read      TEXT,                           -- DES-08 판독 문자열('?' 포함 가능)
  crop_path      TEXT,
  frame_path     TEXT,
  parse_status   TEXT NOT NULL DEFAULT 'ok',     -- ok|partial|failed
  captured_at    TEXT NOT NULL,
  PRIMARY KEY (run_id, rank)
);
"""

SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class RankRow:
    """행 1건의 추출 결과 (설계 내부 계약). DES-05 RowParser가 만들고 DataStore가 저장한다."""
    rank: int
    user_id: int | None
    region_id: int | None
    alliance_id: int | None
    user_score: float | None
    region_score: float | None
    alliance_score: float | None
    rank_read: str | None
    crop_path: str | None
    frame_path: str | None
    parse_status: str = "ok"        # ok|partial|failed


class DataStore:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,))
        self._conn.commit()

    # -- runs ---------------------------------------------------------------

    def create_run(self, max_rank: int | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO runs (started_at, max_rank) VALUES (?, ?)", (_now(), max_rank))
        self._conn.commit()
        return cur.lastrowid

    def get_run(self, run_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()

    def finish_run(self, run_id: int, status: str = "done", *,
                   processed: int = 0, saved: int = 0, failed: int = 0,
                   note: str | None = None) -> None:
        self._conn.execute(
            "UPDATE runs SET status=?, finished_at=?, processed=?, saved=?, failed=?, note=?"
            " WHERE run_id=?",
            (status, _now(), processed, saved, failed, note, run_id))
        self._conn.commit()

    # -- identities ---------------------------------------------------------

    def create_identity(self, namespace: str, label: str | None,
                        template_path: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO identities (namespace, label, first_seen) VALUES (?, ?, ?)",
            (namespace, label, _now()))
        iid = cur.lastrowid
        self._conn.execute(
            "INSERT INTO identity_templates (identity_id, template_path) VALUES (?, ?)",
            (iid, template_path))
        self._conn.commit()
        return iid

    def confirm_label(self, identity_id: int, label: str) -> None:
        self._conn.execute(
            "UPDATE identities SET label=?, label_status='confirmed'"
            " WHERE identity_id=?", (label, identity_id))
        self._conn.commit()

    def pending_identities(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM identities WHERE label_status='pending'"
            " ORDER BY identity_id").fetchall()

    def iter_identities(self, namespace: str):
        yield from self._conn.execute(
            "SELECT * FROM identities WHERE namespace=? ORDER BY identity_id",
            (namespace,))

    def templates_of(self, identity_id: int) -> list[str]:
        return [r[0] for r in self._conn.execute(
            "SELECT template_path FROM identity_templates WHERE identity_id=?"
            " ORDER BY template_path", (identity_id,))]

    # -- rank rows ----------------------------------------------------------

    def upsert_row(self, run_id: int, row: RankRow) -> None:
        """행 1건을 멱등 저장한다 — 같은 (run, rank)는 나중 값으로 덮어쓴다."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO rank_rows (run_id, rank, user_id, region_id,"
                " alliance_id, user_score, region_score, alliance_score, rank_read,"
                " crop_path, frame_path, parse_status, captured_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, row.rank, row.user_id, row.region_id, row.alliance_id,
                 row.user_score, row.region_score, row.alliance_score, row.rank_read,
                 row.crop_path, row.frame_path, row.parse_status, _now()))

    def ranks_of(self, run_id: int) -> list[int]:
        """run에 저장된 순위 집합(오름차순) — 결측·중복 검사용(AC-03)."""
        return [r[0] for r in self._conn.execute(
            "SELECT rank FROM rank_rows WHERE run_id=? ORDER BY rank", (run_id,))]

    def export_rows(self, run_id: int):
        """내보내기용 행 (순위순, 세력명·지역·동맹의 라벨과 확정 상태 조인)."""
        yield from self._conn.execute("""
            SELECT r.*,
                   u.label AS user_label,     u.label_status AS user_status,
                   g.label AS region_label,   g.label_status AS region_status,
                   a.label AS alliance_label, a.label_status AS alliance_status
            FROM rank_rows r
            LEFT JOIN identities u ON u.identity_id = r.user_id
            LEFT JOIN identities g ON g.identity_id = r.region_id
            LEFT JOIN identities a ON a.identity_id = r.alliance_id
            WHERE r.run_id = ?
            ORDER BY r.rank""", (run_id,))

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DataStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
