"""픽스처 순위 셀에서 순위 숫자 글리프를 수확한다 (TASK-04, 1회성 도구).

실행: .venv\\Scripts\\python.exe tools\\harvest_digits.py [출력 디렉터리]
      (기본 assets/templates/digits_rank/. 기존 파일은 덮어쓰지 않는다.)

- 4위 이후 흰색 숫자: RankDigitReader와 같은 마스크·클러스터 규칙으로 글리프를 잘라 숫자마다
  첫 출현을 `<d>.png`(회색조)로 저장한다. 이후 출현은 저장본(변형 포함)과의 최대 NCC를
  출력하고, VARIANT_MIN_NCC 미만이면 변형 `<d>_<n>.png`로 추가 저장한다(판독기는 변형 중
  최대 점수를 취한다). 클러스터 수가 자릿수와 다른 셀은 건너뛴다.
- 1~3위 메달 숫자: 밝거나(V ≥ 120) 채도가 높은(S ≥ 100, V ≥ 90) 픽셀의 bbox + 여유 2px를
  회색조 `medal_<d>.png`로 저장한다. 이후 출현은 슬라이딩 NCC로 같은 규칙을 적용한다.
출력 표(파일·원본·클라이언트 좌표 상자)는 assets/templates/README.md 대장에 옮겨 적는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rankscan.nav import ui_ranking as ui  # noqa: E402
from rankscan.nav.list_scroller import detect_row_tops  # noqa: E402
from rankscan.nav.navigator import frame_client_offset  # noqa: E402
from rankscan.vision.digits import glyph_clusters, text_mask  # noqa: E402

IMG = ROOT / "img"
CLIENT = (2544, 657)
MEDAL_MARGIN = 2
VARIANT_MIN_NCC = 0.8   # 저장본과의 NCC가 이보다 낮은 출현은 변형 템플릿으로 추가
FIXTURES = [  # (픽스처, 완전 가시 행의 순위 — 2026-09-28 순위 셀 확인)
    ("p01_contrib_top", [1, 2, 3, 4, 5, 6]),
    ("p01_w2", [2, 3, 4, 5, 6, 7]),
    ("p01_w11", [5, 6, 7, 8, 9]),
    ("p01_b10_r121", [121, 122, 123, 124, 125]),
    ("p01_b11_r132", [132, 133, 134, 135, 136]),
    ("p01_end_r595_600", [595, 596, 597, 598, 599, 600]),
]


def _client(name: str) -> np.ndarray:
    frame = np.asarray(Image.open(IMG / f"{name}.png").convert("RGB"))
    ox, oy = frame_client_offset(frame.shape, CLIENT)
    return frame[oy:oy + CLIENT[1], ox:ox + CLIENT[0]]


def _medal_box(cell: np.ndarray) -> tuple[int, int, int, int]:
    hsv = cv2.cvtColor(cell, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    ys, xs = np.nonzero((v >= 120) | ((s >= 100) & (v >= 90)))
    h, w = cell.shape[:2]
    return (max(0, xs.min() - MEDAL_MARGIN), max(0, ys.min() - MEDAL_MARGIN),
            min(w, xs.max() + 1 + MEDAL_MARGIN), min(h, ys.max() + 1 + MEDAL_MARGIN))


def _ncc(image: np.ndarray, tpl: np.ndarray, slide: bool) -> float:
    """판독기와 같은 점수: 메달은 셀 안 슬라이딩 최고점, 흰색 글리프는 템플릿 크기로 리사이즈."""
    if not slide:
        image = cv2.resize(image, tpl.shape[::-1], interpolation=cv2.INTER_AREA)
    return float(cv2.matchTemplate(image, tpl, cv2.TM_CCOEFF_NORMED).max())


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, list[np.ndarray]] = {}
    rows: list[str] = []
    for name, ranks in FIXTURES:
        client = _client(name)
        tops = detect_row_tops(client)
        assert len(tops) == len(ranks), (name, tops)
        x0, dy0, x1, dy1 = ui.CELL_RANK
        for top, rank in zip(tops, ranks):
            cell = client[top + dy0:top + dy1, x0:x1]
            gray = cv2.cvtColor(cell, cv2.COLOR_RGB2GRAY)
            if rank <= 3:
                boxes = [(f"medal_{rank}", _medal_box(cell))]
            else:
                boxes = list(zip(str(rank), glyph_clusters(text_mask(cell))))
                if len(boxes) != len(str(rank)):
                    print(f"  skip {name} r{rank}: 클러스터 {len(boxes)}개 ≠ 자릿수 {len(str(rank))}")
                    continue
            for key, (bx0, by0, bx1, by1) in boxes:
                crop = gray[by0:by1, bx0:bx1]
                abs_box = tuple(int(v) for v in (x0 + bx0, top + dy0 + by0, x0 + bx1, top + dy0 + by1))
                variants = saved.setdefault(key, [])
                if variants:
                    medal = key.startswith("medal_")
                    score = max(_ncc(gray if medal else crop, tpl, slide=medal) for tpl in variants)
                    print(f"  {key:8s} {name} r{rank} {crop.shape[1]}x{crop.shape[0]} "
                          f"NCC vs 저장본 {score:.3f}" + (" → 변형 추가" if score < VARIANT_MIN_NCC else ""))
                    if score >= VARIANT_MIN_NCC:
                        continue
                path = out_dir / (f"{key}.png" if not variants else f"{key}_{len(variants) + 1}.png")
                if not path.exists():
                    Image.fromarray(crop).save(path)
                variants.append(np.asarray(Image.open(path).convert("L")))
                rows.append(f"| {path.name} | {key.removeprefix('medal_')} | img/{name}.png "
                            f"{abs_box} {crop.shape[1]}×{crop.shape[0]} | r{rank} |")
    print("\n대장 행(파일 | 문자 | 원본 (클라이언트 좌표) 크기 | 출처 순위):")
    print("\n".join(rows))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "templates" / "digits_rank")
