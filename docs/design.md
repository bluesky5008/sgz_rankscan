# DESIGN-sgz-rankscan: 공헌 랭킹 캡처·추출 SW 설계

> 문서 유형: `design`
> 작업 ID: `20260928-contrib-ranking-capture`
> 상태: `approved`
> 기준선: `v1` (승인일 2026-09-28)
> 작성일: 2026-09-28
> 최종 갱신: 2026-09-28
> 관련 문서: [REQ-sgz-rankscan: 요구사항](./requirements.md), [ADR-001: 인식 전략](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md), [ADR-002: 순위 확정 전략](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md)

## 요약

- 목적: [요구사항](./requirements.md)을 만족하는 캡처·추출 도구 `rankscan`의 구조·계약·동작을 정의한다.
- 현재 결론 또는 상태: 기준선 v1 승인 완료(2026-09-28, 사용자). sgz_statiz 플랫폼 계층 재사용 + 랭킹 화면 전용 모듈(좌표 상수, 화면 이동, 목록 스크롤러, 행 파서, 순위 글리프). 텍스트는 템플릿 ID + OCR 제안([ADR-001](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md)), 순위는 이동량 측정 이어붙임 + 숫자 교차 검증([ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md)). 실기 P-01로 클릭 좌표·행 배치·스크롤 특성·목록 끝(600위, 휠 무효)을 실측했다.
- 다음 행동: wf-implement 계획 수립.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-sgz-rankscan: 요구사항](./requirements.md) | document | 이 설계가 구체화하는 요구사항 |
| input | decision | [ADR-001: 인식 전략](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md) | ADR-001 | DES-06·DES-07의 근거 |
| input | decision | [ADR-002: 순위 확정 전략](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md) | ADR-002 | DES-04·DES-08의 근거 |
| input | related | [sgz_statiz 저장소](file:///C:/src/git/sgz_statiz) | document | 재사용 원천(win/·navigator·identity·digits·ocr·datastore·csv_export). 외부 저장소라 역방향 링크 불가 |
| input | related | [결정 등록부](./decisions.md) | ADR-001, ADR-002 | 전역 결정 목록 |
| output | handoff | [PLAN-sgz-rankscan: 구현 계획](./plan.md) | TASK-01~09 | 이 설계를 번역한 구현 계획 |

## 설계 목표와 제약

- 목표: 수동 개입 없는 1회 실행으로 공헌 랭킹 1~600위(또는 목록 끝)를 순회·캡처·추출·저장하고, 순위 무결성 이상과 인식 실패를 증거와 함께 표면화한다.
- 제약:
  - 클라이언트 2544×657 전제(NFR-04). 불일치 시 실행 거부.
  - 게임 화면을 바꾸는 클릭은 상수 모듈의 좌표 화이트리스트로 한정하고, 목록 안에서는 클릭하지 않는다(휠만).
  - 가려진 창에서도 동작: WGC 캡처 + PostMessage 입력(NFR-05).
  - 게임이 상승 권한이면 도구도 상승 권한이어야 입력이 전달된다(sgz_statiz와 동일, `tools/agent_shell_admin.bat` 이식).

## 시스템 경계와 구조

로컬 PC의 단일 CLI 프로세스. 외부 연동은 (1) 게임 클라이언트 창(캡처·입력), (2) 로컬 SQLite·이미지 파일, (3) 템플릿 자산 디렉터리뿐이다. 네트워크 통신은 없다.

```text
CLI(scan|probe|export|label)
  └─ Controller ─────────────── run 기록, 요약, 예외 경계
       ├─ 플랫폼 계층(DES-01)      창 탐색·권한·WGC 캡처·PostMessage 입력  ← sgz_statiz 무수정 복사
       ├─ RankingNavigator(DES-03) 메인 → 더 보기 → 랭킹 → 공헌 랭킹 탭  (ui_ranking 상수 DES-02)
       ├─ ListScroller(DES-04)     행 검출·이동량 측정·순위 이어붙임·스크롤·종료
       ├─ RowParser(DES-05)        행 크롭 → RankRow
       │    ├─ IdentityMatcher(DES-06)  user/region/alliance 템플릿 ID
       │    ├─ OcrReader(DES-07)        신규 ID 라벨 제안
       │    └─ RankDigitReader(DES-08)  순위 숫자 교차 검증
       └─ DataStore + CsvExport(DES-09) SQLite 저장·CSV
```

프로젝트 구조(신규 저장소 `sgz_rankscan`, 패키지 `rankscan`):

```text
sgz_rankscan/
├── pyproject.toml            # Python ≥3.12, pillow numpy opencv-python windows-capture winocr
├── src/rankscan/
│   ├── cli.py  controller.py
│   ├── win/    # win32.py capture.py input.py session.py  ← sgz_statiz 무수정 복사(출처 주석)
│   ├── nav/    # navigator.py(이식)  ui_ranking.py(신규 상수)  ranking.py(화면 이동)  list_scroller.py
│   ├── vision/ # row_parser.py  identity.py(이식)  digits.py(이식)  ocr.py(이식·축소)
│   └── store/  # datastore.py(스키마 교체)  csv_export.py(이식)
├── assets/templates/         # ui/ digits_rank/ user/ region/ alliance/ + README.md(자산 대장)
├── img/                      # 참고 이미지·P-01 스냅샷 선별본(테스트 픽스처 원본)
├── tools/                    # agent_shell.ps1, agent_shell_admin.bat (이식)
├── output/                   # rankscan.db, captures/, export/  (커밋 제외)
└── docs/                     # requirements.md design.md decisions.md work/<작업-ID>/
```

## 컴포넌트와 책임

| ID | 항목 | 내용 |
|---|---|---|
| DES-01 | 플랫폼 계층 | [sgz_statiz win/](file:///C:/src/git/sgz_statiz/src/deckscan/win) 4개 모듈을 무수정 복사(파일 머리에 출처·복사일 주석). 창 탐색(`삼국지-전략판`)·UIPI 권한 검사·WGC 캡처(`grab_fresh`, `CaptureStalled`)·PostMessage 클릭·휠. 창 선택 절차(FR-09)는 sgz_statiz `choose_window`·`_resolve_session` 이식. |
| DES-02 | ui_ranking 상수 모듈 | 유일한 캘리브레이션 지점. [상세](#des-02-상세) — 클릭 좌표, 화면 마커, 목록 영역, 행 기하, 셀 상자, 스크롤 파라미터. |
| DES-03 | RankingNavigator | 메인(또는 메뉴 열림) → `더 보기` → `랭킹` → `공헌 랭킹` 탭. 각 클릭 직전 현재 화면 마커 재검증, 목표 마커 등장 + `wait_stable`로 성공 판정, 무반응 1회 재시도(sgz_statiz TelegramNavigator 골격 이식). 시작 시 이미 랭킹 화면(공헌 탭 활성)이면 이동 생략(FR-01). |
| DES-04 | ListScroller | [ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md) 구현. [상세](#des-04-상세) — 시작 조건(상단·1위 확인), 행 검출, 이동량 측정, 순위 이어붙임, 완전 가시 행 처리, 겹침 상실 복구, 종료 판정. |
| DES-05 | RowParser | 행 크롭(목록 x 전폭 × 행 높이)과 순위를 받아 `RankRow`를 만든다. 셀 상자(DES-02)로 세력명·지역·동맹을 잘라 DES-06으로 ID화하고 DES-08로 순위 숫자를 읽는다. 셀별 실패를 모아 `ok | partial | failed`를 판정한다. 파싱은 순수 함수에 가깝게 두어 정지 이미지로 테스트한다(AC-02). |
| DES-06 | IdentityMatcher | [sgz_statiz identity.py](file:///C:/src/git/sgz_statiz/src/deckscan/vision/identity.py) 이식. 네임스페이스 `user`·`region`·`alliance`. 임계 이상 최고점 채택, 미등록이면 새 ID 발행 + 크롭 템플릿 저장 + OCR 제안 라벨로 `pending` 등록. 임계는 실기 교차 측정으로 보정(초기값 0.80, sgz_statiz 텍스트 스트립 실측 준용). |
| DES-07 | OcrReader | [sgz_statiz ocr.py](file:///C:/src/git/sgz_statiz/src/deckscan/vision/ocr.py)의 winocr 어댑터·이진화 전처리만 이식(일시·인장 판독 제거). 용도는 신규 ID 라벨 제안뿐(ADR-001). P-02 기준 4배 이진화를 1순위로 한다. |
| DES-08 | RankDigitReader | [sgz_statiz digits.py](file:///C:/src/git/sgz_statiz/src/deckscan/vision/digits.py) 이식(템플릿 디렉터리 `digits_rank/`). 순위 셀에서 흰색 0~9·금색 1~3 글리프를 판독한다. 글리프는 P-01 스냅샷에서 수확한다. 판독 실패는 `?`로 반환하고 검증을 생략한다. |
| DES-09 | DataStore + CsvExport | SQLite 원장(WAL, run 기록, `INSERT OR REPLACE` 멱등) 골격을 [sgz_statiz datastore.py](file:///C:/src/git/sgz_statiz/src/deckscan/store/datastore.py)에서 이식하고 스키마를 아래로 교체. CSV는 UTF-8(BOM). |
| DES-10 | Controller/CLI | `scan`(순회 실행), `probe`(창 진단·스냅샷·클릭·휠 캘리브레이션), `export`(CSV), `label`(pending 라벨 확정). 실행 요약(FR-08)과 예외 경계(아래 실패 흐름). 종료 코드 0 정상 / 1 실행 불가(창·권한·해상도) / 2 순회 중단. |

#### DES-02 상세

좌표계: 클라이언트 픽셀(2544×657). 값은 P-01(2026-09-28 실기, 창 0x206be)과 참고 이미지 실측이며, 구현 초기 실기 스냅샷으로 재확인한다.

| 상수 | 값 | 근거 |
|---|---|---|
| `CLICK_MORE` | (1432, 631) | sgz_statiz 실기 검증 좌표 재사용 |
| `CLICK_MENU_RANKING` | (1235, 585) | P-01 메뉴 크롭 실측(버튼 약 100×38). (1230, 583) 클릭으로 랭킹 화면 도달 확인 |
| `CLICK_CONTRIB_TAB` | (1378, 138) | P-01 클릭으로 공헌 탭 활성 확인 |
| `CLICK_RETURN` | (2499, 24) | 우상단 `귀환`(sgz_statiz 동일) — 화면 이탈 복구용 |
| `MARKER_MAIN`, `MARKER_MENU` | sgz_statiz `main_more.png`·`menu_alliance.png` 템플릿과 상자 재사용 | 메뉴 열림 상태에서 `더 보기` 재클릭 시 토글 닫힘 주의(동일) |
| `MARKER_RANKING` | 좌상단 제목 `랭킹` 영역(약 x 10~100, y 28~56) 템플릿 | 구현 시 스냅샷에서 수확·NCC 교차 측정 |
| `MARKER_CONTRIB_TAB` | 활성 탭 강조 테두리 영역(약 x 1300~1460, y 120~158) 템플릿 | 비활성 탭과 분리되는 상자로 수확 |
| `LIST_REGION` | (960, 200, 1860, 635) | 열 헤더 아래 ~ 패널 바닥. 상·하단에서 행이 잘림 |
| `ROW_PITCH`, `ROW_HEIGHT` | 71, 65 | P-01 행 테두리 실측(268→339→410→482→553→624, 평균 71.2) |
| `ROW_LINE_COL` | x 1140~1160 | 순위·세력 열 사이 빈 열. 행 테두리 수평선(밝기 피크)이 5~9px 간격 쌍으로 나타나며 쌍의 둘째가 행 상단 |
| `CELL_RANK` | (1030, +12, 1110, +52) | 행 상단 기준 상대 상자. 순위 숫자 중심 x≈1068 |
| `CELL_NAME` | (1180, +18, 1400, +48) | 세력명(장식 프레임 포함 폭) |
| `CELL_REGION` | (1460, +18, 1560, +48) | 지역 |
| `CELL_ALLIANCE` | (1690, +18, 1790, +48) | 동맹(밑줄 포함) |
| `SCROLL_POINT` | (1400, 420) | 목록 중앙, 링크 없는 열. 커서가 머물러도 행 렌더 변화 없음(P-01 관찰) |
| `SCROLL_NOTCHES` | 12 (초기값) | P-01: 1노치 33px, 3노치 62px, 6노치 114px, 50노치 ≈815px(11.4행) — 비선형. 12노치 ≈ 200~250px(3행 내외) 추정, 겹침 상한 364px 안. 구현 시 실측 보정 |
| `SHIFT_MAX` | 364 | `LIST_REGION` 높이 435 − `ROW_PITCH` 71 — 이를 넘으면 겹침 상실 |
| `ANCHOR_NCC_THRESHOLD` | 0.80 (초기값) | P-01 띠 매칭 0.83~0.96. 구현 시 보정 |

#### DES-04 상세

상태: `anchor = (rank, top_y)`(직전 프레임의 마지막 완전 가시 행), `done: set[rank]`, `step`.

1. **시작**: 안정 프레임에서 행 검출. 첫 완전 가시 행의 순위 셀을 DES-08로 읽어 `1`이면 `anchor=(1, top)`. 아니면 위로 되감기(`+SCROLL_NOTCHES×10`) 후 재판정, 2회 실패 시 중단(exit 2).
2. **행 검출**: `ROW_LINE_COL` 밝기 피크로 행 상단 y 목록을 만들고, `LIST_REGION` 안에 상단·하단(`top+ROW_HEIGHT`)이 모두 든 행만 완전 가시 행으로 채택.
3. **순위 이어붙임**: 각 완전 가시 행 `rank = anchor.rank + round((top − anchor.top) / ROW_PITCH)`. 첫 프레임은 anchor 자체가 기준.
4. **처리**: `rank ∉ done`이고 `rank ≤ max_rank`인 행마다 DES-05 파싱 → 행 크롭 `rank_NNN.png` 저장 → DataStore upsert → `done`에 추가. 순위 숫자 판독값이 있고 `rank`와 다르면 `rank_conflict`: 프레임 재취득 1회, 재발 시 중단.
5. **종료**: `max(done) ≥ max_rank` → 정상 종료. 스크롤 후 목록 영역이 직전과 동일(`same_image`) → 목록 끝, 정상 종료.
6. **스크롤·측정**: anchor 행의 `CELL_NAME` 띠(행 전폭 × 30px)를 보관 → `wheel(SCROLL_POINT, −SCROLL_NOTCHES)` → `wait_stable` → 새 프레임의 `LIST_REGION`에서 띠를 NCC 매칭. 점수 ≥ 임계이고 이동량 `anchor.top − y₁` ∈ (0, `SHIFT_MAX`)이면 `anchor.top = y₁`로 갱신하고 2로 돌아간다. 아니면 **겹침 상실 복구**: `wheel(+SCROLL_NOTCHES/2)` 후 재측정, 2회 실패 시 중단(저장분 유지, exit 2).
7. anchor 갱신: 처리 후 마지막 완전 가시 행으로 교체(다음 단계의 겹침 최대화).

증거: 단계마다 `LIST_REGION` 크롭을 `frames/step_NNNN.png`로 저장(전체 프레임은 오류 시에만) — FR-04.

## 데이터와 인터페이스

### SQLite 스키마 (`output/rankscan.db`)

```sql
meta(key TEXT PRIMARY KEY, value TEXT);                     -- schema_version = 1

runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT,
     started_at TEXT, finished_at TEXT,
     status TEXT DEFAULT 'running',                         -- running|done|aborted
     max_rank INTEGER, processed INTEGER, saved INTEGER, failed INTEGER,
     note TEXT);                                            -- 중단 사유·연속성 이상 요약

identities(identity_id INTEGER PRIMARY KEY AUTOINCREMENT,
     namespace TEXT,                                        -- user|region|alliance
     label TEXT, label_status TEXT DEFAULT 'pending',       -- pending|confirmed
     first_seen TEXT);
identity_templates(identity_id INTEGER REFERENCES identities,
     template_path TEXT, PRIMARY KEY (identity_id, template_path));

rank_rows(run_id INTEGER REFERENCES runs, rank INTEGER,
     user_id INTEGER, region_id INTEGER, alliance_id INTEGER,   -- identities, 미인식 NULL
     user_score REAL, region_score REAL, alliance_score REAL,
     rank_read TEXT,                                        -- DES-08 판독 문자열('?' 포함 가능)
     crop_path TEXT, frame_path TEXT,
     parse_status TEXT DEFAULT 'ok',                        -- ok|partial|failed
     captured_at TEXT,
     PRIMARY KEY (run_id, rank));
```

- `(run_id, rank)` 기본키가 FR-06의 "같은 run 안 같은 순위 1건"을 구조적으로 보장하고, run이 다르면 모두 보존된다. 같은 run에서 같은 순위를 재처리하면 `INSERT OR REPLACE`로 덮어쓴다(재취득 프레임 처리).
- 템플릿 파일은 `assets/templates/<namespace>/<namespace>_NNNNNN.png`. 식별자 레지스트리(user/region/alliance 템플릿)는 DB와 함께 운영 데이터이므로 커밋 제외(sgz_statiz 동일).

### 파일 산출물

```text
output/captures/run_<id>/rank_001.png … rank_600.png   # 행 크롭(목록 x 전폭 × ROW_HEIGHT)
output/captures/run_<id>/frames/step_0000.png …         # 단계별 LIST_REGION 크롭(증거)
output/captures/run_<id>/error_<step>.png               # 중단 시 전체 프레임
output/export/ranks_<run_id>_<YYYYMMDD>.csv
```

CSV 열: `run_id, captured_at, rank, user, region, alliance, user_id, region_id, alliance_id, parse_status, rank_read, crop_path`. 라벨 미확정은 `#<id>(<제안>)` 표기(FR-10).

### 내부 계약

```python
@dataclass
class RankRow:
    rank: int
    user_id: int | None; region_id: int | None; alliance_id: int | None
    user_score: float | None; region_score: float | None; alliance_score: float | None
    rank_read: str | None
    crop_path: str | None; frame_path: str | None
    parse_status: str = "ok"          # ok|partial|failed

class RowParser:   def parse(frame: ndarray, top: int, rank: int) -> RankRow
class ListScroller: def walk() -> WalkSummary   # processed, saved, failed, partial, conflicts, last_rank, stop_reason
class RankingNavigator: def goto_contrib_tab() -> ndarray
```

CLI:

```text
rankscan scan   [--hwnd N] [--max-rank 600] [--db PATH] [--out DIR]
rankscan probe  [--hwnd N] [--click X Y] [--wheel N] [--settle S]
rankscan export [--db PATH] [--out DIR] [--run ID]
rankscan label  [--db PATH] [--namespace user|region|alliance]
```

## 정상·실패·복구 흐름

정상: 창 확정(FR-09) → 권한·크기 검증 → 캡처 세션 → 화면 판정(이미 공헌 탭이면 생략, 아니면 DES-03 이동) → DES-04 시작 조건 → 루프(행 검출 → 순위 이어붙임 → 미처리 행 파싱·저장 → 종료 판정 → 스크롤·측정) → run 마감 → 요약 출력.

| 상황 | 감지 | 대응 | 결과 |
|---|---|---|---|
| 창 없음·다중 비대화형·권한·크기 불일치 | 초기화 검사 | 메시지 출력 | exit 1 |
| 이동 단계 목표 마커 미등장 | `wait_marker` 타임아웃 | 1회 재클릭(직전 화면 재검증 후) | 실패 시 exit 2 |
| 랭킹 화면 이탈(마커 소실, 팝업 등) | 루프마다 `MARKER_RANKING` 확인 | `귀환` 1회 후 재판정 | 실패 시 exit 2 |
| 시작 시 1위가 보이지 않음 | DES-08 판독 ≠ 1 | 위로 되감기 후 재판정(2회) | 실패 시 exit 2 |
| 겹침 상실·anchor 미발견 | NCC < 임계 또는 이동량 ∉ (0, SHIFT_MAX) | 되감기 후 재측정(2회) | 실패 시 exit 2, 저장분 유지 |
| 순위 교차 불일치 | 판독값 ≠ 이어붙임 순위 | 프레임 재취득 1회 | 재발 시 exit 2, `runs.note`에 기록 |
| 셀 인식 실패(임계 미달·빈 크롭) | RowParser | `partial|failed` 저장, 계속 | 요약에 집계(NFR-01) |
| 캡처 정지 | `CaptureStalled`(창 생존 시 정적 화면 수용 — sgz_statiz `ScreenJudge.fresh`) | 중단 | exit 2 |
| 목록 끝 | 스크롤 후 `same_image` | 정상 종료 | exit 0, `stop_reason=end` |

## 보안과 품질 속성

- 네트워크 없음, 비밀 정보 없음. 게임에 공개 표시되는 정보만 다룬다.
- 권한: 게임이 상승 권한이면 도구도 상승 필요(`tools/agent_shell_admin.bat`). 캡처 전용 `probe`는 승격 불필요.
- 성능: 단계당 이동 3행 내외 기준 600위 ≈ 200단계, 단계당 휠 0.7s + 안정화 ≈ 2s → 약 7분(추정, 구현 시 실측).
- 관측성: 단계·순위·복구·중단 사유를 로그와 `runs.note`에 남기고, 실행 요약(FR-08)에 처리 범위·실패·충돌·pending 수를 출력.
- 유지보수: 좌표·임계는 DES-02 한곳. 게임 UI 변경 시 이 모듈과 `assets/templates/ui/`만 갱신.

## 마이그레이션과 롤백

- 신규 저장소·신규 DB(`schema_version=1`) — 마이그레이션 없음. 롤백은 `output/` 삭제로 충분하며 게임 상태를 바꾸지 않는다.
- 게임 화면은 실행 종료 후 공헌 랭킹 화면에 머문다(복귀는 수동, 요구사항 범위 제외).

## 검증 전략

| 대상 | 방법 | 픽스처·환경 |
|---|---|---|
| 행 검출·완전 가시 판정, 이동량 측정, 순위 이어붙임 | 단위 테스트(정지 이미지 쌍) | P-01 스냅샷 선별본(`img/`) — 예: w1→w2(33px), b10→b11(겹침 상실 사례) |
| RankDigitReader | 단위 테스트(수확 글리프, 흰색·금색) | P-01 스냅샷의 순위 셀 |
| RowParser·IdentityMatcher | AC-02 오프라인 검증(참고 이미지 6행) | `img/ranking_1.png`, 인메모리 DB |
| DataStore·CsvExport | 단위 테스트(멱등, (run, rank) 유일성, CSV 열) | `:memory:` |
| 창 선택(FR-09) | 단위 테스트(입력 콜백 주입) | sgz_statiz test_controller 이식 |
| AC-01, AC-03, AC-04, AC-07, AC-08 | 실기 실행(승격 러너) | 실기 클라이언트 |

## 대안과 결정

- 인식 전략: [ADR-001](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md) — 템플릿 ID + OCR 제안 + 사용자 확정(OCR 단독 기각).
- 순위 확정: [ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md) — 이동량 측정 이어붙임 + 숫자 교차 검증(고정 이동량·숫자 단독 기각).
- 저장 형식: SQLite 원장 + CSV 내보내기. [sgz_statiz ADR-001](file:///C:/src/git/sgz_statiz/docs/work/20260808-telegram-deck-extract/decisions/ADR-001-storage-format.md)의 근거(멱등 upsert, 조회, 라벨 레지스트리 공존)가 그대로 성립하고 새 대안이 없어 별도 ADR 없이 계승한다.
- 재사용 방식: 공용 패키지화 대신 파일 복사(출처 주석). 두 도구가 독립 배포·독립 캘리브레이션이라 결합을 피한다(sgz_statiz가 map_search에서 택한 방식과 동일).
- 스크롤 입력: 휠만 사용(드래그 기각 — 관성·오클릭 위험, 휠은 P-01에서 안정 동작 확인).

## 가정과 미해결 질문

- 가정 A-06: 랭킹 화면을 처음 열면 공헌 탭 목록은 상단(1위)에서 시작한다(P-01: 탭 클릭 직후 1~6위 표시). 시작 조건 검사(DES-04 1)로 방어한다.
- 가정 A-07 → 사실(P-01 버스트 52~60): 본 서버 공헌 랭킹 목록은 **600위에서 끝난다**. 끝 화면은 595~600위 6행이 완전 가시로 정렬되고, 이후 휠은 무효라 목록 영역이 직전 프레임과 동일하다(`same_image` 8회 연속 관찰). 따라서 DES-04 5의 종료 판정이 성립하며 `--max-rank` 기본값 600은 게임 한계와 일치한다.
- 가정 A-08: 커서가 `SCROLL_POINT`에 머물러도 행 렌더가 바뀌지 않는다(P-01 w1~w11 관찰). 실기에서 호버 강조가 확인되면 `MOUSE_PARK` 상수를 추가한다.

## 위험

| ID | 위험 | 영향 | 완화 |
|---|---|---|---|
| RISK-06 | `SCROLL_NOTCHES` 초기값이 실기에서 겹침 상한을 넘거나 너무 작음 | 복구 반복·속도 저하 | 구현 초기 실기 보정, 겹침 상실 복구 경로 |
| RISK-07 | 실행 중 랭킹 갱신으로 anchor 행 내용 변경 | 겹침 상실 | 되감기 복구 → 실패 시 중단(저장분 유지) |
| RISK-08 | 글리프·마커·식별 임계 미보정 | 오탐·미탐 | 실기 교차 측정으로 보정, 판독 실패는 검증 생략으로 처리 |
| RISK-09 | 세력명 렌더 변형(칭호 변경) | 같은 유저의 ID 분리 | 라벨 확정으로 이름 통일(ID 병합은 범위 밖) |

## 추적성

| 요구사항 | 설계 | 인수 조건 | 검증 |
|---|---|---|---|
| [FR-01](./requirements.md#기능-요구사항) | DES-02, DES-03 | AC-01 | 실기 |
| [FR-02](./requirements.md#기능-요구사항) | DES-04 | AC-03, AC-08 | 단위 + 실기 |
| [FR-03](./requirements.md#기능-요구사항) | DES-04, DES-08 ([ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md)) | AC-03 | 단위 + 실기 |
| [FR-04](./requirements.md#기능-요구사항) | DES-04 증거 저장 | AC-03 | 실기 |
| [FR-05](./requirements.md#기능-요구사항) | DES-05, DES-06, DES-07 ([ADR-001](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md)) | AC-02, AC-05 | 오프라인 |
| [FR-06](./requirements.md#기능-요구사항) | DES-09 | AC-03 | 단위 |
| [FR-07](./requirements.md#기능-요구사항) | DES-10 `label`, DES-09 | AC-05 | 단위 |
| [FR-08](./requirements.md#기능-요구사항) | DES-10 | AC-04 | 실기 |
| [FR-09](./requirements.md#기능-요구사항) | DES-01, DES-10 | AC-07 | 단위 + 실기 |
| [FR-10](./requirements.md#기능-요구사항) | DES-09 | AC-06 | 단위 |
| [NFR-01](./requirements.md#비기능-요구사항) | 실패 흐름 표 | AC-04 | 실기 |
| [NFR-02](./requirements.md#비기능-요구사항) | DES-03·DES-04(`wait_stable`, 마커) | AC-01 | 실기 |
| [NFR-03](./requirements.md#비기능-요구사항) | DES-09 `crop_path` | AC-06 | 단위 |
| [NFR-04](./requirements.md#비기능-요구사항) | DES-10 초기화 검사 | — | 단위 |
| [NFR-05](./requirements.md#비기능-요구사항) | DES-01 | — | 실기 |

작업(TASK)·검증(VER) 열은 wf-implement 계획 수립 시 추가한다.

## 승인 기록

- 승인 대상: 본 설계 v1, [요구사항 v1](./requirements.md), [ADR-001](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md), [ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md)
- 결과: **승인**
- 결정자: 사용자 / 결정 일시: 2026-09-28
- 근거: 대화형 승인 관문 응답 "승인"
- 효력: 기준선 v1 발행, wf-implement 인계 가능

## 변경 이력

| 날짜 | 변경 | 근거 | 상태 또는 기준선 | 작성자·승인자 |
|---|---|---|---|---|
| 2026-09-28 | 최초 초안 — P-01 실기 실측(좌표·행 기하·스크롤 특성), ADR-001·002 반영 | 사용자 결정 Q-01~Q-04, P-01/P-02 | draft | Claude(wf-design) |
| 2026-09-28 | A-07 사실 전환(목록 끝 600위·휠 무효), 링크 검사 통과, 승인 요청 | P-01 버스트 52~60 | draft → awaiting-approval | Claude(wf-design) |
| 2026-09-28 | 기준선 v1 발행 | 사용자 승인 응답 | awaiting-approval → approved, v1 | 사용자 승인 / Claude 기록 |

## 인계

- 다음 단계 또는 워크플로우: wf-implement(계획 수립 → 구현 → 검증 → 통합 → 완료 보고).
- 시작 조건: 승인된 기준선 v1(본 설계·[요구사항](./requirements.md))과 승인된 [ADR-001](./work/20260928-contrib-ranking-capture/ADR-001-recognition-strategy.md)·[ADR-002](./work/20260928-contrib-ranking-capture/ADR-002-rank-assignment.md) — 충족.
- 입력 문서와 기준선: 요구사항 v1, 설계 v1, ADR-001·002(approved), [결정 등록부](./decisions.md), 인수 조건 AC-01~08, 위험 RISK-01~09, 픽스처 [img/README.md](../img/README.md).
- 완료된 항목: wf-design 전 절차(조사, 사용자 결정 Q-01~Q-04, P-01·P-02 프로토타입, 문서 작성, 링크 검사, 승인).
- 미완료 항목: 구현 전부(구현 계획 `docs/plan.md`는 wf-implement가 생성).
- 차단 요인: 없음.
- 다음 행동: wf-implement 시작 조건 확인 후 `docs/plan.md` 작성(TASK 분해), 작업 기록 `docs/work/20260928-contrib-ranking-capture/work-log.md` 개시.
- 실기 환경 메모: 게임 클라이언트는 공헌 랭킹 화면 600위 끝에 머물러 있다(복귀 수동). 승격 러너(sgz_statiz `agent_shell`, pid 28052)는 유휴 300분 후 자동 종료된다.
