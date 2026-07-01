"""은행목록(xlsx) 조회 모듈.

취급기관명(촉탁명세서 C)으로 등기의무자의 법인번호/주소를 찾는다.
    취급기관명 | 법인번호 | 주소
"""

import re

import openpyxl


def _norm(value):
    return "" if value is None else str(value).strip()


def _key(name):
    """기관명 비교용 정규화 키 (공백/괄호주석 제거, 대소문자 무시)."""
    name = _norm(name)
    name = re.sub(r"\s+", "", name)          # 모든 공백 제거
    return name.lower()


class BankDirectory:
    """은행목록 조회기."""

    def __init__(self, file_path):
        self.file_path = file_path
        self._by_key = {}
        self._load()

    def _load(self):
        wb = openpyxl.load_workbook(self.file_path, data_only=True)
        ws = wb.active
        for raw in list(ws.iter_rows(values_only=True))[1:]:  # 헤더 제외
            if raw is None or all(c is None for c in raw):
                continue
            name = _norm(raw[0])
            if not name:
                continue
            corp_no = _norm(raw[1]) if len(raw) > 1 else ""
            address = _norm(raw[2]) if len(raw) > 2 else ""
            self._by_key[_key(name)] = {
                "name": name,
                "corp_no": corp_no,
                "address": address,
            }
        wb.close()

    def lookup(self, bank_name):
        """취급기관명으로 등기의무자 정보를 조회한다.

        정확히 일치하지 않으면 부분 포함으로 재시도한다.
        Returns dict{name, corp_no, address} 또는 None.
        """
        key = _key(bank_name)
        if not key:
            return None
        if key in self._by_key:
            return self._by_key[key]

        # 부분 일치(포함) 폴백: "국민" → "국민은행"
        for k, v in self._by_key.items():
            if key in k or k in key:
                return v
        return None
