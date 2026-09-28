"""공헌 랭킹 화면 좌표·마커·기하 상수 — 유일한 캘리브레이션 지점 (설계 DES-02).

좌표계: 클라이언트 픽셀(2544×657 전제, NFR-04). 캡처 프레임(창 2546×689)에서
클라이언트 (0,0)은 (1, 31)이며 변환은 navigator.frame_client_offset()이 한다.
값은 P-01(2026-09-28 실기, 창 0x206be) 스냅샷 선별본(img/p01_*.png) 실측이다.
목록 기하·anchor 임계는 2026-09-28 픽스처 8장 실측(tests/test_list_geometry.py)이며
SCROLL_NOTCHES는 TASK-08 실기 보정 대상이다.
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

# -- 목록 스크롤 (DES-02·DES-04 6)
SCROLL_POINT = (1400, 420)   # 목록 중앙, 링크 없는 열 — 휠 전송 지점
SCROLL_NOTCHES = 12          # 단계당 휠 노치(초기값). P-01: 1노치 33px, 3노치 62px, 6노치 114px로
#   비선형 — 12노치 ≈ 200~250px(3행 내외) 추정. TASK-08 실기 보정
SHIFT_MAX = 364              # 겹침 상한 = LIST_REGION 높이 435 − ROW_PITCH. 이상이면 겹침 상실
ANCHOR_NCC_THRESHOLD = 0.8   # anchor 띠(CELL_NAME 30px) 재발견 임계. 픽스처 실측: 같은 행
#   0.976~0.982, 다른 행 ≤ 0.42, 겹침 상실(b10→b11) ≤ 0.34. 행 전폭 띠는 다른 행이
#   0.64~0.77까지 올라 기각

# -- 목록 기하 (DES-02·DES-04 2). 행 = 어두운 카드 + 상·하단 1px 밝은 테두리선, 카드
#   사이 6~7px 간격에는 밝기가 위치마다 다른 패널 배경이 보인다(검출 규칙은 list_scroller).
LIST_REGION = (960, 200, 1860, 635)   # 열 헤더 하단선(195~200) 아래 ~ 패널 바닥
ROW_PITCH = 71                        # 행 간격(실측 71.2 — 소수부는 순위 배정의 round()가 흡수)
ROW_HEIGHT = 65                       # 상단 테두리선 ~ 하단 테두리선
ROW_LINE_COL = (1140, 1160)           # 순위·세력 열 사이 빈 열 — 행 테두리선 검출 대역(x)
ROW_LINE_MIN_CONTRAST = 10            # 상단선 후보: 선 밝기 − 아래 행 내부(+2~+8px) 최대 밝기의
#   하한. 실측 상단선 22~56, 행 내부 잡음 < 4, 하단선 9~20(쌍 규칙으로 제거)
ROW_LINE_PAIR_MAX = 9                 # 하단선→다음 행 상단선 간격 상한(실측 6~7px)

# -- 행 상단 기준 셀 상자 (x0, +y0, x1, +y1)
CELL_RANK = (1030, 12, 1110, 52)      # 순위 숫자(중심 x≈1068)
CELL_NAME = (1180, 18, 1400, 48)      # 세력명(장식 프레임 포함 폭) — anchor 띠로도 사용
CELL_REGION = (1460, 18, 1560, 48)    # 지역
CELL_ALLIANCE = (1690, 18, 1790, 48)  # 동맹(밑줄 포함)
