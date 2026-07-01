"""등기사항전부증명서(등기부등본) PDF 파싱 모듈.

촉탁신청서 '부동산의 표시'에 들어갈 값들을 등기부등본에서 추출한다.

매뉴얼 규칙:
  - 대지권의 목적인 토지 소재지번은 '취소선(말소선)이 없는 최후 주소'를 사용한다.
    (등기부에서 변경/말소된 행은 텍스트 위에 짧은 수평선이 그어져 있다)
  - 1동 건물표시의 맨 끝 '제N동'을 전유부분 건물번호 앞에 붙인다.
    예) 제10층 제1005호 → 제310동 제10층 제1005호
"""

import re

import pdfplumber


# ─── 컬럼 x좌표 범위 (A4 기준, 등기부등본 표준 서식) ────────
# 표제부(1동): 소재지번,건물명칭 및 번호 컬럼
X_1DONG_LOCATION = (150, 300)
# 대지권 목적 토지: 소재지번 / 지목 / 면적 컬럼
X_LAND_LOCATION = (70, 243)
X_LAND_CATEGORY = (243, 300)
X_LAND_AREA = (300, 362)
# 전유부분: 건물번호 / 건물내역 컬럼
X_EXCL_BUILDING_NO = (150, 250)
X_EXCL_DETAIL = (250, 345)
# 대지권의 표시: 대지권종류 / 대지권비율 컬럼
X_LANDRIGHT_TYPE = (75, 205)
X_LANDRIGHT_RATIO = (255, 350)


def _hlines(page):
    """수평선 목록 (top≈bottom)."""
    return [l for l in page.lines if abs(l["top"] - l["bottom"]) < 1.0]


def _strike_lines(page):
    """취소선 후보: 전체폭 테두리(len>300)가 아닌 짧은 수평선."""
    return [l for l in _hlines(page) if 3 < (l["x1"] - l["x0"]) < 300]


def _full_borders(page, y0, y1):
    """[y0,y1] 구간의 전체폭 가로 테두리 y좌표(정렬)."""
    ys = {
        round(l["top"], 1)
        for l in _hlines(page)
        if (l["x1"] - l["x0"]) > 300 and y0 <= l["top"] <= y1
    }
    return sorted(ys)


def _words_in(page, y0, y1, x0, x1):
    """지정 사각 영역에 걸친 단어들을 (top,x0) 순으로 반환."""
    out = []
    for w in page.extract_words():
        cx = (w["x0"] + w["x1"]) / 2
        if y0 <= w["top"] <= y1 and x0 <= cx <= x1:
            out.append(w)
    return sorted(out, key=lambda w: (round(w["top"]), w["x0"]))


def _joined(words):
    return " ".join(w["text"] for w in words).strip()


def _is_struck(strikes, y0, y1, x0, x1):
    """[y0,y1]×[x0,x1] 영역 텍스트에 취소선이 그어졌는지 판정."""
    for l in strikes:
        ly = l["top"]
        if y0 - 1 <= ly <= y1 + 1 and l["x0"] < x1 and l["x1"] > x0:
            return True
    return False


def _find_word_y(page, keyword, x_max=None):
    """텍스트에 keyword를 포함하는 단어의 top y좌표(첫 매치)."""
    for w in sorted(page.extract_words(), key=lambda w: w["top"]):
        if keyword in w["text"] and (x_max is None or w["x0"] <= x_max):
            return w["top"]
    return None


def _find_line_y(page, keyword):
    """줄 단위로 합쳐 keyword를 포함하는 줄의 top y좌표."""
    lines = {}
    for w in page.extract_words():
        k = round(w["top"] / 3) * 3
        lines.setdefault(k, []).append(w)
    for k in sorted(lines):
        text = "".join(w["text"] for w in sorted(lines[k], key=lambda w: w["x0"]))
        if keyword.replace(" ", "") in text.replace(" ", ""):
            return min(w["top"] for w in lines[k])
    return None


class DeungbonParseError(Exception):
    pass


