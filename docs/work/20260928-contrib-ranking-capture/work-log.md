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
- 현재 결론 또는 상태: TASK-01·02 완료(2026-09-28 22:08 — 단위 테스트 16건 통과, 실기 probe 스냅샷 확보, 마커 4종 교차 NCC 분리 확인). 세션 인계 지점(컨텍스트 임계 초과), TASK-03 미착수.
- 다음 행동: TASK-03 착수 — 아래 재개 지점 참조.

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

- 진행 중인 작업: 없음(TASK-03 착수 전, 세션 인계)
- 마지막 완료 작업: TASK-02(2026-09-28 22:08)
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

## 설계와 달라진 점

- DES-02 `MARKER_MENU`: 설계는 sgz_statiz `menu_alliance.png` 재사용이었으나 P-01 메뉴에서 0.47(메뉴 배치 변경)이라 `menu_ranking.png`를 신규 수확했다. 마커 값은 DES-02가 구현 시 보정을 허용한 캘리브레이션 항목 — 경미한 변경, 설계 문서 수정 불필요(TASK-09에서 설계 DES-02 표의 근거 열 갱신 여부 검토).
- DES-02 `MARKER_RANKING` 상자: 설계 추정 y 28~56 → 실측 (18, 11, 68, 43). 캘리브레이션.
- DES-03 `goto_contrib_tab`: 설계는 "이미 공헌 탭이면 생략"만 명시. 구현은 랭킹 화면(다른 탭)·메뉴 열림에서도 그 지점부터 이어간다 — 체인 시작점 확장, 공개 계약(`goto_contrib_tab() -> ndarray`)·인수 조건 불변. 경미.
- TASK-01 `ui_ranking.py` 조기 생성(SCROLL_POINT) — 계획 차이, 위 수행 기록 참조.

## 미완료 항목

- TASK-03~09(계획 참조). TASK-03·04·05는 서로 독립(모두 TASK-01에만 의존).

## 재개 지점

- 다음 작업: TASK-03 행 검출·이동량 측정·순위 이어붙임 — 순수 함수, 오프라인 픽스처만으로 완료 가능([계획 TASK-03](../../plan.md#task-03-행-검출이동량-측정순위-이어붙임), [ADR-002](./ADR-002-rank-assignment.md) 결정 1·2·6, [설계 DES-04 상세](../../design.md#des-04-상세) 2·3·6).
- 먼저 확인할 사항: (1) `src/rankscan/nav/list_scroller.py`가 없는지(없으면 코드 미착수), `tests/test_list_geometry.py`가 있으면 Red 단계 진행 중, (2) `ui_ranking.py`에 목록 기하 상수(`LIST_REGION`, `ROW_PITCH`, `ROW_HEIGHT`, `ROW_LINE_COL`, `CELL_*`, `SHIFT_MAX`, `ANCHOR_NCC_THRESHOLD`, `SCROLL_NOTCHES`)가 아직 없음 — TASK-03에서 설계 DES-02 값으로 추가하고 픽스처로 재확인, (3) 게임 클라이언트·승격 러너 상태는 TASK-08 전까지 무관(아래 실기 환경 메모).
- 필요한 명령 또는 파일: 픽스처 `img/p01_contrib_top.png`(완전 가시 6행 상단 203, 275, 346, 417, 488, 559 기대), `p01_w1.png`(5행, 598 행은 하단 잘림 제외), `p01_w2.png`, `p01_end_r595_600.png`(6행 202…558), `p01_b10_r121.png`·`p01_b11_r132.png`(겹침 상실 → `measure_shift` None); 기대값의 정본은 계획 TASK-03 검증 방법. 픽스처 크롭은 `navigator.ScreenJudge.crop_client` 또는 오프셋 (x+1, y+31); `navigator.same_image`가 이미 있다. 테스트 `.venv\Scripts\python.exe -m unittest discover -s tests`(현재 16건 OK).

## 인계

- 다음 단계 또는 워크플로우: wf-implement 계속 — 재개 절차: 본 문서의 재개 지점 → 계획 TASK-01 → TDD 사이클.
- 시작 조건: 충족(기준선 v1).
- 입력 문서와 기준선: [계획](../../plan.md), [설계](../../design.md), [요구사항](../../requirements.md), [ADR-001](./ADR-001-recognition-strategy.md), [ADR-002](./ADR-002-rank-assignment.md).
- 완료된 항목: wf-design 전체, 계획 수립, TASK-01(2026-09-28 21:59), TASK-02(2026-09-28 22:08).
- 미완료 항목: TASK-03~09.
- 차단 요인: 없음.
- 다음 행동: TASK-03 착수 — 계획 TASK-03을 `in-progress`로 바꾸고(트리 재생성), `tests/test_list_geometry.py`를 먼저 작성(픽스처 3종 행 상단 검출, `measure_shift` w1→w2 = 33·b10→b11 = None, `assign_ranks`)해 Red를 확인한 뒤 `ui_ranking.py`에 목록 기하 상수 추가·`nav/list_scroller.py` 순수 함수(`detect_row_tops`, `visible_rows`, `measure_shift`, `assign_ranks`, `anchor_band`)로 Green. 행 테두리 밝기 피크 규칙(DES-02 `ROW_LINE_COL`: x 1140~1160, 5~9px 간격 쌍의 둘째가 행 상단)은 픽스처 열 프로파일을 먼저 실측해 정한다.
- 재개 프롬프트: 작업 20260928-contrib-ranking-capture 재개 — docs/work/20260928-contrib-ranking-capture/work-log.md의 인계 절을 읽고 "다음 행동"부터 진행하라.
- 실기 환경 메모: 클라이언트 창 0x206be(pid 21456, 클라이언트 2544×657, 관리자 권한). 현재 화면은 **장수 상세(여포)** — 랭킹도 메인도 아니므로 TASK-08 전 사용자 복귀 필요. 승격 러너 pid 28052(2026-09-28 21:25 기동, cwd sgz_statiz, 유휴 300분 후 자동 종료 — 마지막 명령 21:39이므로 2026-09-29 02:39경 종료 예상; 이 세션에서는 사용하지 않음). 명령 투입 프로토콜은 `sgz_statiz/tools/agent_shell.ps1` 머리 주석 참조(다음 번호 `cmd_0016.txt`; rankscan 실행은 명령 안에서 `Set-Location C:\src\git\sgz_rankscan` 후 `.venv\Scripts\rankscan.exe`).
- 저장소: 원격 https://github.com/bluesky5008/sgz_rankscan — 2026-09-28 사용자 요청으로 최초 커밋·push(TASK-01·02 완료 시점). 이후 커밋·push도 사용자 요청 시에만 수행한다.
