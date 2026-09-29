"""목록 순회 — 행 기하 순수 함수와 순회 루프 ListScroller.walk (설계 DES-04, ADR-002).

순수 함수(detect_row_tops·anchor_band·measure_shift·assign_ranks)의 입력은 클라이언트 좌표계
프레임(2544×657 RGB — 캡처 프레임에서 navigator.ScreenJudge.crop_client(frame, (0, 0, *client_size))로
자른 것), 출력 y도 클라이언트 좌표다. ListScroller.walk는 이 위에 시작 조건·처리·종료·복구를 얹는다.

행 상단 검출 규칙(2026-09-28 픽스처 8장 실측, tests/test_list_geometry.py):
각 행은 어두운 카드이고 상·하단에 1px 밝은 테두리선이 있다. 카드 사이 6~7px 간격에는
밝기가 위치마다 다른 패널 배경이 보이므로 절대 밝기 임계는 쓸 수 없다. ROW_LINE_COL
빈 열의 밝기 프로파일에서 (1) 국소 최대이면서 (2) 그 아래 행 내부(+2~+8px)보다
ROW_LINE_MIN_CONTRAST 이상 밝은 픽셀을 테두리선 후보로 잡고, (3) ROW_LINE_PAIR_MAX 안에
다음 후보가 따라오면 하단선(쌍의 첫째)으로 버리며, (4) 행 전체가 LIST_REGION 안에 드는
것만 완전 가시 행으로 채택한다. 상단선이 부화소 렌더링으로 2px에 걸치면 더 밝은 쪽이
잡혀 프레임 간 ±1px 차이가 날 수 있다(순위 배정의 round()가 흡수).

순회 루프(DES-04 상세 1~7, tests/test_list_scroller.py):
- 시작: 첫 완전 가시 행의 순위 셀이 '1'이어야 anchor=(1, top). 아니면 위로 되감기
  (+SCROLL_NOTCHES×10) 후 재판정, 2회 실패면 중단.
- 패스: anchor로 각 행에 순위를 배정하고 미처리·max_rank 이하 행을 파싱해 행 크롭
  (rank_NNN.png)과 단계 프레임(frames/step_NNNN.png, LIST_REGION) 경로를 기입한 뒤 upsert.
  순위 판독값(실패 ''/'?' 제외)이 배정 순위와 다르면 순위 충돌: 프레임을 재취득해 1회
  재시도하고 재발하면 중단(ADR-002 3). 셀 실패 행은 partial|failed로 저장하고 계속(NFR-01).
- 종료: 저장한 최대 순위 ≥ max_rank(stop_reason=max_rank), 또는 스크롤 후 anchor 이동량
  0(목록 끝, end — ADR-002 6. 설계의 same_image 판정을 포함하는 조건이다).
- 스크롤: anchor(마지막 완전 가시 행)의 이름 띠를 보관 → 휠(−SCROLL_NOTCHES) → 안정
  프레임에서 재발견. 겹침 상실(NCC 미달, 이동량 ∉ (0, SHIFT_MAX))이면 되감기(+SCROLL_NOTCHES/2)
  후 재측정 2회, 실패면 중단. 되감기 뒤에는 이동량 0·음수도 유효한 기하로 받아들인다.
- 프레임마다 랭킹 화면·공헌 탭 마커를 확인하고 이탈 시 귀환 1회로 복구, 실패면 중단.
- 중단(WalkAborted 또는 판정기·캡처 예외)은 저장분을 유지하고 전체 프레임을 error_NNNN.png로
  남긴다. 종료 코드 2는 controller.run_scan이 준다.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import ui_ranking as ui
from .navigator import ScreenJudge, ui_template

log = logging.getLogger(__name__)

_LINE_SKIP, _LINE_WINDOW = 2, 7   # 대비 비교 창: 후보 y+2 ~ y+8 (y+1은 2px 걸침 허용)
_START_RETRIES = 2                # 시작 조건(1위) 되감기 재판정 횟수 (DES-04 1)
_RECOVER_RETRIES = 2              # 겹침 상실 되감기 재측정 횟수 (DES-04 6)


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


# -- 순회 루프 -------------------------------------------------------------------

class WalkAborted(RuntimeError):
    """순회 중단 — 복구 실패(시작 조건·겹침 상실·순위 충돌·화면 이탈·행 미검출). 저장분은 유지된다."""


@dataclass
class WalkSummary:
    processed: int = 0                # 파싱·저장한 행 수(실패 행 포함)
    saved: int = 0                    # parse_status ok|partial
    failed: int = 0                   # parse_status failed
    partial: int = 0
    conflicts: int = 0                # 순위 충돌 발생 횟수(재취득으로 복구한 것 포함)
    last_rank: int = 0                # 저장한 최대 순위
    stop_reason: str | None = None    # max_rank|end|aborted


def _save(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(image)).save(path)


def _list_region(client: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = ui.LIST_REGION
    return client[y0:y1, x0:x1]


class ListScroller:
    """공헌 랭킹 목록 순회 — 캡처·입력·판정기는 생성자 주입(테스트는 가짜 게임으로 대체)."""

    def __init__(self, judge: ScreenJudge, input_, parser, store, run_id: int, *,
                 max_rank: int = 600,
                 captures_dir: Path | str = Path("output") / "captures"):
        self.judge = judge
        self.input = input_
        self.parser = parser
        self.store = store
        self.run_id = run_id
        self.max_rank = max_rank
        self.run_dir = Path(captures_dir) / f"run_{run_id}"
        self.summary = WalkSummary()
        self.done: set[int] = set()
        self.step = -1
        self._window: np.ndarray | None = None    # 마지막 창 프레임(중단 증거용)
        self._frame_path: str | None = None       # 현재 단계 프레임 경로(행 레코드에 기입)

    # -- 프레임 취득 ---------------------------------------------------------

    def _at_ranking(self, window: np.ndarray) -> bool:
        return all(self.judge.marker_score(window, rect, ui_template(name))
                   >= ui.MARKER_NCC_THRESHOLD
                   for name, rect in (ui.MARKER_RANKING, ui.MARKER_CONTRIB_TAB))

    def _frame(self) -> np.ndarray:
        """안정 프레임 취득 → 화면 검증(이탈 시 귀환 1회) → 단계 프레임 저장 → 클라이언트 프레임."""
        window = self.judge.wait_stable()
        if not self._at_ranking(window):
            log.warning("랭킹 화면 이탈 — 귀환 1회 후 재판정")
            self.input.click(*ui.CLICK_RETURN)
            window = self.judge.wait_stable()
            if not self._at_ranking(window):
                self._window = window
                raise WalkAborted("랭킹 화면 이탈 — 귀환 복구 실패")
        self._window = window
        client = self.judge.crop_client(window, (0, 0, *self.judge.client_size))
        self.step += 1
        path = self.run_dir / "frames" / f"step_{self.step:04d}.png"
        _save(path, _list_region(client))
        self._frame_path = str(path)
        return client

    # -- 순회 ----------------------------------------------------------------

    def walk(self) -> WalkSummary:
        try:
            return self._walk()
        except Exception:
            self.summary.stop_reason = "aborted"
            if self._window is not None:
                _save(self.run_dir / f"error_{max(self.step, 0):04d}.png", self._window)
            raise

    def _walk(self) -> WalkSummary:
        anchor, client = self._start(self._frame())
        while True:
            client, rows = self._pass(client, anchor)
            if self.summary.last_rank >= self.max_rank:
                return self._stop("max_rank")
            anchor = rows[-1]                                  # DES-04 7: 겹침 최대화
            band = anchor_band(client, anchor[1])
            self.input.wheel(*ui.SCROLL_POINT, -ui.SCROLL_NOTCHES)
            client = self._frame()
            shift = measure_shift(band, anchor[1], client)
            if shift == 0:
                return self._stop("end")
            if shift is None or not 0 < shift < ui.SHIFT_MAX:
                shift, client = self._recover(band, anchor[1], client, shift)
            anchor = (anchor[0], anchor[1] - shift)

    def _stop(self, reason: str) -> WalkSummary:
        self.summary.stop_reason = reason
        log.info("순회 종료(%s): 마지막 순위 %d, 처리 %d건", reason,
                 self.summary.last_rank, self.summary.processed)
        return self.summary

    def _start(self, client: np.ndarray) -> tuple[tuple[int, int], np.ndarray]:
        """DES-04 1: 첫 완전 가시 행이 1위여야 anchor=(1, top). 아니면 되감기 후 재판정.

        반환: (anchor, 판정에 쓴 현재 프레임) — 되감기했으면 프레임이 바뀌어 있다.
        """
        read = ""
        for attempt in range(_START_RETRIES + 1):
            tops = detect_row_tops(client)
            read = self.parser.read_rank(client, tops[0]) if tops else ""
            if read == "1":
                return (1, tops[0]), client
            if attempt == _START_RETRIES:
                break
            log.warning("시작 조건 미충족(첫 행 판독 %r) — 위로 되감기 후 재판정", read)
            self.input.wheel(*ui.SCROLL_POINT, ui.SCROLL_NOTCHES * 10)
            client = self._frame()
        raise WalkAborted(f"시작 조건 실패: 첫 완전 가시 행이 1위가 아님(판독 {read!r})")

    def _pass(self, client: np.ndarray,
              anchor: tuple[int, int]) -> tuple[np.ndarray, list[tuple[int, int]]]:
        """DES-04 2~4: 행 검출 → 순위 배정 → 미처리 행 처리. 순위 충돌이면 프레임 재취득 1회."""
        conflict = None
        for attempt in range(2):
            tops = detect_row_tops(client)
            if not tops:
                raise WalkAborted("완전 가시 행 없음")
            rows = assign_ranks(anchor, tops)
            conflict = self._process(client, rows)
            if conflict is None:
                return client, rows
            self.summary.conflicts += 1
            if attempt == 0:
                log.warning("순위 충돌(%s) — 프레임 재취득 후 재시도", conflict)
                client = self._frame()
        raise WalkAborted(f"순위 충돌 재발: {conflict}")

    def _process(self, client: np.ndarray, rows: list[tuple[int, int]]) -> str | None:
        """미처리 행 파싱·크롭 저장·upsert. 순위 충돌이면 설명을 반환하고 즉시 멈춘다."""
        x0, _, x1, _ = ui.LIST_REGION
        for rank, top in rows:
            if rank in self.done or rank > self.max_rank:
                continue
            if rank < 1:
                return f"{rank}위 배정(anchor 오류)"
            row = self.parser.parse(client, top, rank)
            if row.rank_read and "?" not in row.rank_read and row.rank_read != str(rank):
                return f"{rank}위 판독 {row.rank_read!r}"
            crop_path = self.run_dir / f"rank_{rank:03d}.png"
            _save(crop_path, client[top:top + ui.ROW_HEIGHT, x0:x1])
            row.crop_path, row.frame_path = str(crop_path), self._frame_path
            self.store.upsert_row(self.run_id, row)
            self.done.add(rank)
            s = self.summary
            s.processed += 1
            s.last_rank = max(s.last_rank, rank)
            if row.parse_status == "failed":
                s.failed += 1
            else:
                s.saved += 1
                s.partial += row.parse_status == "partial"
            log.info("%d위 저장 (%s)", rank, row.parse_status)
        return None

    def _recover(self, band: np.ndarray, band_top: int, client: np.ndarray,
                 shift: int | None) -> tuple[int, np.ndarray]:
        """DES-04 6 겹침 상실 복구: 되감기(+SCROLL_NOTCHES/2) 후 재측정, 2회 실패면 중단."""
        for _ in range(_RECOVER_RETRIES):
            log.warning("겹침 상실(이동량 %s) — 되감기 후 재측정", shift)
            self.input.wheel(*ui.SCROLL_POINT, ui.SCROLL_NOTCHES // 2)
            client = self._frame()
            shift = measure_shift(band, band_top, client)
            if shift is not None and shift < ui.SHIFT_MAX:
                return shift, client
        raise WalkAborted(f"겹침 상실 복구 실패(이동량 {shift})")
