"""오케스트레이션·창 선택·실행 요약·라벨 확정 절차 (설계 DES-10).

TASK-01: 창 선택(choose_window)만 이식. run_scan·label_pending·summarize_run은
TASK-07에서 추가한다.
출처: sgz_statiz src/deckscan/controller.py choose_window·_select
(2026-09-28 이식, 무수정 — 문서 참조만 FR-09로 변경).
"""

from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)


def choose_window(candidates: list, ask: Callable[[str], str],
                  bring_front: Callable[[int], object]):
    """다중 클라이언트 창 후보에서 대상 1개를 확정한다(FR-09).

    ask(프롬프트)의 입력 규약: 번호=선택(bring_front로 전면 표시 후 y/n 확인),
    'q'=중단(None 반환). 후보가 하나면 묻지 않고 그대로 반환한다 — 동일 제목
    창은 제목으로 구분할 수 없어 전면 표시가 유일한 식별 수단이다.
    EOF(입력이 NUL 장치 등 비대화형 — Windows는 isatty()로 못 거른다)도
    중단으로 처리한다.
    """
    if len(candidates) == 1:
        return candidates[0]
    try:
        return _select(candidates, ask, bring_front)
    except EOFError:
        log.warning("입력 스트림 종료(비대화형) — 창 선택 중단")
        return None


def _select(candidates: list, ask, bring_front):
    lines = [f"{i}) hwnd={w.hwnd:#x} pid={w.pid} 위치=({w.rect[0]},{w.rect[1]}) "
             f"크기={w.rect[2]}x{w.rect[3]} elevated={w.elevated}"
             for i, w in enumerate(candidates, 1)]
    menu = ("같은 제목의 클라이언트 창이 여러 개입니다:\n" + "\n".join(lines) +
            f"\n대상 번호 입력(1~{len(candidates)}, q=중단): ")
    while True:
        answer = ask(menu).strip()
        if answer == "q":
            return None
        if not answer.isdigit() or not 1 <= int(answer) <= len(candidates):
            continue
        chosen = candidates[int(answer) - 1]
        try:
            bring_front(chosen.hwnd)
        except Exception:
            log.warning("창 전면 표시 실패: %#x", chosen.hwnd)
        if ask("전면에 표시된 창이 대상입니까? (y/n): ").strip().lower() == "y":
            return chosen
