"""행 → RankRow (설계 DES-05, ADR-001·002).

클라이언트 프레임과 행 상단 y, 기하로 배정된 순위(ADR-002)를 받아 셀 상자(ui_ranking)로
세력명·지역·동맹을 잘라 IdentityMatcher(DES-06)로 ID화하고 순위 셀을 RankDigitReader(DES-08)로
읽는다. 셀별 실패를 모아 ok|partial|failed를 판정한다(NFR-01). 행 크롭·프레임 저장과
crop_path·frame_path 기입은 walk(DES-04 4)의 책임이라 여기서는 None으로 둔다.

빈 셀(밝은 픽셀이 거의 없음 — 동맹 없는 유저 등)은 실패가 아니라 미인식 NULL이며 식별자를
등록하지 않는다: 균일한 크롭은 NCC가 0에 가까워 행마다 새 ID가 발행되기 때문이다.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from ..nav import ui_ranking as ui
from ..store.datastore import DataStore, RankRow
from .digits import RankDigitReader
from .identity import IdentityMatcher, Suggest

log = logging.getLogger(__name__)

DEFAULT_ROOT = Path(__file__).resolve().parents[3]
_TEXT_MIN_VAL = 130       # 텍스트 획의 명도 하한(digits와 동일 근거; 채도는 보지 않음 — 금색 이름)
_BLANK_MAX_BRIGHT = 10    # 밝은 픽셀이 이 미만이면 빈 셀(2026-09-28 텍스트 셀 44개 최소 143)


def _cell(frame: np.ndarray, top: int, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, dy0, x1, dy1 = box
    return np.ascontiguousarray(frame[top + dy0:top + dy1, x0:x1])


def is_blank(cell: np.ndarray) -> bool:
    val = cv2.cvtColor(cell, cv2.COLOR_RGB2HSV)[..., 2]
    return int((val >= _TEXT_MIN_VAL).sum()) < _BLANK_MAX_BRIGHT


class RowParser:
    def __init__(self, store: DataStore, root: Path | str = DEFAULT_ROOT, *,
                 suggest: Suggest | None = None):
        """`suggest`가 None이면 OcrReader.suggest_label을 쓴다(테스트는 대역을 넣는다)."""
        if suggest is None:
            from .ocr import OcrReader
            suggest = OcrReader().suggest_label
        self.users = IdentityMatcher(store, root, "user", ui.NAME_NCC_THRESHOLD, suggest)
        self.regions = IdentityMatcher(store, root, "region", ui.REGION_NCC_THRESHOLD, suggest)
        self.alliances = IdentityMatcher(store, root, "alliance", ui.ALLIANCE_NCC_THRESHOLD,
                                         suggest)
        self.digits = RankDigitReader()

    def read_rank(self, frame: np.ndarray, top: int) -> str:
        """행 상단 top의 순위 셀 판독(DES-08). 예외는 '?'(판독 실패)로 격리한다.

        walk의 시작 조건 판정(DES-04 1)이 셀 하나만 읽을 때도 이 메서드를 쓴다.
        """
        try:
            return self.digits.read_rank(_cell(frame, top, ui.CELL_RANK))
        except Exception:
            log.exception("행(top %d) 순위 셀 판독 예외", top)
            return "?"

    def parse(self, frame: np.ndarray, top: int, rank: int) -> RankRow:
        failed: list[str] = []

        def ident(matcher: IdentityMatcher, box, field: str) -> tuple[int | None, float | None]:
            cell = _cell(frame, top, box)
            if is_blank(cell):
                return None, None
            try:
                iid, score, _ = matcher.resolve(cell)
                return iid, score
            except Exception:
                log.exception("%d위 %s 셀 판독 예외", rank, field)
                failed.append(field)
                return None, None

        user_id, user_score = ident(self.users, ui.CELL_NAME, "user")
        region_id, region_score = ident(self.regions, ui.CELL_REGION, "region")
        alliance_id, alliance_score = ident(self.alliances, ui.CELL_ALLIANCE, "alliance")
        rank_read = self.read_rank(frame, top)
        if not rank_read or "?" in rank_read:
            failed.append("rank")

        status = "ok" if not failed else ("failed" if len(failed) == 4 else "partial")
        if failed:
            log.warning("%d위 파싱 %s: 실패 셀 %s", rank, status, ", ".join(failed))
        return RankRow(rank, user_id, region_id, alliance_id, user_score, region_score,
                       alliance_score, rank_read, None, None, status)
