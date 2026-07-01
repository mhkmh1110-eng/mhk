#!/usr/bin/env python3
"""촉탁신청서 제작 RPA (메인).

촉탁명세서(xlsx)의 각 행에 대해:
  1) 은행목록에서 취급기관명으로 등기의무자(법인번호/주소) 조회
  2) 등기부등본 PDF를 파싱해 부동산의 표시 정보 추출
  3) 근저당권이전등기 촉탁신청서 PDF 생성

사용법:
    python -m choktak.main
    python -m choktak.main --myeongse 촉탁명세서.xlsx --deungbon-dir 등기부폴더 --output 출력폴더
"""

import argparse
import glob
import logging
import os
import re
import sys
from datetime import datetime

from . import config
from . import myeongse
from . import deungbon_parser
from .bank_directory import BankDirectory
from . import pdf_builder


def setup_logging():
    log_dir = os.path.join(config.PROJECT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"choktak_{datetime.now():%Y%m%d_%H%M%S}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("choktak")


def find_deungbon(record, deungbon_dir):
    """명세서 레코드에 대응하는 등기부등본 PDF 경로를 찾는다.

    우선순위: (1) 파일명이 zero-padded 번호로 시작  (2) 채무자명 포함
    """
    if not os.path.isdir(deungbon_dir):
        return None
    pdfs = sorted(glob.glob(os.path.join(deungbon_dir, "*.pdf")))
    if not pdfs:
        return None

    seq = str(record.get("seq") or "").strip()
    if seq.isdigit():
        padded = seq.zfill(3)
        for p in pdfs:
            name = os.path.basename(p)
            if re.match(rf"0*{seq}\b", name) or name.startswith(padded) or name.startswith(seq + "_"):
                return p

    debtor = record.get("debtor", "")
    if debtor:
        for p in pdfs:
            if debtor in os.path.basename(p):
                return p

    # 명세서가 1건이고 PDF도 1건이면 그대로 매칭
    return pdfs[0] if len(pdfs) == 1 else None


def build_context(record, bank_info, deungbon, today):
    """PDF 생성에 필요한 완성 필드 dict를 조립한다."""
    tax_total = (record["reg_tax"] or 0) + (record["local_tax"] or 0)
    return {
        # 상단
        "bank": record["bank"],
        "debtor": record["debtor"],
        "loan_account": record["loan_account"],
        # 부동산의 표시 (등기부등본 파싱)
        "building_1dong": deungbon["building_1dong"],
        "road_address": deungbon["road_address"],
        "exclusive_no": deungbon["exclusive_no"],
        "structure": deungbon["structure"],
        "exclusive_area": deungbon["exclusive_area"],
        "unique_no": deungbon["unique_no"],
        "land_location": deungbon["land_location"],
        "land_category": deungbon["land_category"],
        "land_area": deungbon["land_area"],
        "landright_type": deungbon["landright_type"],
        "landright_ratio": deungbon["landright_ratio"],
        # 등기원인/목적/이전할 근저당권
        "cause_date": record["acquisition_date"],
        "reg_cause": config.REG_CAUSE,
        "reg_purpose": config.REG_PURPOSE,
        "reg_date": record["reg_date"],
        "reg_receipt_no": record["reg_receipt_no"],
        # 등기의무자 (은행목록)
        "obligor_name": bank_info["name"] if bank_info else record["bank"],
        "obligor_reg_no": bank_info["corp_no"] if bank_info else "",
        "obligor_addr": bank_info["address"] if bank_info else "",
        # 세액
        "reg_tax": record["reg_tax"],
        "local_tax": record["local_tax"],
        "tax_total": tax_total,
        # 관할등기소 / 날짜
        "registry_office": record["registry_office"],
        "today_year": today.year,
        "today_month": today.month,
        "today_day": today.day,
    }


def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def parse_args():
    p = argparse.ArgumentParser(description="촉탁신청서 제작 RPA")
    p.add_argument("--myeongse", "-m", default=config.MYEONGSE_FILE,
                   help=f"촉탁명세서 xlsx (기본: {config.MYEONGSE_FILE})")
    p.add_argument("--bank-list", "-b", default=config.BANK_LIST_FILE,
                   help="은행목록 xlsx")
    p.add_argument("--deungbon-dir", "-d", default=config.DEUNGBON_DIR,
                   help="등기부등본 PDF 폴더")
    p.add_argument("--output", "-o", default=config.OUTPUT_DIR,
                   help="촉탁신청서 PDF 출력 폴더")
    return p.parse_args()


def main():
    logger = setup_logging()
    args = parse_args()
    today = datetime.now()

    logger.info("=" * 60)
    logger.info("촉탁신청서 제작 RPA")
    logger.info("=" * 60)
    logger.info(f"촉탁명세서 : {args.myeongse}")
    logger.info(f"은행목록   : {args.bank_list}")
    logger.info(f"등기부폴더 : {args.deungbon_dir}")
    logger.info(f"출력폴더   : {args.output}")
    logger.info("=" * 60)

    if not os.path.exists(args.myeongse):
        logger.error(f"촉탁명세서를 찾을 수 없습니다: {args.myeongse}")
        sys.exit(1)

    records = myeongse.load_records(args.myeongse)
    if not records:
        logger.error("촉탁명세서에 처리할 데이터가 없습니다.")
        sys.exit(1)
    logger.info(f"촉탁명세서 {len(records)}건 로드")

    bank_dir = BankDirectory(args.bank_list)

    ok, fail = 0, 0
    for rec in records:
        label = f"[{rec['seq'] or rec['row']}] {rec['debtor']} / {rec['bank']}"
        try:
            bank_info = bank_dir.lookup(rec["bank"])
            if not bank_info:
                logger.warning(f"{label}: 은행목록에서 '{rec['bank']}'를 찾지 못함")

            pdf = find_deungbon(rec, args.deungbon_dir)
            if not pdf:
                logger.error(f"{label}: 대응하는 등기부등본 PDF를 찾지 못함 → 건너뜀")
                fail += 1
                continue

            deungbon = deungbon_parser.parse(pdf)
            ctx = build_context(rec, bank_info, deungbon, today)

            fname = sanitize_filename(
                f"{str(rec['seq']).zfill(3) if str(rec['seq']).isdigit() else rec['row']}"
                f"_{rec['debtor']}_촉탁신청서.pdf"
            )
            out_path = os.path.join(args.output, fname)
            pdf_builder.generate(ctx, out_path)
            logger.info(f"{label}: 생성 완료 → {out_path}")
            ok += 1
        except Exception as e:
            logger.error(f"{label}: 오류 - {e}", exc_info=True)
            fail += 1

    logger.info("=" * 60)
    logger.info(f"완료  성공 {ok}건 / 실패 {fail}건  (출력: {args.output})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
