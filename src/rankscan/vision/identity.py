# 출처: sgz_statiz C:\src\git\sgz_statiz\src\deckscan\vision\identity.py (2026-09-28 이식,
#       원류 map_search 검증 구조). 변경점: 라벨 제안을 resolve 인수 대신 생성자 `suggest`
#       콜러블로 받아 신규 등록 시에만 호출(기존 식별자 매칭에 OCR 비용을 쓰지 않음), 제안
#       예외는 라벨 None으로 등록. 기본 임계 0.90 제거 → ui_ranking의 네임스페이스별 상수 필수.
"""템플릿 매칭 기반 안정 식별자 (설계 DES-06, ADR-001).

같은 렌더링은 픽셀이 거의 동일하다는 전제에서, 세력명·지역·동맹 셀 크롭을 등록된 템플릿과
슬라이딩 NCC로 대조해 안정적 ID를 부여한다. 미등록 크롭은 새 ID로 등록하고 라벨은
`pending`으로 남긴다(FR-05·FR-07).

템플릿은 크롭에서 가장자리 `inset`을 깎아 저장한다 — 행 상단 검출의 ±1px 지터를 슬라이딩
매칭(max)으로 흡수하기 위해서다. 임계는 ui_ranking의 `*_NCC_THRESHOLD`(2026-09-28 픽스처
실측, tests/test_identity.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from ..store.datastore import DataStore

log = logging.getLogger(__name__)

_INSET = 3
Suggest = Callable[[np.ndarray], "str | None"]


class IdentityMatcher:
    def __init__(self, store: DataStore, root: Path | str, namespace: str,
                 threshold: float, suggest: Suggest | None = None,
                 inset: int = _INSET):
        self.store = store
        self.root = Path(root)
        self.namespace = namespace
        self.threshold = threshold
        self.suggest = suggest
        self.inset = inset
        self.dir = self.root / "assets" / "templates" / namespace
        self._templates: list[tuple[int, np.ndarray]] = []
        for row in store.iter_identities(namespace):
            for rel in store.templates_of(row["identity_id"]):
                path = self.root / rel
                if path.is_file():
                    tpl = np.asarray(Image.open(path).convert("RGB"))
                    self._templates.append((row["identity_id"], tpl))
                else:
                    log.warning("템플릿 파일 없음: %s (identity %d)", rel, row["identity_id"])

    def resolve(self, crop: np.ndarray) -> tuple[int, float, bool]:
        """크롭을 식별한다. 반환: (identity_id, 매칭 점수, 신규 등록 여부)."""
        best_id, best = None, self.threshold
        for iid, tpl in self._templates:
            th, tw = tpl.shape[:2]
            if th > crop.shape[0] or tw > crop.shape[1]:
                continue
            score = float(cv2.matchTemplate(crop, tpl, cv2.TM_CCOEFF_NORMED).max())
            if score > best:
                best_id, best = iid, score
        if best_id is not None:
            return best_id, best, False
        return self._register(crop)

    def _register(self, crop: np.ndarray) -> tuple[int, float, bool]:
        label = None
        if self.suggest is not None:
            try:
                label = self.suggest(crop)
            except Exception:
                log.exception("%s 라벨 제안 실패 — 라벨 없이 등록", self.namespace)
        i = self.inset
        tpl = crop[i:crop.shape[0] - i, i:crop.shape[1] - i]
        self.dir.mkdir(parents=True, exist_ok=True)
        n = len(list(self.dir.glob("*.png"))) + 1
        path = self.dir / f"{self.namespace}_{n:06d}.png"
        Image.fromarray(np.ascontiguousarray(tpl)).save(path)
        rel = path.relative_to(self.root).as_posix()
        iid = self.store.create_identity(self.namespace, label, rel)
        self._templates.append((iid, tpl))
        log.info("신규 %s 등록: identity %d (%s) 제안=%r", self.namespace, iid, rel, label)
        return iid, 1.0, True
