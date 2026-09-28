# 출처: sgz_statiz C:\src\git\sgz_statiz\src\deckscan\store\csv_export.py (2026-09-28 이식,
#       원류 map_search mapscan/store/csv_export.py). 변경점: 파일 3종 → run당 1종
#       ranks_<run_id>_<날짜>.csv, 열은 설계 DES-09 파일 산출물 순서, 미확정 라벨은
#       `#<id>(<제안>)` 표기(FR-10).
"""CSV 내보내기 (설계 DES-09 파일 산출물, FR-10). UTF-8(BOM)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .datastore import DataStore

HEADER = ["run_id", "captured_at", "rank", "user", "region", "alliance",
          "user_id", "region_id", "alliance_id", "parse_status", "rank_read",
          "crop_path"]


def display_label(identity_id: int | None, label: str | None, status: str | None) -> str:
    """확정 라벨은 그대로, 미확정은 `#<id>(<제안>)`, 미인식(NULL)은 빈 칸."""
    if identity_id is None:
        return ""
    if status == "confirmed":
        return label or ""
    return f"#{identity_id}({label or ''})"


def export_csv(store: DataStore, out_dir: str | Path, run_id: int) -> Path:
    """run 1개를 (run, 순위) 단위 1행 CSV로 내보내고 경로를 반환한다."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"ranks_{run_id}_{datetime.now():%Y%m%d}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for r in store.export_rows(run_id):
            w.writerow([
                r["run_id"], r["captured_at"], r["rank"],
                display_label(r["user_id"], r["user_label"], r["user_status"]),
                display_label(r["region_id"], r["region_label"], r["region_status"]),
                display_label(r["alliance_id"], r["alliance_label"], r["alliance_status"]),
                r["user_id"], r["region_id"], r["alliance_id"],
                r["parse_status"], r["rank_read"], r["crop_path"]])
    return path
