"""근저당권이전등기 촉탁신청서 PDF 생성 모듈.

reportlab 캔버스로 촉탁신청서 서식을 그대로 재현한다.
본문은 나눔고딕(Regular/Bold), 맨 아래 '○○ 귀중'은 나눔고딕 ExtraBold.
"""

import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from . import config

PAGE_W, PAGE_H = A4  # 595.28 x 841.89

# 좌우 여백 및 표 전체 폭
LEFT = 30
RIGHT = PAGE_W - 30
WIDTH = RIGHT - LEFT

_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont(config.FONT_NAME_REGULAR, config.FONT_REGULAR))
    pdfmetrics.registerFont(TTFont(config.FONT_NAME_BOLD, config.FONT_BOLD))
    pdfmetrics.registerFont(TTFont(config.FONT_NAME_EXTRABOLD, config.FONT_EXTRABOLD))
    _FONTS_REGISTERED = True


class _Sheet:
    """top-down 좌표계로 캔버스에 그리는 헬퍼."""

    def __init__(self, c):
        self.c = c

    # ── 좌표 변환 (top → reportlab y) ──
    def _y(self, top):
        return PAGE_H - top

    def line(self, x1, t1, x2, t2, width=0.7):
        self.c.setLineWidth(width)
        self.c.line(x1, self._y(t1), x2, self._y(t2))

    def rect(self, x, top, w, h, width=0.7):
        self.c.setLineWidth(width)
        self.c.rect(x, self._y(top + h), w, h, stroke=1, fill=0)

    def hline(self, x1, x2, top, width=0.7):
        self.line(x1, top, x2, top, width)

    def vline(self, x, t1, t2, width=0.7):
        self.line(x, t1, x, t2, width)

    def text(self, x, top, s, size=9, font=None, align="left"):
        """top = 글자 윗선. align: left/center/right."""
        font = font or config.FONT_NAME_REGULAR
        self.c.setFont(font, size)
        y = self._y(top + size)  # baseline
        if align == "center":
            self.c.drawCentredString(x, y, s)
        elif align == "right":
            self.c.drawRightString(x, y, s)
        else:
            self.c.drawString(x, y, s)

    def text_in_cell(self, x0, x1, top, h, s, size=9, font=None, align="left", pad=4):
        """셀(x0~x1, top~top+h) 안에서 세로 가운데 정렬로 텍스트를 그린다."""
        ty = top + (h - size) / 2
        if align == "center":
            self.text((x0 + x1) / 2, ty, s, size, font, "center")
        elif align == "right":
            self.text(x1 - pad, ty, s, size, font, "right")
        else:
            self.text(x0 + pad, ty, s, size, font, "left")

    def vtext(self, x, top, s, size=9, font=None, gap=3):
        """세로쓰기(한 글자씩 아래로). '부동산의표시' 라벨용."""
        font = font or config.FONT_NAME_REGULAR
        self.c.setFont(font, size)
        cy = top
        for ch in s:
            self.c.drawCentredString(x, self._y(cy + size), ch)
            cy += size + gap


def _won(n):
    """정수를 '1,234' 형태로."""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def _fmt_date_ymd(s):
    """'2023-09-26' → '2023-09-26' (그대로), 날짜 객체 문자열 정규화."""
    return str(s).strip() if s else ""


