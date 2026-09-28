# WORK-20260928-contrib-ranking-capture: 공헌 랭킹 캡처·추출 작업 기록

> 문서 유형: `work-log`
> 작업 ID: `20260928-contrib-ranking-capture`
> 상태: `in-progress`
> 기준선: `v1` (승인일 2026-09-28)
> 작성일: 2026-09-28
> 최종 갱신: 2026-09-28
> 관련 문서: [PLAN-sgz-rankscan: 구현 계획](../../plan.md), [DESIGN-sgz-rankscan: 설계](../../design.md), [REQ-sgz-rankscan: 요구사항](../../requirements.md)

## 요약

- 목적: 기준선 v1 구현의 수행 내역·결정·검증·재개 지점을 기록한다.
- 현재 결론 또는 상태: TASK-01~04 완료(2026-09-28 22:58 — 단위 테스트 29건 통과, 실기 probe 스냅샷 확보, 마커 4종 교차 NCC 분리, 행 검출·이동량·순위 배정을 픽스처 8장으로 검증, 순위 셀 33개 정확 판독). 세션 인계 지점(컨텍스트 임계 초과), TASK-05 미착수.
- 다음 행동: TASK-05 착수 — 아래 재개 지점 참조.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [PLAN-sgz-rankscan: 구현 계획](../../plan.md) | TASK-01~09 | 이 기록이 따르는 계획 |
| input | baseline | [DESIGN-sgz-rankscan: 설계](../../design.md) | DES-01~10 | 승인 기준선 v1 |
| input | baseline | [REQ-sgz-rankscan: 요구사항](../../requirements.md) | FR-01~10, AC-01~08 | 승인 기준선 v1 |
| input | decision | [ADR-001: 인식 전략](./ADR-001-recognition-strategy.md), [ADR-002: 순위 확정 전략](./ADR-002-rank-assignment.md) | ADR-001, ADR-002 | approved |

## 기준선과 현재 계획

- 기준선 v1(2026-09-28 승인): [요구사항](../../requirements.md) · [설계](../../design.md) · ADR-001·002.
- 계획: [plan.md](../../plan.md) TASK-01~09, 계획 트리 사용. DCR 없음.

## 현재 상태

- 진행 중인 작업: 없음(TASK-05 착수 전, 세션 인계)
- 마지막 완료 작업: TASK-04(2026-09-28 22:58)
- 차단 요인: 없음

## 수행 기록

### 2026-09-28 — 계획 수립

- 수행 내용: wf-implement 3.1 재확인(기준선 직후, 저장소 변경 없음, Python 3.13.1, 의존성은 sgz_statiz venv에서 설치 실적) → [plan.md](../../plan.md) 작성(TASK-01~09, 계획 트리).
- 변경 파일: `docs/plan.md`, 본 문서.
- 발견 사항: 설계 단계 P-01 스냅샷을 `img/`에 선별 보존해 두어(색인 [img/README.md](../../../img/README.md)) TASK-02·03·04·06의 픽스처가 이미 확보됨. 순위 셀 좌표 등 미세 상수는 픽스처로 실측하며 확정.
- 결정과 이유: 테스트 체계는 `unittest`(sgz_statiz와 동일, 새 의존성 없음). 이식은 파일 복사 + 출처 주석(설계 대안과 결정). `probe`를 TASK-01에 포함 — 이후 작업의 실기 스냅샷 확보 수단이 먼저 필요하기 때문.
- 실행한 검증: 없음(문서 작업).
- 결과: 계획 `in-progress`, 구현 미착수.

### 2026-09-28 — TASK-01 프로젝트 골격·플랫폼 계층 이식·probe

