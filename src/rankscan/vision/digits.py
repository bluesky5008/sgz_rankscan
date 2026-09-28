# 출처: sgz_statiz C:\src\git\sgz_statiz\src\deckscan\vision\digits.py (2026-09-28 이식,
#       원류 map_search mapscan/vision/digits.py). 변경점: DEFAULT_DIR → digits_rank, 클래스명
#       RankDigitReader, 진입점 read_rank(순위 셀). 좌표 파싱(read_coords)·콤마/괄호·초소형
#       글리프 처리와 과폭 클러스터 분할 가설은 제거(순위 셀에서 관찰되지 않는 실패 모드).
#       세그먼테이션 병합 복구는 항상 적용. 메달(1~3위) 글리프는 색 마스크 대신 회색조
#       슬라이딩 NCC(medal_N.png)로 판독.
"""순위 숫자 글리프 템플릿 판독 (설계 DES-08, ADR-002 결정 3).

순위 셀(ui_ranking.CELL_RANK, 80×40 RGB)은 두 부류다(2026-09-28 픽스처 실측,
tests/test_rank_digits.py):

- 1~3위: 금·은·동 메달 위의 큰 숫자. 세 색이 다르고 동색은 어두워(V 최대 ≈123) 흰색용
  색 마스크가 통하지 않는다 → 메달 글리프 템플릿 `medal_N.png`를 셀 회색조에서 슬라이딩
  NCC로 찾는다. 같은 메달·다른 프레임 0.946~0.951, 다른 메달·흰색 셀 ≤ 0.683 → 임계 0.8.
- 4위 이후: 흰색 숫자(S≈35, 획 중심 V≥200, 폭 6~10·높이 13~14px, 글리프 간격 2px).
  sgz_statiz와 같이 HSV 마스크 → 연결 성분 클러스터 → 템플릿 크기로 리사이즈해 NCC(임계
  0.45). 마스크 명도 하한은 sgz_statiz의 170이 아니라 130이다: 가는 가로 획(세리프, '4'의
  가로 막대, '1'의 깃발)이 부화소 위치에 따라 110~175를 오가 170에서는 글리프 상자가
  프레임마다 달라졌다('1' 폭 4~6, '4' 폭 7~9, '6' 좌우 분리). 130에서는 상자가 안정되고
  ('1' 6~7, 나머지 8~10) 셀 배경(V<90)과도 분리된다.
  '6'이 좌우 두 성분(간격 1px)으로 갈라지는 사례(170 기준)가 있어 병합 가설 복구를 항상
  적용한다(인접 숫자는 합쳐도 폭 ≥ 14 > 한 글리프 폭 + 1이라 잘못 병합되지 않는다).

글리프는 tools/harvest_digits.py로 픽스처에서 수확했다(대장 assets/templates/README.md).
"""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "assets" / "templates" / "digits_rank"

_MEDAL_PREFIX = "medal_"
_MEDAL_THRESHOLD = 0.8
_TEXT_MAX_SAT = 90
_TEXT_MIN_VAL = 130   # sgz_statiz 170 → 130 (모듈 docstring 참조)
_MIN_COMPONENT_AREA = 3
_MATCH_THRESHOLD = 0.45
_MAX_DIM_RATIO = 1.4  # 글리프와 템플릿의 폭·높이 비가 이 이상 다르면 후보 제외


