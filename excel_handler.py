"""엑셀 파일 읽기/쓰기 모듈"""

import openpyxl
from config import (
    EXCEL_FILE_PATH,
    PROPERTY_ID_COLUMN,
    RESULT_COLUMN,
    DATA_START_ROW,
)


def load_property_ids(file_path=None):
    """엑셀에서 부동산고유번호 목록을 읽어온다.

    Returns:
        list[dict]: [{"row": 행번호, "property_id": "고유번호"}, ...]
    """
    path = file_path or EXCEL_FILE_PATH
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    items = []
    for row_num in range(DATA_START_ROW, ws.max_row + 1):
        cell_value = ws.cell(row=row_num, column=PROPERTY_ID_COLUMN).value
        if cell_value is None:
            continue

        # 고유번호는 숫자로 저장될 수 있으므로 문자열로 변환
        property_id = str(cell_value).strip()

        # 하이픈 제거 (1234-5678-901234 → 1234567890123)
        property_id_clean = property_id.replace("-", "")

        if not property_id_clean:
            continue

        items.append({
            "row": row_num,
            "property_id": property_id_clean,
            "property_id_display": property_id,
        })

    wb.close()
    return items


def write_result(row_num, result_text, file_path=None):
    """엑셀의 결과 컬럼(A열)에 성공/실패를 기록한다."""
    path = file_path or EXCEL_FILE_PATH
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    ws.cell(row=row_num, column=RESULT_COLUMN, value=result_text)
    wb.save(path)
    wb.close()


def write_results_batch(results, file_path=None):
    """여러 결과를 한번에 기록한다.

    Args:
        results: list[dict] - [{"row": 행번호, "result": "성공"/"실패"}, ...]
    """
    path = file_path or EXCEL_FILE_PATH
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    for item in results:
        ws.cell(row=item["row"], column=RESULT_COLUMN, value=item["result"])

    wb.save(path)
    wb.close()