- 수행 내용: TDD — `tests/test_smoke.py`(3건: 패키지·win 계층 임포트, `find_client_windows()` list 반환)와 `tests/test_controller.py`(6건: sgz_statiz ChooseWindowTest 이식)를 먼저 작성 → `.venv` 생성 후 실행하여 Red 확인(errors=4, 전부 `ModuleNotFoundError: No module named 'rankscan'`) → 골격 작성, win/ 4모듈 복사, `pip install -e .` → Green(9건 OK). 후행: `rankscan --help`에 probe 노출, `rankscan probe`(비승격, 캡처만)로 실기 스냅샷 생성.
- 변경 파일: `pyproject.toml`, `.gitignore`, `.gitattributes`, `src/rankscan/{__init__,cli,controller}.py`, `src/rankscan/win/{__init__,win32,capture,input,session}.py`, `src/rankscan/nav/{__init__,ui_ranking}.py`, `tools/agent_shell.ps1`, `tools/agent_shell_admin.bat`, `tests/test_smoke.py`, `tests/test_controller.py`. 커밋 제외: `.venv/`, `output/probe/`.
- 발견 사항:
  - 사실: 의존성 네트워크 설치 성공 — numpy 2.5.3, opencv-python 5.0.0.93, pillow 12.3.0, windows-capture 2.0.1(sgz_statiz는 2.0.0), winocr 0.0.15. 버전 고정 불필요(계획 위험 미발생).
  - 사실: 실기 probe — hwnd 0x206be, pid 21456, elevated=True, client 2544×657, 프레임 2546×689. 증거 `output/probe/snap_215850_probe.png`.
  - 사실: 현재 게임 화면은 공헌 랭킹이 아니라 **장수 상세(여포) 화면** — 이전 세션 메모(600위 끝 화면)와 다르다. A-01(메인 또는 랭킹 화면)을 충족하지 않으므로 TASK-08 실기 검증 전에 사용자가 메인 화면으로 복귀시켜야 한다(도구는 화이트리스트 밖 클릭을 하지 않는다).
  - 사실: 계획 트리의 설계 단계 완료 시점 `22:05`는 실제 시각 순서(계획 수립 21:52 이전)와 맞지 않는 이전 세션 표기. 승인 효력과 무관하므로 수정하지 않는다.
- 결정과 이유:
  - 결정: probe `--wheel N`(설계 DES-10 CLI 계약)의 휠 지점을 위해 `nav/ui_ranking.py`를 `SCROLL_POINT`만 담아 미리 생성 — 계획 TASK-03 비고("상수 모듈이 없으면 먼저 둔다")를 준용. 나머지 상수는 TASK-02·03에서 채운다(경미한 변경, 계획 TASK-01 변경 대상에 병기).
  - 결정: win/ 4모듈은 바이트 복사하되 UTF-8 BOM만 제거하고 출처 주석 1행을 앞에 붙였다(코드 본문 무수정, 원본의 map_search 출처 주석 유지).
  - 결정: `controller.py`는 `choose_window`·`_select`만 이식(run_scan·label_pending·summarize_run은 TASK-07). `test_controller.py`는 계획의 4 시나리오에 sgz_statiz의 재확인 거부·잘못된 입력 2건을 더해 6건 이식(AC 의미 불변).
- 실행한 검증: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — Red `Ran 4 tests, FAILED (errors=4)` → Green `Ran 9 tests, OK`. `.venv\Scripts\rankscan.exe --help` exit 0(probe 노출). `.venv\Scripts\rankscan.exe probe` exit 0, 스냅샷 1장.
- 결과: TASK-01 completed(2026-09-28 21:59). 완료 조건(unittest 통과, probe 스냅샷 생성) 충족.

### 2026-09-28 — TASK-02 화면 판정·이동 (nav)

