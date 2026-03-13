#!/usr/bin/env python3
"""인터넷등기소 등기부등본 자동 발급 프로그램

엑셀 파일에 있는 부동산고유번호 목록을 읽어
인터넷등기소에서 등기부등본을 자동으로 발급/다운로드합니다.

사용법:
    python main.py                          # 기본 설정으로 실행
    python main.py --excel input.xlsx       # 엑셀 파일 지정
    python main.py --headless               # 백그라운드 실행
    python main.py --mode view              # 열람 모드 (기본)
    python main.py --mode issue             # 발급 모드
"""

import argparse
import logging
import sys
import os
from datetime import datetime

import config
from excel_handler import load_property_ids, write_result
from iros_automation import IrosAutomation


def setup_logging():
    """로깅 설정"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(
        log_dir, f"iros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="인터넷등기소 등기부등본 자동 발급 프로그램"
    )
    parser.add_argument(
        "--excel", "-e",
        default=config.EXCEL_FILE_PATH,
        help=f"부동산고유번호 엑셀 파일 경로 (기본: {config.EXCEL_FILE_PATH})",
    )
    parser.add_argument(
        "--output", "-o",
        default=config.DOWNLOAD_BASE_DIR,
        help=f"다운로드 폴더 경로 (기본: {config.DOWNLOAD_BASE_DIR})",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["view", "issue"],
        default=config.ISSUE_MODE,
        help="열람(view) 또는 발급(issue) 모드 (기본: view)",
    )
    parser.add_argument(
        "--cert-type", "-t",
        choices=["full", "current"],
        default=config.CERT_TYPE,
        help="전부사항(full) 또는 현재유효사항(current) (기본: full)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=config.HEADLESS,
        help="헤드리스 모드 (브라우저 창 숨김)",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="N번째 항목부터 시작 (0-based, 중간부터 재개할 때 사용)",
    )
    return parser.parse_args()


def main():
    logger = setup_logging()
    args = parse_args()

    # 설정 오버라이드
    config.EXCEL_FILE_PATH = args.excel
    config.ISSUE_MODE = args.mode
    config.CERT_TYPE = args.cert_type
    config.HEADLESS = args.headless

    # 다운로드 폴더 (오늘 날짜 하위 폴더)
    today = datetime.now().strftime("%Y%m%d")
    download_dir = os.path.join(args.output, today)

    logger.info("=" * 60)
    logger.info("인터넷등기소 등기부등본 자동 발급 프로그램")
    logger.info("=" * 60)
    logger.info(f"엑셀 파일    : {args.excel}")
    logger.info(f"다운로드 폴더: {download_dir}")
    logger.info(f"모드         : {args.mode}")
    logger.info(f"증명서 유형  : {args.cert_type}")
    logger.info(f"헤드리스     : {args.headless}")
    logger.info("=" * 60)

    # 1. 엑셀에서 부동산고유번호 목록 로드
    if not os.path.exists(args.excel):
        logger.error(f"엑셀 파일을 찾을 수 없습니다: {args.excel}")
        sys.exit(1)

    items = load_property_ids(args.excel)
    if not items:
        logger.error("처리할 부동산고유번호가 없습니다.")
        sys.exit(1)

    total = len(items)
    logger.info(f"총 {total}건의 부동산고유번호를 로드했습니다.")

    # start-from 옵션 처리
    if args.start_from > 0:
        items = items[args.start_from:]
        logger.info(f"{args.start_from}번째부터 시작합니다. 남은 건수: {len(items)}")

    # 2. 자동화 시작
    automation = IrosAutomation(
        download_dir=download_dir,
        headless=args.headless,
    )

    success_count = 0
    fail_count = 0

    try:
        automation.start()
        automation.login()

        for idx, item in enumerate(items):
            row = item["row"]
            pid = item["property_id"]
            display_pid = item["property_id_display"]

            logger.info(
                f"[{idx + 1}/{len(items)}] 처리 중: {display_pid}"
            )

            success = automation.process_single(pid)

            if success:
                write_result(row, "성공", args.excel)
                success_count += 1
                logger.info(f"  → 성공 (누적: {success_count}건)")
            else:
                write_result(row, "실패", args.excel)
                fail_count += 1
                logger.warning(f"  → 실패 (누적: {fail_count}건)")

            # 과도한 요청 방지를 위한 딜레이
            if idx < len(items) - 1:
                import time
                time.sleep(2)

    except KeyboardInterrupt:
        logger.warning("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
    finally:
        automation.close()

    # 3. 결과 요약
    logger.info("=" * 60)
    logger.info("처리 결과 요약")
    logger.info("=" * 60)
    logger.info(f"전체: {total}건")
    logger.info(f"성공: {success_count}건")
    logger.info(f"실패: {fail_count}건")
    logger.info(f"파일 저장 위치: {download_dir}")
    logger.info(f"결과 기록 파일: {args.excel}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
