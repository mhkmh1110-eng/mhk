"""촉탁신청서 제작 RPA 패키지.

촉탁명세서(xlsx), 은행목록(xlsx), 등기부등본(PDF)을 입력으로 받아
근저당권이전등기 촉탁신청서 PDF를 자동 생성한다.
"""

__all__ = [
    "config",
    "myeongse",
    "bank_directory",
    "deungbon_parser",
    "pdf_builder",
]