class RankDigitReader:
    """순위 셀에서 메달 글리프(1~3위) 또는 흰색 숫자 글리프를 템플릿 매칭으로 읽는다."""

    def __init__(self, template_dir: Path | str = DEFAULT_DIR):
        self._glyphs: list[tuple[str, np.ndarray]] = []
        self._medals: list[tuple[str, np.ndarray]] = []
        for path in sorted(Path(template_dir).glob("*.png")):
            img = np.asarray(Image.open(path).convert("L"))
            if path.stem.startswith(_MEDAL_PREFIX):
                self._medals.append((path.stem[len(_MEDAL_PREFIX):], img))
            else:
                self._glyphs.append((re.sub(r"_\d+$", "", path.stem), img))  # 변형 접미사 제거
        if not self._glyphs:
            raise FileNotFoundError(f"글리프 템플릿이 없습니다: {template_dir}")

    def read_rank(self, cell: np.ndarray) -> str:
        """순위 셀(RGB)의 순위 문자열. 인식 실패 글리프는 '?', 글리프가 없으면 ''."""
        gray = cv2.cvtColor(cell, cv2.COLOR_RGB2GRAY)
        best, char = 0.0, ""
        for ch, tpl in self._medals:
            score = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED).max()
            if np.isfinite(score) and score > best:
                best, char = score, ch
        if best >= _MEDAL_THRESHOLD:
            return char
        mask = text_mask(cell)
        return self._read_repaired(gray, glyph_clusters(mask))

    def _read_repaired(self, gray: np.ndarray, clusters: list) -> str:
        w_digit = max(t.shape[1] for _, t in self._glyphs)
        out: list[str] = []
        i = 0
        while i < len(clusters):
            c = clusters[i]
            ch, sc = self._match_scored(_crop(gray, c))
            # 병합 가설: 다음 클러스터와 2px 이내 간격 + 병합 폭이 한 글리프 폭
            if i + 1 < len(clusters):
                nxt = clusters[i + 1]
                gap = nxt[0] - c[2]
                union = (c[0], min(c[1], nxt[1]), nxt[2], max(c[3], nxt[3]))
                if 0 <= gap <= 2 and union[2] - union[0] <= w_digit + 1:
                    _, sc_n = self._match_scored(_crop(gray, nxt))
                    ch_m, sc_m = self._match_scored(_crop(gray, union))
                    if ch_m != "?" and sc_m > max(sc, sc_n):
                        out.append(ch_m)
                        i += 2
                        continue
            out.append(ch)
            i += 1
        return "".join(out)

    def _match_scored(self, crop: np.ndarray) -> tuple[str, float]:
        ch, cw = crop.shape
        best_char, best_score = "?", _MATCH_THRESHOLD
        for char, tpl in self._glyphs:
            th, tw = tpl.shape
            if (max(ch, th) > _MAX_DIM_RATIO * min(ch, th) or
                    max(cw, tw) > _MAX_DIM_RATIO * min(cw, tw)):
                continue
            resized = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)
            score = cv2.matchTemplate(resized, tpl, cv2.TM_CCOEFF_NORMED)[0, 0]
            if np.isfinite(score) and score > best_score:
                best_char, best_score = char, score
        return best_char, (best_score if best_char != "?" else 0.0)


def text_mask(cell: np.ndarray) -> np.ndarray:
    """흰색 숫자 픽셀 마스크(uint8 0/1): 채도가 낮고 밝은 픽셀."""
    hsv = cv2.cvtColor(cell, cv2.COLOR_RGB2HSV)
    return ((hsv[:, :, 1] < _TEXT_MAX_SAT) &
            (hsv[:, :, 2] >= _TEXT_MIN_VAL)).astype(np.uint8)


def glyph_clusters(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """연결 성분을 x 구간이 겹치거나 맞닿는 것끼리 글리프 상자 (x0, y0, x1, y1)로 병합한다.

    글꼴 안티에일리어싱으로 한 글리프가 여러 성분으로 조각나는 경우를 흡수한다.
    글리프 사이 간격은 2px 이상이라 합쳐지지 않는다.
    """
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    comps = sorted(tuple(int(v) for v in stats[i][:4])
                   for i in range(1, n) if stats[i][4] >= _MIN_COMPONENT_AREA)
    clusters: list[list[int]] = []
    for x, y, w, h in comps:
        if clusters and x <= clusters[-1][2]:
            c = clusters[-1]
            c[0], c[1] = min(c[0], x), min(c[1], y)
            c[2], c[3] = max(c[2], x + w), max(c[3], y + h)
        else:
            clusters.append([x, y, x + w, y + h])
    return [tuple(c) for c in clusters]


def _crop(gray: np.ndarray, box: tuple) -> np.ndarray:
    x0, y0, x1, y1 = box
    return gray[y0:y1, x0:x1]
