# 템플릿 자산 대장

> 문서 유형: `reference`
> 작업 ID: `20260928-contrib-ranking-capture`
> 작성일: 2026-09-28
> 최종 갱신: 2026-09-28
> 관련 문서: [DESIGN-sgz-rankscan: 설계 DES-02](../../docs/design.md#des-02-상세), [PLAN-sgz-rankscan: 구현 계획](../../docs/plan.md)

파일 ↔ 의미 ↔ 원본(픽스처·크롭 사각형) ↔ 등록일을 유지한다(sgz_statiz 규약).
크롭 사각형은 **클라이언트 픽셀 좌표**(2544×657)이며 코드 상수와 같은 값이다
([ui_ranking.py](../../src/rankscan/nav/ui_ranking.py)). 픽스처(창 2546×689)에서
잘라낼 때는 (x+1, y+31) 오프셋을 더한다([img/README.md](../../img/README.md)).

## ui/ — 화면 판정 마커 (RankingNavigator, TASK-02)

교차 NCC 실측(2026-09-28, `tests/test_ranking_nav.py` 픽스처 4장 + 합성 비활성 탭):
자기 화면 1.000, 타 화면 최대 0.350(공헌 탭 마커 ↔ 합성 비활성 탭) → 임계 0.8.

| 파일 | 의미 | 원본 | 등록일 |
|---|---|---|---|
| main_more.png | 메인 화면 하단 '더 보기' 버튼(메인 판정+클릭 목표. 메뉴 열림 중에도 보임 — 메뉴 마커를 먼저 판정) | sgz_statiz assets/templates/ui/main_more.png 복사(원본 실기 snap_012159, 2026-08-09). 상자 (1404, 618, 1460, 644) | 2026-09-28 |
| menu_ranking.png | 더 보기 메뉴의 '랭킹' 버튼 내부(메뉴 열림 판정+클릭 목표). sgz_statiz의 menu_alliance.png는 P-01 메뉴에서 0.47(메뉴 배치 변경)이라 대체 | img/p01_menu.png (1190, 568, 1278, 596) | 2026-09-28 |
| ranking_title.png | 랭킹 화면 좌상단 제목 '랭킹' | img/p01_contrib_top.png (18, 11, 68, 43) | 2026-09-28 |
| contrib_tab_on.png | 공헌 랭킹 탭 활성(주황 브래킷 포함 탭 전체) | img/p01_contrib_top.png (1298, 117, 1460, 160) | 2026-09-28 |

## digits_rank/ — 순위 숫자 글리프 (RankDigitReader, TASK-04)

TASK-04에서 수확·등록한다(흰색 0~9, 금색 1~3).

## user/ · region/ · alliance/ — 식별 템플릿 (IdentityMatcher, 실행 시 자동 생성)

`scan` 실행 중 미등록 세력명·지역·동맹 셀이 등장하면 IdentityMatcher가 크롭을
자동 저장하고 DB `identity_templates`에 등록한다(FR-05). 파일명
`<ns>_<순번>.png`. 이 대장에는 개별 파일을 나열하지 않는다 — 원장은 DB가
소유하며 라벨은 `label` 명령으로 확정한다.

이 세 디렉터리는 **런타임 레지스트리**(DB와 수명 동기)로 git에 커밋하지
않는다(.gitignore). DB(`output/rankscan.db`)를 초기화할 때는 이 디렉터리도
함께 비워야 식별자 번호와 파일이 어긋나지 않는다.