def parse(pdf_path):
    """등기부등본 PDF를 파싱해 부동산 표시 정보를 dict로 반환한다.

    반환 키:
        unique_no            고유번호 (예: 1164-1996-338621)
        building_1dong       1동 건물 소재지번·명칭 (제N동 포함)
        road_address         도로명주소 (없으면 "")
        dong                 제N동 (예: 제310동)
        exclusive_no         전유부분 건물번호 (제N동 접두 포함)
        structure            구조 (예: 피.씨조)
        exclusive_area       전유부분 면적 (예: 84.945㎡)
        land_location        대지권 목적 토지 소재지번 (취소선 없는 최후)
        land_category        지목 (예: 대)
        land_area            토지 면적 (예: 52157.2㎡)
        landright_type       대지권 종류 (예: 소유권)
        landright_ratio      대지권 비율 (예: 52157.2분의 53.388)
    """
    result = {
        "unique_no": "", "building_1dong": "", "road_address": "", "dong": "",
        "exclusive_no": "", "structure": "", "exclusive_area": "",
        "land_location": "", "land_category": "", "land_area": "",
        "landright_type": "", "landright_ratio": "",
    }

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)

        # 1) 고유번호
        m = re.search(r"고유번호\s*([0-9]{4}-[0-9]{4}-[0-9]{6})", full_text)
        if m:
            result["unique_no"] = m.group(1)

        for page in pdf.pages:
            text = page.extract_text() or ""
            if "1동의 건물의 표시" in text and not result["building_1dong"]:
                _parse_1dong(page, result)
            if "대지권의 목적인 토지의 표시" in text and not result["land_location"]:
                _parse_land_object(page, result)
            if "전유부분의 건물의 표시" in text and not result["exclusive_no"]:
                _parse_exclusive(page, result)
            if ("대지권의 표시" in text and "목적인" not in text.split("대지권의 표시")[0][-20:]
                    and not result["landright_ratio"]):
                _parse_landright(page, result)

    _postprocess(result)
    return result


def _parse_1dong(page, result):
    """표제부(1동 건물의 표시)에서 소재지번/도로명주소 추출."""
    # 컬럼 헤더('소재지번,건물명칭...') 아래 테두리 ~ 다음 섹션 위 테두리 사이가 데이터 영역
    y_colhead = _find_line_y(page, "소재지번") or _find_line_y(page, "1동의 건물의 표시") or 0
    y_next = _find_line_y(page, "대지권의 목적인 토지") or page.height
    borders = _full_borders(page, 0, page.height)
    data_top = min([b for b in borders if b > y_colhead + 3], default=y_colhead)
    data_bot = max([b for b in borders if b < y_next - 3], default=y_next)

    words = _words_in(page, data_top, data_bot, *X_1DONG_LOCATION)
    # 소재지번 텍스트는 연속된 줄 묶음. 큰 y간격(워터마크 등)에서 끊는다.
    block = []
    prev_top = None
    for w in words:
        if prev_top is not None and (w["top"] - prev_top) > 22:
            break
        block.append(w)
        prev_top = w["top"]

    text = _joined(block)
    if "[도로명주소]" in text:
        before, after = text.split("[도로명주소]", 1)
        result["building_1dong"] = re.sub(r"\s+", " ", before).strip()
        result["road_address"] = re.sub(r"\s+", " ", after).strip()
    else:
        result["building_1dong"] = re.sub(r"\s+", " ", text).strip()


def _parse_land_object(page, result):
    """대지권의 목적인 토지의 표시: 취소선 없는 최후 행 추출."""
    y_head = _find_line_y(page, "대지권의 목적인 토지의 표시") or 0
    y_bottom = page.height
    borders = _full_borders(page, y_head, y_bottom)
    if len(borders) < 3:
        return
    # 헤더행 아래 첫 데이터 경계부터 밴드 구성
    # borders[0]=헤더위, borders[1]=헤더아래 → 데이터는 borders[1]부터
    data_borders = borders[1:]
    strikes = _strike_lines(page)

    chosen = None
    for i in range(len(data_borders) - 1):
        top, bot = data_borders[i], data_borders[i + 1]
        loc_words = _words_in(page, top, bot, *X_LAND_LOCATION)
        loc = _joined(loc_words)
        if not loc or "소재지번" in loc:
            continue
        struck = _is_struck(strikes, top, bot, *X_LAND_LOCATION)
        if struck:
            continue
        cat = _joined(_words_in(page, top, bot, *X_LAND_CATEGORY))
        area = _joined(_words_in(page, top, bot, *X_LAND_AREA))
        chosen = {
            "loc": re.sub(r"\s+", " ", loc).strip(),
            "cat": cat.strip(),
            "area": area.strip(),
        }  # 마지막(최후) 비취소 행이 최종 선택됨

    if chosen:
        result["land_location"] = chosen["loc"]
        result["land_category"] = chosen["cat"]
        result["land_area"] = chosen["area"]