- 수행 내용: 조사 — 픽스처 4장(`p01_main`, `p01_menu`, `p01_contrib_top`, `ranking_1`)에서 마커 후보 영역을 확대 크롭·밝은 픽셀 bbox로 실측하고 sgz_statiz 마커 2종의 클라이언트 상자를 환산해 교차 NCC를 측정. TDD — `tests/test_ranking_nav.py`(마커 4종 × 프레임 6장 교차 판별 1건, `goto_contrib_tab` 플로우 6건)를 먼저 작성 → Red(`ModuleNotFoundError: rankscan.nav.navigator`) → `navigator.py` 이식(+`ui_template`), `ui_ranking.py` 이동·마커 상수, `ranking.py`(`RankingNavigator`), 템플릿 3종 수확 → Green(16건 OK).
- 변경 파일: `src/rankscan/nav/{navigator,ranking,ui_ranking}.py`, `assets/templates/ui/{main_more,menu_ranking,ranking_title,contrib_tab_on}.png`, `assets/templates/README.md`, `tests/test_ranking_nav.py`.
- 발견 사항:
  - 사실: `main_more.png`(sgz_statiz)는 P-01 메인·메뉴에서 1.000, 랭킹 화면 0.061 — 재사용 가능. 상자는 표시 좌표 `_box(1104,510,1148,530)` → 클라이언트 (1404, 618, 1460, 644).
  - 사실: `menu_alliance.png`(sgz_statiz)는 P-01 메뉴에서 **0.470**으로 임계 미달 — 더 보기 메뉴가 3×3 격자(국가·행낭·시련 / 패업·랭킹·시스템 / 장수·전법·정청)로 8월과 배치가 다르다. 하단 행 장수·전법·정청은 메뉴가 닫혀도 보인다.
  - 사실: 제목 `랭킹` 밝은 픽셀 bbox는 클라이언트 x 22~64, y 15~39 — 설계 추정(y 28~56)보다 위. 공헌 탭 주황 브래킷 bbox x 1300~1457, y 119~157 — 설계 추정과 일치.
  - 사실: 교차 NCC(마커 4종 × 픽스처 4장 + 합성 비활성 탭 + 검은 프레임): 자기 화면 1.000, 타 화면 최대 0.350(공헌 탭 마커 ↔ 합성 비활성 탭). `p01_contrib_top`과 `ranking_1`은 마커 영역이 픽셀 동일.
  - 해석: 랭킹 화면에서 다른 탭이 활성인 실기 픽스처가 없어 합성 프레임(활성 탭 상자에 좌측 비활성 탭 띠 복사)으로 플로우를 검증했다. 실제 비활성 공헌 탭의 점수는 TASK-08에서 확인한다.
- 결정과 이유:
  - 결정: 메뉴 마커를 `menu_ranking.png`(`p01_menu` 랭킹 버튼 내부 (1190, 568, 1278, 596))로 신규 수확 — 설계 DES-02의 "재사용"은 실측으로 기각(DES-02가 "구현 시 스냅샷에서 수확·NCC 교차 측정"을 허용하므로 경미한 변경).
  - 결정: `goto_contrib_tab`은 이미 도달한 지점(공헌 탭 활성 > 랭킹 화면 > 메뉴 열림 > 메인)부터 이어서 진행한다. 랭킹 화면에서 다른 탭이 활성이면 탭 클릭만 수행 — DES-03의 "각 단계 직전 화면 재검증" 체인의 자연스러운 시작점 선택이며 FR-01 생략 규칙을 포함한다.
  - 결정: `ui_template()`·`UI_DIR`는 `navigator.py`에 둔다(sgz_statiz는 list_walker.py — rankscan에 없음).
  - 결정: sgz_statiz의 `menu_alliance.png`는 복사했다가 미사용으로 삭제.
- 실행한 검증: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — Red `Ran 10 tests, FAILED (errors=1)`(임포트 실패) → Green `Ran 16 tests, OK`(1.2s). 실기 이동은 미수행(TASK-08 AC-01).
- 결과: TASK-02 completed(2026-09-28 22:08). 완료 조건(테스트 통과) 충족.

### 2026-09-28 — TASK-03 행 검출·이동량 측정·순위 이어붙임

