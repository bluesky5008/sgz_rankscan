"""rankscan CLI (설계 DES-10): scan | probe | export | label.

출처: sgz_statiz src/deckscan/cli.py (2026-09-28 _resolve_session·_snap·cmd_probe 이식,
probe에 --wheel 추가; 2026-09-30 cmd_scan·cmd_export·cmd_label 이식 — 변경점: scan은
RankingNavigator·RowParser·ListScroller 조립과 --max-rank·--out(캡처 루트), export는
run당 1파일에 --run 생략 시 최신 run, label은 --namespace 필터).
종료 코드: 0 정상 / 1 실행 불가(창·권한·해상도·run 없음) / 2 순회 중단(controller.run_scan).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import sys
import time
from pathlib import Path

from PIL import Image

from .nav.ui_ranking import SCROLL_POINT
from .win import session
from .win.capture import WgcCapture
from .win.input import PostMessageInput

PROBE_DIR = Path("output") / "probe"
DEFAULT_DB = str(Path("output") / "rankscan.db")
DEFAULT_OUT = "output"                                  # scan 캡처 루트 → output/captures/run_<id>/
DEFAULT_EXPORT_DIR = str(Path("output") / "export")
REQUIRED_CLIENT = (2544, 657)                           # NFR-04 — 캘리브레이션 전제 해상도


def _resolve_session(hwnd_arg: int | None) -> session.WindowSession | None:
    """FR-09 창 확정: --hwnd 지정, 단일 자동, 다중 대화형 선택.

    비대화형 실행(stdin이 콘솔 아님)에서 다중 후보면 프롬프트 대기 없이
    후보 목록과 함께 거부한다 — 에이전트 실행기 보호.
    """
    if hwnd_arg is not None:
        return session.WindowSession(hwnd_arg)
    wins = session.find_client_windows()
    if not wins:
        print("대상 창 없음")
        return None
    if len(wins) > 1 and not sys.stdin.isatty():
        for w in wins:
            print(f"hwnd={w.hwnd:#x} pid={w.pid} rect={w.rect}")
        print("같은 제목의 창이 여러 개입니다 — 비대화형 실행은 --hwnd로 지정하세요")
        return None
    from .controller import choose_window
    from .win import win32
    chosen = choose_window(wins, input, win32.raise_to_top)
    if chosen is None:
        print("창 선택 중단")
        return None
    print(f"대상 창: hwnd={chosen.hwnd:#x} pid={chosen.pid} rect={chosen.rect}")
    return session.WindowSession(chosen.hwnd)


def _snap(cap: WgcCapture, tag: str) -> Path:
    frame = cap.grab_fresh()
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%H%M%S")
    path = PROBE_DIR / f"snap_{ts}_{tag}.png"
    Image.fromarray(frame).save(path)
    print(f"snapshot: {path}  frame={frame.shape[1]}x{frame.shape[0]}")
    return path


def cmd_probe(args: argparse.Namespace) -> int:
    for w in session.find_client_windows():
        print(f"hwnd={w.hwnd:#x} pid={w.pid} elevated={w.elevated} "
              f"rect={w.rect} client={w.client} title='{w.title}'")
    ws = _resolve_session(args.hwnd)
    if ws is None:
        return 1
    if args.click or args.wheel:
        ws.check_permission()   # 입력은 UIPI 제약 — 스냅샷만이면 승격 불필요
    info = ws.info()
    print(f"attached: hwnd={info.hwnd:#x} client={info.client}")
    with WgcCapture(info.hwnd, info.title) as cap:
        _snap(cap, "probe")
        inp = PostMessageInput(info.hwnd)
        if args.click:
            x, y = args.click
            inp.click(x, y)
            print(f"click: ({x},{y}) [클라이언트 좌표]")
            time.sleep(args.settle)
            _snap(cap, f"after_{x}x{y}")
        if args.wheel:
            x, y = SCROLL_POINT
            inp.wheel(x, y, args.wheel)
            print(f"wheel: {args.wheel:+d} notches at ({x},{y})")
            time.sleep(args.settle)
            _snap(cap, f"wheel_{args.wheel:+d}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from .controller import run_scan
    from .nav.list_scroller import ListScroller
    from .nav.navigator import ScreenJudge
    from .nav.ranking import RankingNavigator
    from .store.datastore import DataStore
    from .vision.row_parser import RowParser

    ws = _resolve_session(args.hwnd)
    if ws is None:
        return 1
    try:
        ws.check_permission()
    except Exception as e:
        print(f"입력 권한 없음: {e}")
        return 1
    info = ws.info()
    if info.client != REQUIRED_CLIENT:
        print(f"클라이언트 크기 {info.client} ≠ {REQUIRED_CLIENT} — 실행 거부(NFR-04)")
        return 1

    with DataStore(args.db) as store, \
            WgcCapture(info.hwnd, info.title) as cap:
        judge = ScreenJudge(cap, info.client)
        inp = PostMessageInput(info.hwnd)
        nav = RankingNavigator(judge, inp)
        parser = RowParser(store)

        def make_walker(run_id: int) -> ListScroller:
            return ListScroller(judge, inp, parser, store, run_id,
                                max_rank=args.max_rank,
                                captures_dir=Path(args.out) / "captures")

        code, summary = run_scan(store, nav, make_walker, max_rank=args.max_rank)
    print(summary)
    return code


def cmd_export(args: argparse.Namespace) -> int:
    from .store.csv_export import export_csv
    from .store.datastore import DataStore

    with DataStore(args.db) as store:
        run_id = args.run if args.run is not None else store.latest_run_id()
        if run_id is None:
            print("run 없음 — scan을 먼저 실행하세요")
            return 1
        print(f"export: {export_csv(store, args.out, run_id)}")
    return 0


def cmd_label(args: argparse.Namespace) -> int:
    import os

    from .controller import label_pending
    from .store.datastore import DataStore

    with DataStore(args.db) as store:
        n = label_pending(store, input, opener=os.startfile, namespace=args.namespace)
        print(f"라벨 확정 {n}건")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="rankscan",
                                description="공헌 랭킹 캡처·추출 도구")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("scan", help="공헌 랭킹 순회·캡처·추출 실행")
    ps.add_argument("--hwnd", type=lambda s: int(s, 0), default=None)
    ps.add_argument("--max-rank", type=int, default=600,
                    help="처리할 순위 상한 (기본 600)")
    ps.add_argument("--db", default=DEFAULT_DB)
    ps.add_argument("--out", default=DEFAULT_OUT,
                    help="캡처 저장 루트 — <DIR>/captures/run_<id>/ (기본 output)")
    ps.set_defaults(func=cmd_scan)

    pp = sub.add_parser("probe", help="창 진단·스냅샷·클릭·휠 (캘리브레이션용)")
    pp.add_argument("--hwnd", type=lambda s: int(s, 0), default=None)
    pp.add_argument("--click", type=int, nargs=2, metavar=("X", "Y"),
                    help="캘리브레이션용 클릭(클라이언트 좌표) 후 재스냅샷")
    pp.add_argument("--wheel", type=int, default=None, metavar="N",
                    help="SCROLL_POINT에 휠 N노치(음수=아래) 전송 후 재스냅샷")
    pp.add_argument("--settle", type=float, default=1.5,
                    help="클릭·휠 후 스냅샷까지 대기 초")
    pp.set_defaults(func=cmd_probe)

    pe = sub.add_parser("export", help="CSV 내보내기 (run당 1파일)")
    pe.add_argument("--db", default=DEFAULT_DB)
    pe.add_argument("--out", default=DEFAULT_EXPORT_DIR)
    pe.add_argument("--run", type=int, default=None,
                    help="대상 run ID (기본: 최신 run)")
    pe.set_defaults(func=cmd_export)

    pl = sub.add_parser("label", help="pending 식별자 라벨 확정")
    pl.add_argument("--db", default=DEFAULT_DB)
    pl.add_argument("--namespace", choices=("user", "region", "alliance"), default=None,
                    help="지정 네임스페이스의 pending만 순회 (기본: 전체)")
    pl.set_defaults(func=cmd_label)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