def _parse_exclusive(page, result):
    """전유부분의 건물의 표시: 건물번호/구조/면적 추출."""
    y_head = _find_line_y(page, "전유부분의 건물의 표시") or 0
    y_end = _find_line_y(page, "대지권의 표시") or page.height
    borders = _full_borders(page, y_head, y_end)
    # 헤더 아래 첫 데이터 밴드
    if len(borders) >= 3:
        top, bot = borders[1], borders[2]
    else:
        top, bot = y_head, y_end

    building_no = _joined(_words_in(page, top, bot, *X_EXCL_BUILDING_NO))
    m = re.search(r"제\s*\d+\s*층\s*제\s*\d+\s*호", building_no)
    result["exclusive_no"] = (m.group(0) if m else building_no).replace("  ", " ").strip()

    detail_words = _words_in(page, top, bot, *X_EXCL_DETAIL)
    detail = _joined(detail_words)
    am = re.search(r"[\d,]+\.\d+\s*㎡", detail)
    if am:
        result["exclusive_area"] = am.group(0).replace(" ", "")
    sm = re.search(r"[가-힣][가-힣.]*조", detail)
    if sm:
        result["structure"] = sm.group(0)


def _parse_landright(page, result):
    """대지권의 표시: 종류/비율 추출."""
    # '대지권의 표시' 중 '목적인'이 아닌 헤더 찾기
    y_head = None
    for kw_y in _all_line_y(page, "대지권의 표시"):
        # 목적 토지 헤더가 아니라 전유부분 뒤의 대지권 표시
        y_head = kw_y  # 마지막 매치 사용
    if y_head is None:
        return
    y_end = _find_line_y(page, "【 갑 구") or _find_line_y(page, "갑 구") or page.height
    borders = _full_borders(page, y_head, y_end)
    if len(borders) >= 3:
        top, bot = borders[1], borders[2]
    else:
        top, bot = y_head, y_end

    type_txt = _joined(_words_in(page, top, bot, *X_LANDRIGHT_TYPE))
    # 앞의 표시번호 숫자 제거 → "1 소유권대지권" → "소유권대지권"
    type_txt = re.sub(r"^\d+\s*", "", type_txt).strip()
    type_txt = re.sub(r"대지권$", "", type_txt).strip()
    result["landright_type"] = type_txt

    ratio_words = _words_in(page, top, bot, *X_LANDRIGHT_RATIO)
    ratio = _joined(ratio_words)
    rm = re.search(r"([\d,]+\.?\d*)\s*분의\s*([\d,]+\.?\d*)", ratio.replace(" ", ""))
    if rm:
        result["landright_ratio"] = f"{rm.group(1)}분의 {rm.group(2)}"
    else:
        result["landright_ratio"] = re.sub(r"\s+", " ", ratio).strip()


def _all_line_y(page, keyword):
    """keyword를 포함하는 모든 줄의 top y좌표 리스트."""
    lines = {}
    for w in page.extract_words():
        k = round(w["top"] / 3) * 3
        lines.setdefault(k, []).append(w)
    ys = []
    for k in sorted(lines):
        text = "".join(w["text"] for w in sorted(lines[k], key=lambda w: w["x0"]))
        if keyword.replace(" ", "") in text.replace(" ", ""):
            ys.append(min(w["top"] for w in lines[k]))
    return ys


def _postprocess(result):
    """제N동 추출 및 전유부분 건물번호 앞에 접두."""
    m = re.findall(r"제\s*\d+\s*동", result["building_1dong"])
    if m:
        dong = m[-1].replace(" ", "")
        result["dong"] = dong
        if result["exclusive_no"] and not result["exclusive_no"].startswith(dong):
            result["exclusive_no"] = f"{dong} {result['exclusive_no']}"