def build_page(sheet, ctx):
    """촉탁신청서 한 페이지를 그린다. ctx는 완성된 필드 dict."""
    s = sheet
    R = config.FONT_NAME_REGULAR
    B = config.FONT_NAME_BOLD
    XB = config.FONT_NAME_EXTRABOLD

    # ── 1. 제목 ──
    top = 40
    s.text(PAGE_W / 2, top, "근저당권이전등기 촉탁신청서", size=18, font=B, align="center")
    top += 30

    # ── 2. 관리고유번호 / 채무자 (우측 정렬) ──
    s.text(RIGHT, top, f"관리고유번호 : {ctx['bank']}", size=9, font=R, align="right")
    top += 14
    s.text(RIGHT, top, f"{ctx['debtor']} ({ctx['loan_account']})", size=9, font=R, align="right")
    top += 16

    # ── 3. 접수 처리 표 ──
    proc_top = top
    proc_h = 34
    # 컬럼 경계 (접수라벨 | 접수기재 | 처리인 | 접수 | 조사 | 기입 | 교합 | 등기필통지 | 각종통지)
    xs = [LEFT, LEFT + 24, LEFT + 150, LEFT + 210,
          LEFT + 255, LEFT + 300, LEFT + 345, LEFT + 390, LEFT + 460, RIGHT]
    s.rect(LEFT, proc_top, WIDTH, proc_h)
    for x in xs[1:-1]:
        s.vline(x, proc_top, proc_top + proc_h)
    # 세로 중간선 (접수기재 셀과 나머지 상하 분할)
    mid = proc_top + proc_h / 2
    for i in range(2, len(xs) - 1):
        s.hline(xs[i], xs[i + 1] if i + 1 < len(xs) else RIGHT, mid)
    # 접수 라벨(세로)
    s.vtext(xs[0] + 12, proc_top + 6, "접수", size=9, font=R, gap=2)
    # 접수 기재 칸: 위 '2026 년 월 일', 아래 '제 호'
    from datetime import datetime
    yr = ctx["today_year"]
    s.text_in_cell(xs[1], xs[2], proc_top, proc_h / 2, f"{yr} 년      월      일", size=8, align="center")
    s.text_in_cell(xs[1], xs[2], mid, proc_h / 2, "제              호", size=8, align="center")
    # 나머지 헤더
    headers = ["처리인", "접수", "조사", "기입", "교합", "등기필통지", "각종통지"]
    for i, htxt in enumerate(headers):
        cx0, cx1 = xs[i + 2], xs[i + 3]
        s.text_in_cell(cx0, cx1, proc_top, proc_h / 2, htxt, size=7.5, align="center")
    top = proc_top + proc_h

    # ── 4. 부동산의 표시 ──
    re_top = top
    re_h = 226
    label_w = 22
    s.rect(LEFT, re_top, WIDTH, re_h)
    s.vline(LEFT + label_w, re_top, re_top + re_h)
    s.vtext(LEFT + label_w / 2, re_top + 55, "부동산의표시", size=9, font=R, gap=8)

    cx = LEFT + label_w + 10
    ct = re_top + 12
    lh = 15  # 줄높이
    s.text(cx, ct, "1.1동의 건물의 표시", size=9.5, font=R); ct += lh + 3
    s.text(cx + 14, ct, ctx["building_1dong"], size=9.5, font=R); ct += lh
    s.text(cx + 14, ct, f"[도로명주소]{ctx['road_address']}", size=9.5, font=R); ct += lh + 8

    s.text(cx, ct, "전유부분의 건물의 표시", size=9.5, font=R); ct += lh + 3
    s.text(cx + 14, ct,
           f"1.건물의 번호 : {ctx['exclusive_no']}[고유번호:{ctx['unique_no']}]",
           size=9.5, font=R); ct += lh
    s.text(cx + 14, ct, f"구조 및 면적 : {ctx['structure']} {ctx['exclusive_area']}",
           size=9.5, font=R); ct += lh + 8

    s.text(cx, ct, "전유부분의 대지권의 표시", size=9.5, font=R); ct += lh + 3
    s.text(cx + 14, ct, "토지의 표시", size=9.5, font=R); ct += lh
    s.text(cx + 24, ct, ctx["land_location"], size=9.5, font=R); ct += lh
    s.text(cx + 24, ct, f"{ctx['land_category']} {ctx['land_area']}", size=9.5, font=R); ct += lh
    s.text(cx + 24, ct, f"대지권의 종류: {ctx['landright_type']}", size=9.5, font=R); ct += lh
    s.text(cx + 24, ct, f"대지권의 비율: {ctx['landright_ratio']}", size=9.5, font=R)
    top = re_top + re_h

    # ── 5. 등기원인 / 목적 / 이전할 근저당권 ──
    label_x = LEFT + 130   # 좌측 라벨열 폭
    row_h = 18
    # 등기원인과 그 년월일
    s.rect(LEFT, top, WIDTH, row_h)
    s.vline(label_x, top, top + row_h)
    s.text_in_cell(LEFT, label_x, top, row_h, "등기원인과 그 년월일", size=9, align="center")
    s.text_in_cell(label_x, RIGHT, top, row_h,
                   f"  {ctx['cause_date']} {ctx['reg_cause']}", size=9)
    top += row_h
    # 등기의 목적
    s.rect(LEFT, top, WIDTH, row_h)
    s.vline(label_x, top, top + row_h)
    s.text_in_cell(LEFT, label_x, top, row_h, "등 기 의 목 적", size=9, align="center")
    s.text_in_cell(label_x, RIGHT, top, row_h, f"  {ctx['reg_purpose']}", size=9)
    top += row_h
    # 이전할 근저당권 (2줄)
    trans_h = 30
    s.rect(LEFT, top, WIDTH, trans_h)
    s.vline(label_x, top, top + trans_h)
    s.text_in_cell(LEFT, label_x, top, trans_h, "이전 할 근저당권", size=9, align="center")
    s.text(label_x + 6, top + 4,
           f"{ctx['reg_date']} 제 {ctx['reg_receipt_no']} 호로서 등기한 근저당권.", size=9)
    s.text(label_x + 6, top + 17, "(단, 근저당권을 채권과 함께 이전함)", size=8.5)
    top += trans_h

    # ── 6. 등기의무자 / 등기권리자 표 ──
    # 컬럼: 구분 | 성명(상호,명칭) | 주민등록번호(등기용등록번호) | 주소(소재지)
    c0 = LEFT
    c1 = LEFT + 60      # 구분
    c2 = LEFT + 200     # 성명
    c3 = LEFT + 320     # 주민번호
    c4 = RIGHT          # 주소
    head_h = 24
    s.rect(LEFT, top, WIDTH, head_h)
    for x in (c1, c2, c3):
        s.vline(x, top, top + head_h)
    s.text_in_cell(c0, c1, top, head_h, "구 분", size=9, align="center")
    s.text_in_cell(c1, c2, top, head_h, "성명(상호, 명칭)", size=9, align="center")
    s.text(( c2 + c3) / 2, top + 3, "주민등록번호", size=8, align="center")
    s.text(( c2 + c3) / 2, top + 13, "(등기용등록번호)", size=8, align="center")
    s.text_in_cell(c3, c4, top, head_h, "주 소 (소 재 지)", size=9, align="center")
    top += head_h

    # 등기의무자 행
    ob_h = 30
    _party_row(s, top, ob_h, c0, c1, c2, c3, c4,
               "등 기\n의무자", ctx["obligor_name"], ctx["obligor_reg_no"], ctx["obligor_addr"])
    top += ob_h
    # 등기권리자 행
    cr_h = 30
    _party_row(s, top, cr_h, c0, c1, c2, c3, c4,
               "등 기\n권리자",
               f"{config.CREDITOR_NAME}\n{config.CREDITOR_CEO}",
               config.CREDITOR_REG_NO, config.CREDITOR_ADDRESS)
    top += cr_h

    # ── 7. 등록면허세 / 등기신청수수료 / 국민주택채권 ──
    for label, value in [
        ("등록면허세, 교육세",
         f"  등록세: {_won(ctx['reg_tax'])} 원, 교육세: {_won(ctx['local_tax'])} 원 "
         f"(합계: {_won(ctx['tax_total'])} 원)"),
        ("등기신청수수료",
         f"  금 {_won(config.APPLICATION_FEE)} 원 ({config.FEE_LEGAL_BASIS})"),
        ("국민주택채권 매입금액", f"  {config.HOUSING_BOND_BASIS}"),
    ]:
        s.rect(LEFT, top, WIDTH, row_h)
        s.vline(label_x, top, top + row_h)
        s.text_in_cell(LEFT, label_x, top, row_h, label, size=8.5, align="center")
        s.text_in_cell(label_x, RIGHT, top, row_h, value, size=8.5)
        top += row_h

    # ── 8. 첨부서면 ──
    att_h = 14 + 14 * max(len(config.ATTACHMENTS_LEFT), len(config.ATTACHMENTS_RIGHT))
    s.rect(LEFT, top, WIDTH, att_h)
    s.text(PAGE_W / 2, top + 3, "첨 부 서 면", size=9, font=R, align="center")
    ay = top + 17
    for i, line in enumerate(config.ATTACHMENTS_LEFT):
        s.text(LEFT + 8, ay + i * 13, line, size=8)
    for i, line in enumerate(config.ATTACHMENTS_RIGHT):
        s.text(LEFT + WIDTH / 2 + 8, ay + i * 13, line, size=8)
    top += att_h + 6

    # ── 9. 촉탁 문구 ──
    s.text(PAGE_W / 2, top, config.COMMISSION_CLAUSE, size=9, font=R, align="center")
    top += 20

    # ── 10. 날짜 ──
    s.text(PAGE_W / 2, top,
           f"{ctx['today_year']} 년    {ctx['today_month']:0>2} 월    {ctx['today_day']:0>2} 일",
           size=9.5, font=R, align="center")
    top += 20

    # ── 11. 신청인 ──
    s.text(PAGE_W / 2, top, f"위 신청인   {config.CREDITOR_NAME}", size=9.5, font=R, align="center")
    top += 15
    ceo = config.CREDITOR_CEO.replace("사장 ", "사장 ")
    s.text(PAGE_W / 2 + 30, top, ceo, size=9.5, font=R, align="center")
    top += 15
    s.text(PAGE_W / 2 + 30, top, f"(담당자 : {config.CREDITOR_CONTACT})", size=8.5, font=R, align="center")
    top += 26

    # ── 12. 관할등기소 귀중 (ExtraBold) ──
    s.text(PAGE_W / 2, top, f"{ctx['registry_office']} 귀중", size=13, font=XB, align="center")