- 수행 내용: 조사 — 픽스처 8장의 `ROW_LINE_COL`(x 1140~1160) 열 밝기 프로파일과 확대 크롭을 실측하고, 행 상단 검출 규칙 후보 2종과 anchor 띠 후보 5종을 전 픽스처에서 수치 비교. TDD — `tests/test_list_geometry.py`(행 검출 5건, 이동량 3건, 순위 배정 3건)를 먼저 작성 → Red → `ui_ranking.py`에 목록 기하·스크롤 상수 추가, `nav/list_scroller.py`(`detect_row_tops`, `anchor_band`, `measure_shift`, `assign_ranks`) 작성 → Green.
- 변경 파일: `src/rankscan/nav/{list_scroller,ui_ranking}.py`, `tests/test_list_geometry.py`, `img/README.md`(w11 순위 정정), `docs/plan.md`(TASK-03 상태·차이, TASK-04 수확 출처).
- 발견 사항:
  - 사실: 행은 어두운 갈색 카드 + 상·하단 1px 밝은 테두리선(행 높이 65, 간격 71.2). 카드 사이 6~7px 간격에는 패널 배경(반투명 월드맵)이 보여 밝기가 40~101로 위치마다 다르다 → 절대 밝기 임계로는 선을 가를 수 없다.
  - 사실: 빈 열 프로파일에서 "국소 최대 − 아래 행 내부(+2~+8px) 최대"의 대비는 상단선 22~56, 행 내부 잡음 < 4, 하단선 9~20이며 하단선→상단선 간격은 6~7px. 이 규칙의 검출값은 contrib_top 203·275·346·417·488·559, end 202·273·344·415·486·558(계획 기대값과 정확히 일치), w1 242·313·384·455·527(598은 하단 잘림 제외), 나머지 픽스처도 71±1 간격.
  - 사실: 상단선이 부화소 렌더링으로 2px에 걸치는 행(contrib_top 6위 559/560, w1 6위 526/527)은 더 밝은 픽셀이 잡혀 프레임 간 ±1px 차이가 난다(w1 6위 527 vs 33px 이동 기대값 526). 순위 배정 `round()`가 흡수한다.
  - 사실: anchor 띠 NCC(이름 열 `CELL_NAME` 30px): 같은 행 0.976~0.982(contrib_top→w1, w1→w2 이동량 모두 정확히 33), 다른 행 ≤ 0.42, 겹침 상실 b10→b11 ≤ 0.34. 행 전폭 30px 띠는 지역·동맹 열이 행마다 같아 다른 행이 0.64~0.77 → 임계 0.8과 여유 없음.
  - 사실: 순위 셀 몽타주로 픽스처 순위를 확인 — w2 2~7, **w11 5~9(README의 "4~9"는 오기, 10위는 하단 잘림)**, b10 121~125, b11 132~136, end 595~600. README와 계획 TASK-04 수확 출처를 정정.
  - 사실: 게임 클라이언트·승격 러너는 이 작업에서 사용하지 않았다(상태 미확인).
- 결정과 이유:
  - 결정: 행 상단 규칙 = 국소 최대 + 대비 ≥ `ROW_LINE_MIN_CONTRAST`(10) + `ROW_LINE_PAIR_MAX`(9px) 안에 다음 후보가 따라오면 하단선으로 제거 + 행 전체가 `LIST_REGION` 안인 것만 채택. 기각: 1D 임펄스 NCC 템플릿 — NCC가 진폭을 정규화해 행 내부의 ±1 잡음이 0.8~0.98로 잡힘(거짓 양성 다수).
  - 결정: anchor 띠는 DES-04 6의 "행 전폭"이 아니라 `CELL_NAME` x 범위(220px)만 사용(위 실측). 캘리브레이션 수준.
  - 결정: `visible_rows`를 별도 함수로 두지 않고 `detect_row_tops`가 완전 가시 행만 반환 — DES-04는 완전 가시 행만 쓴다(YAGNI). 부분 행의 상단선은 검출되어도 반환하지 않는다.
  - 결정: 순수 함수의 입력은 클라이언트 좌표계 프레임(캡처 프레임을 `crop_client(frame, (0, 0, 2544, 657))`로 자른 것). 변환 책임은 TASK-07 walk.
  - 결정: `measure_shift`는 임계 미달 `None`, 0(이동 없음)·음수(되감기)는 그대로 반환하고 범위 판정(0 < shift < `SHIFT_MAX`)은 호출자(TASK-07)가 한다 — 계획 검증 방법의 "임계 미달로 None"과 일치.
