"""공헌 랭킹 화면 좌표·마커·기하 상수 — 유일한 캘리브레이션 지점 (설계 DES-02).

좌표계: 클라이언트 픽셀(2544×657 전제, NFR-04). 캡처 프레임(창 2546×689)에서
클라이언트 (0,0)은 (1, 31)이며 변환은 navigator.frame_client_offset()이 한다.
값은 P-01(2026-09-28 실기, 창 0x206be) 스냅샷 선별본(img/p01_*.png) 실측이다.
목록 기하(LIST_REGION, ROW_PITCH/HEIGHT, ROW_LINE_COL, CELL_*, SCROLL_NOTCHES,
SHIFT_MAX, ANCHOR_NCC_THRESHOLD)는 TASK-03에서 추가한다.
"""

# -- 화면 이동 클릭 좌표 (DES-02·DES-03). P-01 실기 클릭으로 목표 화면 도달 확인.
CLICK_MORE = (1432, 631)          # 메인 하단 바 '더 보기' (sgz_statiz 검증 좌표 재사용)
CLICK_MENU_RANKING = (1235, 585)  # 더 보기 메뉴의 '랭킹' (버튼 약 x 1182~1285, y 562~602)
CLICK_CONTRIB_TAB = (1378, 138)   # 랭킹 화면 '공헌 랭킹' 탭
CLICK_RETURN = (2499, 24)         # 우상단 '귀환' — 화면 이탈 복구용 (sgz_statiz 동일)

# -- 화면 판정 마커 — (assets/templates/ui/ 파일명, 기대 위치 상자).
# 2026-09-28 픽스처 4장 + 합성 비활성 탭 교차 NCC: 자기 화면 1.000, 타 화면 최대
# 0.350 (tests/test_ranking_nav.py, 자산 대장 assets/templates/README.md).
# 주의: MARKER_MAIN(더 보기 버튼)은 메뉴 열림 상태에서도 보인다 — 메뉴 열림을
# MARKER_MENU로 먼저 판정한다(재클릭 시 메뉴 토글 닫힘 방지, sgz_statiz 동일).
MARKER_MAIN = ("main_more.png", (1404, 618, 1460, 644))          # sgz_statiz 템플릿 재사용
MARKER_MENU = ("menu_ranking.png", (1190, 568, 1278, 596))       # '랭킹' 버튼 내부. 설계의
#   menu_alliance.png 재사용은 P-01 메뉴에서 0.47(메뉴 배치 변경)이라 기각 → 신규 수확
MARKER_RANKING = ("ranking_title.png", (18, 11, 68, 43))         # 좌상단 제목 '랭킹'
#   (밝은 픽셀 bbox x 22~64, y 15~39 + 여유 4px — 설계 추정 y 28~56보다 위)
MARKER_CONTRIB_TAB = ("contrib_tab_on.png", (1298, 117, 1460, 160))  # 활성 탭 주황 브래킷
#   전체(bbox x 1300~1457, y 119~157) — 텍스트만으로는 비활성과 미구분(sgz_statiz 경험)
MARKER_NCC_THRESHOLD = 0.8

# -- 목록 스크롤 (DES-02·DES-04)
SCROLL_POINT = (1400, 420)   # 목록 중앙, 링크 없는 열 — 휠 전송 지점