def _party_row(s, top, h, c0, c1, c2, c3, c4, gubun, name, reg_no, addr):
    """등기의무자/권리자 한 행을 그린다. gubun/name은 \\n 다중행 지원."""
    s.rect(c0, top, c4 - c0, h)
    for x in (c1, c2, c3):
        s.vline(x, top, top + h)

    def multiline(x0, x1, txt, size, align="center", pad=4):
        parts = txt.split("\n")
        n = len(parts)
        line_h = size + 3
        block = n * line_h
        start = top + (h - block) / 2
        for i, p in enumerate(parts):
            ty = start + i * line_h
            if align == "center":
                s.text((x0 + x1) / 2, ty, p, size, align="center")
            else:
                s.text(x0 + pad, ty, p, size, align="left")

    multiline(c0, c1, gubun, 9, "center")
    multiline(c1, c2, name, 9, "center")
    s.text_in_cell(c2, c3, top, h, reg_no, size=8.5, align="center")
    # 주소는 길면 두 줄로 감쌈
    _wrapped_text(s, c3 + 4, c4 - 4, top, h, addr, size=8)


def _wrapped_text(s, x0, x1, top, h, txt, size=8):
    """주소를 셀 폭에 맞춰 줄바꿈하여 세로 가운데 배치."""
    max_w = x1 - x0
    from reportlab.pdfbase.pdfmetrics import stringWidth
    font = config.FONT_NAME_REGULAR
    words = txt.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    line_h = size + 3
    block = len(lines) * line_h
    start = top + (h - block) / 2
    for i, ln in enumerate(lines):
        s.text(x0, start + i * line_h, ln, size, font, "left")


def generate(ctx, out_path):
    """ctx(완성된 필드 dict)로 촉탁신청서 PDF 한 장을 생성한다."""
    _register_fonts()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    c = canvas.Canvas(out_path, pagesize=A4)
    sheet = _Sheet(c)
    build_page(sheet, ctx)
    c.showPage()
    c.save()
    return out_path