- 실행한 검증: `.venv\Scripts\python.exe -m unittest discover -s tests` — Red `Ran 17 tests, FAILED (errors=1)`(`ModuleNotFoundError: rankscan.nav.list_scroller`) → Green `Ran 27 tests, OK`(1.3s, 신규 11건).
- 결과: TASK-03 completed(2026-09-28 22:37). 완료 조건(테스트 통과) 충족.

### 2026-09-28 — TASK-04 순위 숫자 글리프 판독

- 수행 내용: 조사 — 픽스처 6장의 순위 셀 33개(`CELL_RANK`)를 몽타주로 확인하고 HSV 분포·연결 성분 클러스터·메달 셀 교차 NCC를 실측. TDD — `tests/test_rank_digits.py`(33셀 정확 판독 1건 + 빈 셀 `''` 1건)를 먼저 작성 → Red(`ModuleNotFoundError: rankscan.vision`) → `vision/digits.py` 이식(+메달 슬라이딩 NCC), `tools/harvest_digits.py` 작성·수확 → 1차 실행 7건 실패(아래 발견) → 마스크 명도 하한 130으로 조정·재수확 → Green → 변형 자동 추가 규칙으로 재수확 → Green 유지. 후행: 스크래치 스크립트로 전 셀 최고점·차점 여유 측정.
- 변경 파일: `src/rankscan/vision/{__init__,digits}.py`, `tools/harvest_digits.py`, `assets/templates/digits_rank/*.png`(18장), `assets/templates/README.md`(digits_rank 대장), `tests/test_rank_digits.py`, `docs/plan.md`(TASK-04 상태·차이·트리), 본 문서.
- 발견 사항:
  - 사실: 1~3위는 **금·은·동** 3색 메달 숫자다(설계 "금색 1~3"은 실제 3색). 동색 3은 명도 최대 123, 은색 2는 채도 ≈ 0 → 흰색용 HSV 마스크(V ≥ 170)로 3위는 픽셀 0개, 2위는 부분만 잡힌다. 메달 숫자는 흰색보다 크다(12×23·16×19·15×20 vs 9×13).
  - 사실: 메달 글리프 템플릿(`medal_N.png`, 회색조 bbox+여유 2px)을 셀 회색조에서 슬라이딩 NCC — 자기 1.000, 같은 메달 다른 프레임(w2) 0.946~0.951, 다른 메달·흰색 셀 33개 최대 0.690(`medal_1` ↔ 흰색 `1xx` 셀 0.60~0.69).
  - 사실: 흰색 숫자는 S ≈ 35, 획 중심 V ≥ 200, 셀 배경 V < 90(반투명 패널 포함). 글리프 폭 6~10(1은 6~7)·높이 13~14, 간격 2px. sgz_statiz 임계 V ≥ 170에서는 가는 가로 획(세리프·`4` 가로 막대·`1` 깃발)이 부화소 위치에 따라 110~175를 오가 상자가 흔들렸다(`1` 폭 4~6, `4` 폭 7~9, `6` 좌우 1px 분리 2건) → 1차 Green 시도 7건 실패(`1`이 비율 1.4 초과로 후보 제외 → `?`, `4` NCC 0.18). V ≥ 130에서는 상자가 안정(`1` 6~7, 나머지 8~10, 클러스터 수 불일치 0).
  - 사실: 변형 규칙(저장본 대비 NCC < 0.8 → `N_k.png`)으로 `1_2`·`3_2`·`3_3`·`7_2`·`9_2` 5장 추가. 최종 여유(33셀, 문자별 최대 점수): 정답 최고점 최소 0.816, 다른 문자 최대 0.764(`8`↔`3`), 최소 여유 0.155(변형 전 0.101). 메달 자기 최소 0.946 / 타 최대 0.690.
  - 해석: 템플릿과 테스트 픽스처가 같은 P-01 스냅샷이라 테스트는 판독 규칙의 자기 일관성을 보장할 뿐 실기 일반화는 TASK-08에서 확인한다(특히 메달 셀은 반투명 패널 뒤 월드맵 위치에 따라 점수가 내려갈 수 있다 — 여유 0.15).
  - 사실: 게임 클라이언트·승격 러너는 이 작업에서 사용하지 않았다(상태 미확인).
