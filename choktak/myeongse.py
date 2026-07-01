"""촉탁명세서(xlsx) 읽기 모듈.

촉탁명세서의 한 행은 촉탁신청서 한 건에 대응한다.
컬럼(A~I)은 매뉴얼 기준:
    번호 | 대출계좌번호(A) | 채무자명(B) | 취급기관명(C) | 관할등기소(D)
        | 양수일자(E) | 등기일자(F) | 등기접수번호(G) | 등록세(H) | 지방세(I)
"""

from datetime import datetime, date

import openpyxl


# 헤더에 포함된 키워드로 컬럼 위치를 찾기 위한 매핑
_COLUMN_KEYWORDS = {
    "seq": ["번호"],
    "loan_account": ["대출계좌번호", "(A)"],
    "debtor": ["채무자명", "(B)"],
    "bank": ["취급기관명", "(C)"],
    "registry_office": ["관할등기소", "(D)"],
    "acquisition_date": ["양수일자", "(E)"],
    "reg_date": ["등기일자", "(F)"],
    "reg_receipt_no": ["등기접수번호", "(G)"],
    "reg_tax": ["등록세", "(H)"],
    "local_tax": ["지방세", "(I)"],
}


def _norm(value):
    """셀 값을 사람이 읽는 문자열로 정규화한다."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _find_columns(header_row):
    """헤더 셀 값을 보고 각 필드가 몇 번째 컬럼(0-based)인지 찾는다."""
    mapping = {}
    headers = [(_norm(c)) for c in header_row]
    for key, keywords in _COLUMN_KEYWORDS.items():
        for idx, text in enumerate(headers):
            if any(kw in text for kw in keywords):
                mapping[key] = idx
                break
    return mapping


def load_records(file_path):
    """촉탁명세서를 읽어 레코드 리스트를 반환한다.

    Returns:
        list[dict]: 각 dict는 아래 키를 가진다.
            row, seq, loan_account, debtor, bank, registry_office,
            acquisition_date, reg_date, reg_receipt_no, reg_tax, local_tax
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return []

    col = _find_columns(rows[0])
    if "bank" not in col or "registry_office" not in col:
        wb.close()
        raise ValueError(
            f"촉탁명세서 헤더를 인식하지 못했습니다: {rows[0]}"
        )

    records = []
    for r_idx, raw in enumerate(rows[1:], start=2):  # 2번째 행부터가 데이터
        if raw is None or all(c is None for c in raw):
            continue

        def get(field):
            i = col.get(field)
            if i is None or i >= len(raw):
                return ""
            return _norm(raw[i])

        debtor = get("debtor")
        bank = get("bank")
        if not debtor and not bank:
            continue  # 빈 행 취급

        # 세액은 숫자로도 보관 (합계 계산용)
        def get_int(field):
            i = col.get(field)
            if i is None or i >= len(raw) or raw[i] is None:
                return 0
            try:
                return int(float(str(raw[i]).replace(",", "")))
            except (ValueError, TypeError):
                return 0

        records.append({
            "row": r_idx,
            "seq": get("seq"),
            "loan_account": get("loan_account"),
            "debtor": debtor,
            "bank": bank,
            "registry_office": get("registry_office"),
            "acquisition_date": get("acquisition_date"),
            "reg_date": get("reg_date"),
            "reg_receipt_no": get("reg_receipt_no"),
            "reg_tax": get_int("reg_tax"),
            "local_tax": get_int("local_tax"),
        })

    wb.close()
    return records
