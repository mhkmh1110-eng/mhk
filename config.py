"""인터넷등기소 자동 발급 프로그램 설정"""

import os
from datetime import datetime

# ─── 인터넷등기소 URL ───────────────────────────────────────
IROS_BASE_URL = "https://www.iros.go.kr"
IROS_LOGIN_URL = f"{IROS_BASE_URL}/PMainJ.jsp"
IROS_ISSUE_URL = f"{IROS_BASE_URL}/ifwd.jsp?laession=0&PKsession=0&jOption=0"

# ─── 사용자 정보 (환경변수 또는 직접 입력) ──────────────────
IROS_USER_ID = os.environ.get("IROS_USER_ID", "")
IROS_USER_PW = os.environ.get("IROS_USER_PW", "")

# ─── 파일 경로 설정 ────────────────────────────────────────
# 부동산고유번호가 담긴 엑셀 파일 경로
EXCEL_FILE_PATH = os.environ.get("EXCEL_FILE_PATH", "property_list.xlsx")

# 다운로드 기본 폴더 (오늘 날짜 폴더가 하위에 생성됨)
DOWNLOAD_BASE_DIR = os.environ.get("DOWNLOAD_BASE_DIR", "downloads")

# 오늘 날짜 폴더명
TODAY_FOLDER = datetime.now().strftime("%Y%m%d")

# 최종 다운로드 경로
DOWNLOAD_DIR = os.path.join(DOWNLOAD_BASE_DIR, TODAY_FOLDER)

# ─── 발급 옵션 ──────────────────────────────────────────────
# 등기부등본 유형: "full" (전부사항), "current" (현재유효사항)
CERT_TYPE = os.environ.get("CERT_TYPE", "full")

# 열람/발급 선택: "view" (열람 - 700원), "issue" (발급 - 1000원)
ISSUE_MODE = os.environ.get("ISSUE_MODE", "view")

# ─── 브라우저 설정 ──────────────────────────────────────────
# Chrome 브라우저 사용 (True: headless 모드)
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

# 페이지 로딩 대기 시간 (초)
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 15

# ─── 재시도 설정 ────────────────────────────────────────────
MAX_RETRIES = 2
RETRY_DELAY = 3  # 초

# ─── 엑셀 컬럼 설정 ────────────────────────────────────────
# 부동산고유번호가 있는 컬럼 (1-based index)
PROPERTY_ID_COLUMN = 2  # B열 (기본값)

# 결과를 기록할 컬럼 (1-based index)
RESULT_COLUMN = 1  # A열 (가장 왼쪽)

# 데이터 시작 행 (헤더 제외)
DATA_START_ROW = 2