- 결정과 이유:
  - 결정: 메달 숫자는 색상별 HSV 마스크 3종 대신 회색조 슬라이딩 NCC(`_MEDAL_THRESHOLD` 0.8)로 판독한다 — 파라미터 1개, 메달 테두리 잡음 무관. 기각: 색상별 마스크 — 3색 파라미터 + 금색 테두리가 마스크에 섞여 `?` 클러스터 발생 위험.
  - 결정: 흰색 마스크 명도 하한 `_TEXT_MIN_VAL` 170 → 130(캘리브레이션, 위 실측). 채도 상한 90 유지.
  - 결정: 이식 시 `read_coords`·콤마/괄호 글리프·초소형 글리프·과폭 클러스터 분할 가설을 제거(순위 셀에서 관찰되지 않는 실패 모드, 인접 숫자 간격 2px로 맞닿음 없음). 병합 가설 복구는 유지하고 항상 적용(`6` 분리 관찰; 인접 숫자는 합쳐도 폭 ≥ 14 > 글리프 폭 + 1이라 오병합 없음). 클래스명은 설계 DES-08의 `RankDigitReader`, 진입점 `read_rank(cell) -> str`.
  - 결정: 판독 실패 어휘 — 미인식 글리프 `?`(설계), 글리프 없음 `''`. 둘 다 `str(rank)`와 불일치이므로 TASK-07 walk는 `?` 포함 또는 빈 문자열을 "판독 실패(검증 생략)"로, 그 외 불일치를 `rank_conflict`로 다룬다.
  - 결정: 수확 도구는 숫자별 첫 출현 저장 + 저장본 대비 NCC < 0.8 출현을 변형으로 자동 추가(`VARIANT_MIN_NCC`) — sgz_statiz의 `N_k` 변형 방식을 규칙화. 기각: 모든 출현 저장 — 중복 다수, 판독 비용 증가.
  - 결정: 테스트 픽스처를 계획의 4장에 `p01_w2`·`p01_b11_r132`를 더한 6장 33셀로 확대 — `6` 분리·변형 대상 셀을 포함하기 위함(AC 의미 불변, 테스트 보강).
- 실행한 검증: `.venv\Scripts\python.exe -m unittest discover -s tests` — Red `Ran 28 tests, FAILED (errors=1)`(`ModuleNotFoundError: No module named 'rankscan.vision'`) → 1차 Green 시도 `Ran 29 tests, FAILED (failures=7)`(V ≥ 170) → 임계 130 `Ran 29 tests, OK`(1.45s) → 변형 추가 후 `Ran 29 tests, OK`. `tools/harvest_digits.py` 실행 로그(변형 5건, 대장 행 18건). 실기 판독은 미수행(TASK-08).
- 결과: TASK-04 completed(2026-09-28 22:58). 완료 조건(테스트 통과, 글리프 대장 갱신) 충족.

## 설계와 달라진 점

