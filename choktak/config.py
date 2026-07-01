"""촉탁신청서 제작 RPA 설정.

경로/폰트/고정값(등기권리자, 수수료 등)을 한곳에서 관리한다.
"""

import os

# ─── 기본 디렉터리 ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # choktak/
PROJECT_DIR = os.path.dirname(BASE_DIR)                          # repo root
FONT_DIR = os.path.join(PROJECT_DIR, "fonts")
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── 입력 파일/폴더 (환경변수로 재정의 가능) ────────────────
# 촉탁명세서: 한 행이 촉탁신청서 한 건에 대응 (A~I 컬럼)
MYEONGSE_FILE = os.environ.get(
    "CHOKTAK_MYEONGSE", os.path.join(PROJECT_DIR, "samples", "촉탁명세서_예시.xlsx")
)

# 은행목록: 취급기관명 → 법인번호/주소 (등기의무자 조회용)
BANK_LIST_FILE = os.environ.get(
    "CHOKTAK_BANK_LIST", os.path.join(DATA_DIR, "은행목록.xlsx")
)

# 등기부등본 PDF들이 모여있는 폴더 (파일명으로 명세서 행과 매칭)
DEUNGBON_DIR = os.environ.get(
    "CHOKTAK_DEUNGBON_DIR", os.path.join(PROJECT_DIR, "samples", "등기부등본")
)

# 산출물(촉탁신청서 PDF) 출력 폴더
OUTPUT_DIR = os.environ.get(
    "CHOKTAK_OUTPUT_DIR", os.path.join(PROJECT_DIR, "output")
)

# ─── 폰트 파일 ──────────────────────────────────────────────
FONT_REGULAR = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "NanumGothicBold.ttf")
FONT_EXTRABOLD = os.path.join(FONT_DIR, "NanumGothicExtraBold.ttf")

# reportlab 등록 시 사용할 폰트 이름
FONT_NAME_REGULAR = "NanumGothic"
FONT_NAME_BOLD = "NanumGothic-Bold"
FONT_NAME_EXTRABOLD = "NanumGothic-ExtraBold"

# ─── 등기권리자 (고정값: 한국주택금융공사) ─────────────────
# 한국주택금융공사법 제28조에 따른 촉탁신청 → 등기권리자는 항상 공사
CREDITOR_NAME = "한국주택금융공사"
CREDITOR_CEO = "사장 김 경 환"
CREDITOR_REG_NO = "110171-0029402"          # 등기용등록번호
CREDITOR_ADDRESS = "부산광역시 남구 문현금융로40(문현동, 부산국제금융센터)"
CREDITOR_CONTACT = "02-2638-1988"

# ─── 직인(약인) 날인 ────────────────────────────────────────
# 사장 서명 옆에 찍는 한국주택금융공사 직인 이미지(배경 투명 PNG)
# 실제 운영 시 고해상도 공식 직인 PNG로 교체하면 됨.
SEAL_IMAGE = os.environ.get("CHOKTAK_SEAL", os.path.join(DATA_DIR, "seal.png"))
SEAL_ENABLED = os.environ.get("CHOKTAK_SEAL_ENABLED", "true").lower() == "true"
SEAL_WIDTH = 62    # pt
SEAL_HEIGHT = 38   # pt (preserveAspectRatio로 폭에 맞춰 축소됨)

# ─── 고정 문구/금액 ────────────────────────────────────────
REG_PURPOSE = "근저당권이전"                # 등기의 목적
REG_CAUSE = "확정채권양도"                  # 등기원인
APPLICATION_FEE = 4000                       # 등기신청수수료 (원)
FEE_LEGAL_BASIS = "등기사항증명서등 수수료규칙 제5조의2 제4항"
HOUSING_BOND_BASIS = "주택도시기금법시행령 별표 제2호 사목"
COMMISSION_CLAUSE = "한국주택금융공사법 제28조 제2항의 규정에 의하여 위 등기를 촉탁합니다."

# 첨부서면 (좌/우 2단)
ATTACHMENTS_LEFT = [
    "1.주택저당채권 양도등록 사실확인서 1통(동시제출건 중 첫건 원용)",
    "1.신청서 부본 1통",
]
ATTACHMENTS_RIGHT = [
    "1.한국주택금융공사 법인등기부초본 1통",
    "  (동시제출건 중 첫건 원용)",
]
