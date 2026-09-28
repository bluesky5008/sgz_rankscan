"""rankscan CLI (설계 DES-10): scan | probe | export | label.

TASK-01: probe만. scan·export·label은 TASK-07에서 추가한다.
출처: sgz_statiz src/deckscan/cli.py _resolve_session·_snap·cmd_probe
(2026-09-28 이식; probe에 --wheel 추가 — 설계 DES-10 CLI 계약).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
import time
from pathlib import Path

from PIL import Image

from .nav.ui_ranking import SCROLL_POINT
from .win import session
from .win.capture import WgcCapture
from .win.input import PostMessageInput

PROBE_DIR = Path("output") / "probe"


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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rankscan",
                                description="공헌 랭킹 캡처·추출 도구")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("probe", help="창 진단·스냅샷·클릭·휠 (캘리브레이션용)")
    pp.add_argument("--hwnd", type=lambda s: int(s, 0), default=None)
    pp.add_argument("--click", type=int, nargs=2, metavar=("X", "Y"),
                    help="캘리브레이션용 클릭(클라이언트 좌표) 후 재스냅샷")
    pp.add_argument("--wheel", type=int, default=None, metavar="N",
                    help="SCROLL_POINT에 휠 N노치(음수=아래) 전송 후 재스냅샷")
    pp.add_argument("--settle", type=float, default=1.5,
                    help="클릭·휠 후 스냅샷까지 대기 초")
    pp.set_defaults(func=cmd_probe)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