- DES-02 `MARKER_MENU`: 설계는 sgz_statiz `menu_alliance.png` 재사용이었으나 P-01 메뉴에서 0.47(메뉴 배치 변경)이라 `menu_ranking.png`를 신규 수확했다. 마커 값은 DES-02가 구현 시 보정을 허용한 캘리브레이션 항목 — 경미한 변경, 설계 문서 수정 불필요(TASK-09에서 설계 DES-02 표의 근거 열 갱신 여부 검토).
- DES-02 `MARKER_RANKING` 상자: 설계 추정 y 28~56 → 실측 (18, 11, 68, 43). 캘리브레이션.
- DES-03 `goto_contrib_tab`: 설계는 "이미 공헌 탭이면 생략"만 명시. 구현은 랭킹 화면(다른 탭)·메뉴 열림에서도 그 지점부터 이어간다 — 체인 시작점 확장, 공개 계약(`goto_contrib_tab() -> ndarray`)·인수 조건 불변. 경미.
- TASK-01 `ui_ranking.py` 조기 생성(SCROLL_POINT) — 계획 차이, 위 수행 기록 참조.
- DES-04 6 anchor 띠: 설계는 "`CELL_NAME` 띠(행 전폭 × 30px)"이나 구현은 `CELL_NAME` x 범위(1180~1400)만 사용 — 행 전폭은 다른 행 NCC가 0.64~0.77까지 올라 임계 0.8과 여유가 없다(TASK-03 실측). 캘리브레이션, 계약 불변, 경미.
- DES-02 `ROW_LINE_COL` 규칙: 설계는 "밝기 피크 5~9px 쌍의 둘째가 행 상단"만 명시. 구현은 쌍 규칙 앞에 "선 − 아래 행 내부 대비 ≥ 10" 후보 조건을 더했다(카드 사이 배경 밝기 변동 때문). 경미.
- 계획 TASK-03 `visible_rows` 미생성 — `detect_row_tops`에 합침. 경미(계획 세부).
- DES-08 "금색 1~3": 실제는 금·은·동 3색 메달 숫자. 구현은 색 마스크 대신 메달 글리프 템플릿(`medal_N.png`)의 회색조 슬라이딩 NCC(임계 0.8)로 판독한다. 계약(순위 셀 → 문자열, 실패 `?`)·책임 불변 — 경미(내부 세부·캘리브레이션). TASK-09에서 설계 DES-08·ADR-002 3의 "금색" 표현 갱신 여부 검토.
- DES-08 이식 축소·보정: sgz_statiz `digits.py`의 좌표 파싱·콤마/괄호·초소형 글리프·과폭 분할 가설 제거, 흰색 마스크 명도 하한 170 → 130, 병합 복구 항상 적용(TASK-04 실측). 경미.
- 계획 TASK-04 검증 방법: 픽스처 4장 → 6장 33셀(`p01_w2`·`p01_b11_r132` 추가). 테스트 보강, AC 의미 불변. 변경 대상에 `src/rankscan/vision/__init__.py`·변형 자동 추가 규칙 추가.

## 미완료 항목

- TASK-05~09(계획 참조). TASK-05는 TASK-01에만 의존, TASK-06은 04(완료)·05에 의존.

## 재개 지점

