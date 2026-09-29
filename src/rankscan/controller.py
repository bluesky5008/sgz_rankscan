"""오케스트레이션·창 선택·실행 요약·라벨 확정 절차 (설계 DES-10, FR-06·FR-07·FR-08·FR-09).

run_scan은 설계 §정상·실패·복구 흐름의 예외 경계다: 내비게이션·순회 실패는 run을
aborted로 마감하고 종료 코드 2를 반환하며, 이미 저장된 레코드는 유지한다. 초기화
실패(창·권한·해상도, 종료 코드 1)는 CLI가 담당한다.

출처: sgz_statiz src/deckscan/controller.py — choose_window·_select(2026-09-28 무수정
이식, 문서 참조만 FR-09로 변경), run_scan·label_pending·summarize_run(2026-09-30 이식.
변경점: create_run(max_rank), 중단 사유·순위 충돌 횟수를 runs.note에 기록, 요약에
순위 범위·결측·partial/failed 사유·비고 추가(FR-08), label_pending 네임스페이스 필터).
"""

from __future__ import annotations

import logging
from typing import Callable

from .store.datastore import DataStore

log = logging.getLogger(__name__)


def run_scan(store: DataStore, navigator, make_walker, *, max_rank: int) -> tuple[int, str]:
    """공헌 랭킹 순회 실행. 반환: (종료 코드 0|2, 요약 텍스트).

    make_walker(run_id) → ListScroller — run 기록과 워커 생성 순서를 분리한다.
    """
    run_id = store.create_run(max_rank)
    walker = None
    try:
        navigator.goto_contrib_tab()
        walker = make_walker(run_id)
        s = walker.walk()
    except Exception as exc:
        log.exception("scan 중단 — run #%d aborted", run_id)
        s = walker.summary if walker is not None else None
        store.finish_run(run_id, "aborted",
                         processed=s.processed if s else 0,
                         saved=s.saved if s else 0,
                         failed=s.failed if s else 0,
                         note=f"{type(exc).__name__}: {exc}")
        return 2, summarize_run(store, run_id)
    note = f"순위 충돌 {s.conflicts}회(프레임 재취득으로 복구)" if s.conflicts else None
    store.finish_run(run_id, "done", processed=s.processed, saved=s.saved,
                     failed=s.failed, note=note)
    return 0, summarize_run(store, run_id)


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


def label_pending(store: DataStore, ask: Callable[[str], str],
                  opener: Callable[[str], None] | None = None,
                  namespace: str | None = None) -> int:
    """pending 식별자를 순회하며 라벨을 확정한다(FR-07, AC-05).

    ask(프롬프트)의 입력 규약: 빈값=건너뜀(pending 유지), 'q'=중단,
    그 외=라벨 확정. opener(템플릿 경로)는 크롭 표시용(CLI가 뷰어 주입).
    namespace를 주면 그 네임스페이스의 pending만 순회한다. 반환: 확정한 식별자 수.
    """
    done = 0
    for row in store.pending_identities(namespace):
        templates = store.templates_of(row["identity_id"])
        template = templates[0] if templates else "?"
        if opener is not None:
            try:
                opener(template)
            except Exception:
                log.warning("크롭 표시 실패: %s", template)
        answer = ask(
            f"[{row['namespace']}#{row['identity_id']}] "
            f"제안='{row['label'] or ''}' 크롭={template} "
            f"→ 라벨 입력(빈값=건너뜀, q=종료): ").strip()
        if answer == "q":
            break
        if not answer:
            continue
        store.confirm_label(row["identity_id"], answer)
        done += 1
    return done


def summarize_run(store: DataStore, run_id: int) -> str:
    """run 요약 문자열(FR-08) — 처리 순위 범위, 저장·실패 수와 사유, 순위 연속성 이상
    (결측·비고), pending 식별자 수."""
    run = store.get_run(run_id)
    ranks = store.ranks_of(run_id)
    span = f"{ranks[0]}~{ranks[-1]}위" if ranks else "없음"
    lines = [f"run #{run_id} {run['status']} — 순위 {span}, 처리 {run['processed'] or 0}건, "
             f"저장 {run['saved'] or 0}건, 실패 {run['failed'] or 0}건"]
    counts = store.status_counts(run_id)
    if counts.get("partial") or counts.get("failed"):
        lines.append(f"인식 실패 사유: partial {counts.get('partial', 0)}건(일부 셀 미인식), "
                     f"failed {counts.get('failed', 0)}건(전 셀 실패)")
    missing = sorted(set(range(1, ranks[-1] + 1)) - set(ranks)) if ranks else []
    if missing:
        lines.append(f"순위 결측 {len(missing)}건: {missing[:20]}"
                     f"{' …' if len(missing) > 20 else ''}")
    if run["note"]:
        lines.append(f"비고: {run['note']}")
    pending = len(store.pending_identities())
    if pending:
        lines.append(f"미확정 식별자 pending {pending}건 — "
                     f"`rankscan label`로 라벨을 확정하세요")
    return "\n".join(lines)
