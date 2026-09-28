# 출처: sgz_statiz C:\src\git\sgz_statiz\src\deckscan\vision\ocr.py (2026-09-28 이식). 변경점:
#       suggest_label만 남기고 read_number·read_datetime·ResultReader·일시 정규식을 제거(DES-07).
#       suggest_label은 4배 이진화를 1순위로 하고 빈 결과면 4배 확대로 폴백(P-02·실측).
"""Windows 내장 OCR 어댑터 — 신규 식별자의 라벨 제안 전용 (설계 DES-07, ADR-001).

2026-09-28 ranking_1 실측(tests/test_ocr.py): 4배 이진화 — 지역 6/6, 동맹 잠룡·백련·삼룡
정독(잡룡 2건, 빈 결과 1건), 세력명 0/6(한자 접두·장식 프레임). 4배 이진화가 빈 결과인
셀('맹수')은 4배 확대가 정독 → 폴백. 제안은 정확성을 보장하지 않으며 사용자가 `label`로
확정한다. 엔진 교체는 이 모듈 교체로 한정된다.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

_BIN_THRESHOLD = 150


def _upscale(crop: np.ndarray, scale: int) -> Image.Image:
    im = Image.fromarray(np.ascontiguousarray(crop))
    return im.resize((im.width * scale, im.height * scale), Image.LANCZOS)


def _binarize(crop: np.ndarray, scale: int) -> Image.Image:
    """이진화(검은 글자/흰 배경) + 잡음 성분 제거 + 여백 패딩.

    카드 테두리 파편 같은 소형 잡음과 여백 부족이 Windows OCR의 인식 거부를 유발한다
    (sgz_statiz 실측) — 성분 면적 필터와 12px 흰 여백으로 정리한다. 닫힘 연산 5px는 렌더
    변형으로 끊긴 획만 잇는다.
    """
    gray = np.asarray(_upscale(crop, scale).convert("L")).astype(np.int16)
    text = (gray >= _BIN_THRESHOLD).astype(np.uint8)   # 밝은 글자=1
    text = cv2.morphologyEx(text, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(text, connectivity=8)
    keep = np.zeros_like(text)
    min_area = 10 * scale * scale
    for i in range(1, n):
        if stats[i][4] >= min_area:
            keep[labels == i] = 1
    out = np.where(keep == 1, 0, 255).astype(np.uint8)
    pad = 12
    out = cv2.copyMakeBorder(out, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    return Image.fromarray(out).convert("RGB")


class OcrReader:
    def __init__(self, lang: str = "ko"):
        self.lang = lang

    def _ocr(self, img: Image.Image) -> str:
        import winocr  # 임포트 지연 — 픽스처 전용 테스트 환경 고려
        r = winocr.recognize_pil_sync(img, lang=self.lang)
        return (r.get("text", "") if isinstance(r, dict)
                else getattr(r, "text", "")) or ""

    def suggest_label(self, crop: np.ndarray) -> str | None:
        """신규 식별자 등록용 라벨 제안 — 정확성을 보장하지 않는다(ADR-001). 실패 시 None."""
        for img in (_binarize(crop, 4), _upscale(crop, 4)):
            text = self._ocr(img).strip().replace("\n", " ")
            if text:
                return text
        return None