- 다음 작업: TASK-05 DataStore·CsvExport — 순수 로컬, 오프라인으로 완료 가능([계획 TASK-05](../../plan.md#task-05-datastorecsvexport), [설계 DES-09](../../design.md#컴포넌트와-책임)와 [SQLite 스키마](../../design.md#데이터와-인터페이스) — `runs`·`identities`·`identity_templates`·`rank_rows`, CSV 열·`#id(제안)` 표기·UTF-8 BOM은 같은 절의 "파일 산출물").
- 먼저 확인할 사항: (1) `src/rankscan/store/`가 없는지(없으면 미착수), `tests/test_datastore.py`·`tests/test_csv_export.py`가 있으면 Red 단계 진행 중, (2) 이식 원천 `C:\src\git\sgz_statiz\src\deckscan\store\datastore.py`(WAL, run 기록, `INSERT OR REPLACE` 멱등 골격)·`csv_export.py`·`tests/test_datastore.py`(csv_export 테스트는 sgz_statiz에 없음), (3) 계획 검증 방법: run 생성·마감(status/note), `upsert_row` 같은 `(run, rank)` 재저장 시 1건·다른 run 별도 보존, identities pending → confirm 조회 반영, CSV 열 순서·`#id(제안)`·BOM.
- 필요한 명령 또는 파일: 테스트 `.venv\Scripts\python.exe -m unittest discover -s tests`(현재 29건 OK). TASK-06이 쓸 순위 판독 진입점은 `rankscan.vision.digits.RankDigitReader().read_rank(cell)`(셀 = 클라이언트 프레임 `CELL_RANK` 크롭, 실패 `?`/`''`).

## 인계

- 다음 단계 또는 워크플로우: wf-implement 계속 — 재개 절차: 본 문서의 재개 지점 → 계획의 해당 TASK → TDD 사이클.
- 시작 조건: 충족(기준선 v1).
- 입력 문서와 기준선: [계획](../../plan.md), [설계](../../design.md), [요구사항](../../requirements.md), [ADR-001](./ADR-001-recognition-strategy.md), [ADR-002](./ADR-002-rank-assignment.md).
- 완료된 항목: wf-design 전체, 계획 수립, TASK-01(2026-09-28 21:59), TASK-02(2026-09-28 22:08), TASK-03(2026-09-28 22:37), TASK-04(2026-09-28 22:58).
- 미완료 항목: TASK-05~09.
- 차단 요인: 없음.
- 다음 행동: TASK-05 착수 — 계획 TASK-05를 `in-progress`로 바꾸고(트리 재생성), sgz_statiz `tests/test_datastore.py`를 참고해 `tests/test_datastore.py`·`tests/test_csv_export.py`를 먼저 작성(위 재개 지점의 검증 방법)해 Red를 확인한 뒤, `src/rankscan/store/datastore.py`(sgz_statiz 골격 이식 + 설계 DES-09 스키마로 교체)·`src/rankscan/store/csv_export.py` 이식으로 Green. 이식 파일 머리에 출처·복사일·변경점 주석을 남긴다.
- 재개 프롬프트: 작업 20260928-contrib-ranking-capture 재개 — docs/work/20260928-contrib-ranking-capture/work-log.md의 인계 절을 읽고 "다음 행동"부터 진행하라.
- 실기 환경 메모: 클라이언트 창 0x206be(pid 21456, 클라이언트 2544×657, 관리자 권한). 현재 화면은 **장수 상세(여포)** — 랭킹도 메인도 아니므로 TASK-08 전 사용자 복귀 필요. 승격 러너 pid 28052(2026-09-28 21:25 기동, cwd sgz_statiz, 유휴 300분 후 자동 종료 — 마지막 명령 21:39이므로 2026-09-29 02:39경 종료 예상; 이 세션에서는 사용하지 않음). 명령 투입 프로토콜은 `sgz_statiz/tools/agent_shell.ps1` 머리 주석 참조(다음 번호 `cmd_0016.txt`; rankscan 실행은 명령 안에서 `Set-Location C:\src\git\sgz_rankscan` 후 `.venv\Scripts\rankscan.exe`).
- 저장소: 원격 https://github.com/bluesky5008/sgz_rankscan — 2026-09-28 사용자 요청으로 최초 커밋·push(TASK-01·02 완료 시점). 이후 커밋·push도 사용자 요청 시에만 수행한다. TASK-03·04 변경분은 2026-09-28 사용자 요청으로 커밋 `53344df`·push 완료(main = origin/main). 이 메모 갱신만 후속 커밋.
