"""목록 행 기하 — 행 검출·이동량 측정·순위 이어붙임 (설계 DES-04 2·3·6, ADR-002 1·2).

이 모듈의 함수는 순수 함수다. 입력은 클라이언트 좌표계 프레임(2544×657 RGB — 캡처
프레임에서 navigator.ScreenJudge.crop_client(frame, (0, 0, *client_size))로 자른 것),
출력 y도 클라이언트 좌표다. 순회 루프(ListScroller.walk)는 TASK-07에서 이 위에 얹는다.

행 상단 검출 규칙(2026-09-28 픽스처 8장 실측, tests/test_list_geometry.py):
각 행은 어두운 카드이고 상·하단에 1px 밝은 테두리선이 있다. 카드 사이 6~7px 간격에는
밝기가 위치마다 다른 패널 배경이 보이므로 절대 밝기 임계는 쓸 수 없다. ROW_LINE_COL
빈 열의 밝기 프로파일에서 (1) 국소 최대이면서 (2) 그 아래 행 내부(+2~+8px)보다
ROW_LINE_MIN_CONTRAST 이상 밝은 픽셀을 테두리선 후보로 잡고, (3) ROW_LINE_PAIR_MAX 안에
다음 후보가 따라오면 하단선(쌍의 첫째)으로 버리며, (4) 행 전체가 LIST_REGION 안에 드는
것만 완전 가시 행으로 채택한다. 상단선이 부화소 렌더링으로 2px에 걸치면 더 밝은 쪽이
잡혀 프레임 간 ±1px 차이가 날 수 있다(순위 배정의 round()가 흡수).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import cv2
import numpy as np

from . import ui_ranking as ui

log = logging.getLogger(__name__)

_LINE_SKIP, _LINE_WINDOW = 2, 7   # 대비 비교 창: 후보 y+2 ~ y+8 (y+1은 2px 걸침 허용)


def detect_row_tops(client: np.ndarray) -> list[int]:
    """완전 가시 행의 상단 y 목록(위→아래). 행이 없으면 []."""
    x0, x1 = ui.ROW_LINE_COL
    _, y0, _, y1 = ui.LIST_REGION
    p = client[y0:y1, x0:x1].astype(np.float32).mean(axis=(1, 2))
    lines = [i for i in range(1, len(p) - _LINE_SKIP - _LINE_WINDOW + 1)
             if p[i] >= p[i - 1] and p[i] > p[i + 1]
             and p[i] - p[i + _LINE_SKIP:i + _LINE_SKIP + _LINE_WINDOW].max()
             >= ui.ROW_LINE_MIN_CONTRAST]
    tops = [y0 + i for k, i in enumerate(lines)
            if k + 1 == len(lines) or lines[k + 1] - i > ui.ROW_LINE_PAIR_MAX]
    return [t for t in tops if t + ui.ROW_HEIGHT <= y1]


def anchor_band(client: np.ndarray, top: int) -> np.ndarray:
    """anchor 행의 이름 열 띠(CELL_NAME) — 다음 프레임에서 그 행을 재발견하는 템플릿."""
    x0, dy0, x1, dy1 = ui.CELL_NAME
    return client[top + dy0:top + dy1, x0:x1].copy()


def measure_shift(band: np.ndarray, band_top: int, client: np.ndarray) -> int | None:
    """직전 프레임 anchor 띠(행 상단 band_top)를 새 프레임에서 재발견해 위로 이동한 px.

    목록 영역의 이름 열에서 NCC 최고점이 ANCHOR_NCC_THRESHOLD 미만이면 None(겹침 상실).
    0은 이동 없음(목록 끝), 음수는 아래로 이동(되감기). 범위 판정은 호출자가 한다.
    """
    x0, dy0, x1, _ = ui.CELL_NAME
    _, y0, _, y1 = ui.LIST_REGION
    res = cv2.matchTemplate(client[y0:y1, x0:x1], band, cv2.TM_CCOEFF_NORMED)
    _, score, _, (_, dy) = cv2.minMaxLoc(res)
    new_top = y0 + dy - dy0
    log.debug("anchor 재발견: top %d → %d (NCC %.3f)", band_top, new_top, score)
    if score < ui.ANCHOR_NCC_THRESHOLD:
        return None
    return band_top - new_top


def assign_ranks(anchor: tuple[int, int], tops: Iterable[int]) -> list[tuple[int, int]]:
    """anchor=(rank, top) 기준으로 각 행 상단에 순위를 배정한 [(rank, top)] (ADR-002 1)."""
    rank, top = anchor
    return [(rank + round((t - top) / ui.ROW_PITCH), t) for t in tops]
