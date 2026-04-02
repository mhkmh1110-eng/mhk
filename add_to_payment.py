#!/usr/bin/env python3
"""인터넷등기소 부동산 등기부등본 결제대상 자동 추가 프로그램

엑셀 파일에 나열된 부동산고유번호를 읽어
인터넷등기소에서 결제대상 목록에 자동으로 추가합니다.

워크플로우:
  1. 인터넷등기소 접속 (전체화면) → 사용자 로그인 후 Enter
  2. [부동산 열람·발급] 클릭 → [고유번호검색] 탭 선택
  3. 고유번호 입력 → [검색] → [다음]
  4. [말소사항포함] 클릭하여 [현재유효사항]으로 변경 → [다음] → [다음]
  5. 결제대상 추가 완료 → 로고 클릭(메인) → 반복
  6. 실패 건은 작업 완료 후 텍스트 파일로 저장

사용법:
    python add_to_payment.py
    python add_to_payment.py --excel property_list.xlsx
"""

import argparse
import os
import sys
import time
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

from excel_handler import load_property_ids


# ─── 설정 ──────────────────────────────────────────────────
IROS_BASE_URL = "http://www.iros.go.kr"
ELEMENT_WAIT_TIMEOUT = 15
MAX_RETRIES = 2

# ─── 로깅 설정 ─────────────────────────────────────────────
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_filename = os.path.join(
    log_dir, f"add_payment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class PaymentQueueAutomation:
    """인터넷등기소 결제대상 자동 추가 클래스"""

    def __init__(self):
        self.driver = None
        self.failed_items = []  # 실패 목록: [(고유번호, 사유), ...]

    def _create_driver(self):
        """Chrome WebDriver 생성"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        # 전체화면 시작
        chrome_options.add_argument("--start-maximized")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(3)

    def start(self):
        """브라우저를 시작하고 인터넷등기소에 접속"""
        logger.info("브라우저 시작 중...")
        self._create_driver()

        logger.info("인터넷등기소 접속 중...")
        self.driver.get(IROS_BASE_URL)
        time.sleep(3)

        # 전체화면 (maximize 외 추가 보장)
        self.driver.maximize_window()
        logger.info("인터넷등기소 접속 완료 (전체화면)")

    def wait_for_login(self):
        """사용자가 로그인을 완료할 때까지 대기"""
        logger.info("=" * 50)
        logger.info("브라우저에서 로그인을 완료해 주세요.")
        logger.info("로그인 완료 후 Enter를 눌러주세요.")
        logger.info("=" * 50)
        input(">> 로그인 완료 후 Enter... ")
        logger.info("로그인 확인 → 작업 시작")

    def _wait_and_click(self, by, selector, timeout=None, description=""):
        """요소를 대기한 후 클릭"""
        timeout = timeout or ELEMENT_WAIT_TIMEOUT
        wait = WebDriverWait(self.driver, timeout)
        try:
            elem = wait.until(EC.element_to_be_clickable((by, selector)))
            elem.click()
            return True
        except ElementClickInterceptedException:
            # JS 클릭 폴백
            elem = self.driver.find_element(by, selector)
            self.driver.execute_script("arguments[0].click();", elem)
            return True
        except (TimeoutException, NoSuchElementException) as e:
            if description:
                logger.warning(f"{description} 클릭 실패: {e}")
            return False

    def _handle_alert(self, accept=True):
        """JavaScript alert 처리 (있으면 처리, 없으면 무시)"""
        try:
            alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            logger.info(f"알림 발생: {alert_text}")
            if accept:
                alert.accept()
            else:
                alert.dismiss()
            time.sleep(1)
            return alert_text
        except TimeoutException:
            return None

    def go_to_main(self):
        """메인 페이지로 이동 (로고 클릭)"""
        try:
            # 로고 클릭으로 메인 이동 시도
            logo_selectors = [
                (By.CSS_SELECTOR, "h1 a"),
                (By.CSS_SELECTOR, ".logo a"),
                (By.CSS_SELECTOR, "a[href*='Main']"),
                (By.CSS_SELECTOR, "#header a"),
                (By.XPATH, "//div[@id='header']//a"),
                (By.XPATH, "//h1//a"),
            ]
            for by, selector in logo_selectors:
                try:
                    elem = self.driver.find_element(by, selector)
                    if elem.is_displayed():
                        elem.click()
                        time.sleep(2)
                        logger.info("로고 클릭 → 메인 페이지 이동")
                        return True
                except (NoSuchElementException, ElementClickInterceptedException):
                    continue

            # 로고 클릭 실패시 URL 직접 이동
            self.driver.get(IROS_BASE_URL)
            time.sleep(2)
            logger.info("URL 직접 이동 → 메인 페이지")
            return True
        except Exception as e:
            logger.error(f"메인 페이지 이동 실패: {e}")
            self.driver.get(IROS_BASE_URL)
            time.sleep(2)
            return True

    def click_realty_view_issue(self):
        """메인에서 [부동산 열람·발급] 아이콘 클릭"""
        wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)

        selectors = [
            (By.XPATH, "//a[contains(text(), '열람') and contains(text(), '발급')]"),
            (By.XPATH, "//img[contains(@alt, '열람') and contains(@alt, '발급')]/.."),
            (By.XPATH, "//img[contains(@alt, '부동산')]/.."),
            (By.XPATH, "//a[contains(@href, 'iros') and contains(@href, 'realty')]"),
            (By.XPATH, "//div[contains(@class, 'main')]//a[contains(text(), '부동산')]"),
            (By.XPATH, "//a[contains(text(), '부동산')]"),
        ]

        for by, selector in selectors:
            try:
                elem = wait.until(EC.element_to_be_clickable((by, selector)))
                elem.click()
                time.sleep(2)
                logger.info("[부동산 열람·발급] 클릭 완료")
                return True
            except (TimeoutException, NoSuchElementException,
                    ElementClickInterceptedException):
                continue

        logger.error("[부동산 열람·발급] 아이콘을 찾을 수 없습니다.")
        return False

    def handle_existing_payment_popup(self):
        """'결제할 등기사항증명서가 존재합니다' 팝업 처리 → [취소] 클릭 (추가 계속)"""
        time.sleep(1)

        # JavaScript confirm/alert 팝업 처리
        try:
            alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
            alert_text = alert.text
            if "결제" in alert_text or "등기사항증명서" in alert_text:
                logger.info(f"결제대상 존재 팝업 감지: {alert_text}")
                alert.dismiss()  # [취소] 클릭 → 추가 모드
                logger.info("[취소] 클릭 → 추가 작업 계속")
                time.sleep(1)
                return True
            else:
                alert.accept()
                time.sleep(1)
                return False
        except TimeoutException:
            # 팝업 없음 (첫 번째 건이거나 이미 처리됨)
            return False

        # HTML 모달 팝업 처리 (alert가 아닌 경우)
        try:
            cancel_selectors = [
                (By.XPATH, "//button[contains(text(), '취소')]"),
                (By.XPATH, "//input[@value='취소']"),
                (By.XPATH, "//a[contains(text(), '취소')]"),
            ]
            for by, selector in cancel_selectors:
                try:
                    btn = self.driver.find_element(by, selector)
                    if btn.is_displayed():
                        btn.click()
                        logger.info("결제대상 팝업 [취소] 클릭 (HTML)")
                        time.sleep(1)
                        return True
                except NoSuchElementException:
                    continue
        except Exception:
            pass

        return False

    def select_unique_number_tab(self):
        """[고유번호검색] 탭 선택 (맨 오른쪽 탭)"""
        wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)

        selectors = [
            (By.XPATH, "//a[contains(text(), '고유번호')]"),
            (By.XPATH, "//li[contains(text(), '고유번호')]"),
            (By.XPATH, "//*[contains(text(), '고유번호검색')]"),
            (By.XPATH, "//a[contains(text(), '고유번호') and contains(text(), '검색')]"),
        ]

        for by, selector in selectors:
            try:
                elem = wait.until(EC.element_to_be_clickable((by, selector)))
                elem.click()
                time.sleep(1)
                logger.info("[고유번호검색] 탭 선택 완료")
                return True
            except (TimeoutException, NoSuchElementException,
                    ElementClickInterceptedException):
                continue

        logger.error("[고유번호검색] 탭을 찾을 수 없습니다.")
        return False

    def enter_property_id_and_search(self, property_id):
        """고유번호 입력 후 [검색] 클릭

        Args:
            property_id: 하이픈 없는 고유번호 문자열 (예: "1101202401234")
        """
        wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)

        # 고유번호를 4-4-6(또는 5) 형식으로 분할
        part1 = property_id[:4]
        part2 = property_id[4:8]
        part3 = property_id[8:]

        try:
            # 3개 분할 입력 필드 탐색
            input_fields = self.driver.find_elements(
                By.CSS_SELECTOR,
                "input[type='text'][maxlength]"
            )

            # 고유번호 입력 필드 찾기 (maxlength가 4, 4, 6 또는 유사)
            uid_fields = []
            for field in input_fields:
                if field.is_displayed():
                    maxlen = field.get_attribute("maxlength")
                    if maxlen and int(maxlen) <= 7:
                        uid_fields.append(field)

            if len(uid_fields) >= 3:
                for f in uid_fields[:3]:
                    f.clear()
                uid_fields[0].send_keys(part1)
                uid_fields[1].send_keys(part2)
                uid_fields[2].send_keys(part3)
                logger.info(f"고유번호 입력: {part1}-{part2}-{part3}")
            else:
                # 단일 입력 필드
                single_field = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input#uniqueNo, input.search-input, input[name*='unique']")
                    )
                )
                single_field.clear()
                single_field.send_keys(property_id)
                logger.info(f"고유번호 입력 (단일 필드): {property_id}")

            time.sleep(1)

            # [검색] 버튼 클릭
            search_selectors = [
                (By.XPATH, "//a[contains(text(), '검색')]"),
                (By.XPATH, "//button[contains(text(), '검색')]"),
                (By.XPATH, "//input[@value='검색']"),
                (By.CSS_SELECTOR, "a.btn_search"),
                (By.CSS_SELECTOR, "button.btn_search"),
            ]
            clicked = False
            for by, selector in search_selectors:
                try:
                    btn = self.driver.find_element(by, selector)
                    if btn.is_displayed():
                        btn.click()
                        clicked = True
                        break
                except (NoSuchElementException, ElementClickInterceptedException):
                    continue

            if not clicked:
                logger.error("[검색] 버튼을 찾을 수 없습니다.")
                return False

            time.sleep(2)

            # alert 처리 (검색 결과 없음 등)
            alert_text = self._handle_alert(accept=True)
            if alert_text and ("없습니다" in alert_text or "오류" in alert_text):
                logger.error(f"검색 실패 알림: {alert_text}")
                return False

            logger.info(f"[검색] 완료: {property_id}")
            return True

        except Exception as e:
            logger.error(f"고유번호 입력/검색 실패 [{property_id}]: {e}")
            return False

    def click_next_button(self, description="다음"):
        """[다음] 버튼 클릭"""
        time.sleep(1)

        next_selectors = [
            (By.XPATH, "//a[contains(text(), '다음')]"),
            (By.XPATH, "//button[contains(text(), '다음')]"),
            (By.XPATH, "//input[@value='다음']"),
            (By.CSS_SELECTOR, "a.btn_next"),
            (By.CSS_SELECTOR, "button.btn_next"),
        ]

        for by, selector in next_selectors:
            try:
                elem = self.driver.find_element(by, selector)
                if elem.is_displayed():
                    elem.click()
                    time.sleep(2)

                    # alert 처리
                    self._handle_alert(accept=True)

                    logger.info(f"[{description}] 클릭 완료")
                    return True
            except (NoSuchElementException, ElementClickInterceptedException):
                continue

        logger.error(f"[{description}] 버튼을 찾을 수 없습니다.")
        return False

    def select_current_valid_option(self):
        """등기기록유형에서 [말소사항포함]을 클릭하여 [현재유효사항]으로 변경"""
        time.sleep(1)

        # 방법 1: [말소사항포함] 클릭하여 토글 → [현재유효사항]
        toggle_selectors = [
            (By.XPATH, "//label[contains(text(), '말소사항포함')]"),
            (By.XPATH, "//input[contains(@id, 'malso') or contains(@name, 'malso')]"),
            (By.XPATH, "//*[contains(text(), '말소사항')]"),
        ]

        for by, selector in toggle_selectors:
            try:
                elem = self.driver.find_element(by, selector)
                if elem.is_displayed():
                    elem.click()
                    time.sleep(1)
                    logger.info("[말소사항포함] → [현재유효사항] 옵션 변경 완료")
                    return True
            except (NoSuchElementException, ElementClickInterceptedException):
                continue

        # 방법 2: [현재유효사항] 직접 선택
        current_selectors = [
            (By.XPATH, "//label[contains(text(), '현재유효')]"),
            (By.XPATH, "//input[contains(@value, 'current')]"),
            (By.XPATH, "//*[contains(text(), '현재유효사항')]"),
        ]

        for by, selector in current_selectors:
            try:
                elem = self.driver.find_element(by, selector)
                if elem.is_displayed():
                    elem.click()
                    time.sleep(1)
                    logger.info("[현재유효사항] 선택 완료")
                    return True
            except (NoSuchElementException, ElementClickInterceptedException):
                continue

        logger.warning("등기기록유형 옵션 변경 실패 (기본값으로 진행)")
        return False

    def process_single(self, property_id, display_id, is_first=False):
        """단일 고유번호를 결제대상에 추가하는 전체 흐름

        Args:
            property_id: 하이픈 제거된 고유번호
            display_id: 표시용 고유번호 (원본)
            is_first: 첫 번째 항목 여부

        Returns:
            bool: 성공 여부
        """
        try:
            # Step 1: 메인 → [부동산 열람·발급] 클릭
            if not self.click_realty_view_issue():
                return False

            # Step 2: 두 번째 건부터 결제대상 존재 팝업 처리 → [취소]
            if not is_first:
                self.handle_existing_payment_popup()

            time.sleep(1)

            # Step 3: [고유번호검색] 탭 선택
            if not self.select_unique_number_tab():
                return False

            # Step 4: 고유번호 입력 → [검색]
            if not self.enter_property_id_and_search(property_id):
                return False

            # Step 5: [다음] 클릭 (검색 결과 → 등기기록유형 선택)
            if not self.click_next_button("다음 (검색결과)"):
                return False

            # Step 6: [말소사항포함] → [현재유효사항] 옵션 변경
            self.select_current_valid_option()

            # Step 7: [다음] 클릭 (등기기록유형 → 다음 페이지)
            if not self.click_next_button("다음 (유형선택)"):
                return False

            # Step 8: [다음] 클릭 (다음 페이지 → 결제대상 추가 완료)
            if not self.click_next_button("다음 (최종확인)"):
                return False

            # Step 9: 결제대상 추가 완료 → 로고 클릭하여 메인으로
            logger.info(f"결제대상 추가 완료: {display_id}")
            time.sleep(1)
            self.go_to_main()
            time.sleep(1)

            return True

        except UnexpectedAlertPresentException as e:
            logger.error(f"예상치 못한 알림: {e}")
            try:
                self.driver.switch_to.alert.accept()
            except NoAlertPresentException:
                pass
            return False
        except Exception as e:
            logger.error(f"처리 실패 [{display_id}]: {e}")
            return False

    def save_failed_items(self):
        """실패한 항목들을 텍스트 파일로 저장"""
        if not self.failed_items:
            logger.info("실패 항목 없음 - 모든 작업 성공!")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fail_filename = f"failed_items_{timestamp}.txt"

        with open(fail_filename, "w", encoding="utf-8") as f:
            f.write(f"인터넷등기소 결제대상 추가 실패 목록\n")
            f.write(f"작업 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"실패 건수: {len(self.failed_items)}건\n")
            f.write("=" * 50 + "\n\n")

            for idx, (pid, reason) in enumerate(self.failed_items, 1):
                f.write(f"{idx}. 고유번호: {pid}  |  사유: {reason}\n")

        logger.info(f"실패 목록 저장 완료: {fail_filename} ({len(self.failed_items)}건)")
        return fail_filename

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("브라우저 종료")


def parse_args():
    parser = argparse.ArgumentParser(
        description="인터넷등기소 부동산 등기부등본 결제대상 자동 추가"
    )
    parser.add_argument(
        "--excel", "-e",
        default="property_list.xlsx",
        help="부동산고유번호 엑셀 파일 경로 (기본: property_list.xlsx)",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="N번째 항목부터 시작 (0-based, 중간부터 재개할 때 사용)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("인터넷등기소 결제대상 자동 추가 프로그램")
    logger.info("=" * 60)
    logger.info(f"엑셀 파일: {args.excel}")

    # 1. 엑셀에서 고유번호 목록 로드
    if not os.path.exists(args.excel):
        logger.error(f"엑셀 파일을 찾을 수 없습니다: {args.excel}")
        sys.exit(1)

    items = load_property_ids(args.excel)
    if not items:
        logger.error("처리할 부동산고유번호가 없습니다.")
        sys.exit(1)

    total = len(items)
    logger.info(f"총 {total}건의 부동산고유번호를 로드했습니다.")

    if args.start_from > 0:
        items = items[args.start_from:]
        logger.info(f"{args.start_from}번째부터 시작. 남은 건수: {len(items)}")

    # 2. 자동화 시작
    automation = PaymentQueueAutomation()
    success_count = 0
    fail_count = 0

    try:
        # 브라우저 시작 + 접속
        automation.start()

        # 사용자 로그인 대기
        automation.wait_for_login()

        # 3. 각 고유번호에 대해 결제대상 추가
        for idx, item in enumerate(items):
            pid = item["property_id"]
            display_pid = item["property_id_display"]
            is_first = (idx == 0)

            logger.info(f"\n[{idx + 1}/{len(items)}] 처리 중: {display_pid}")

            success = False
            for attempt in range(MAX_RETRIES + 1):
                if attempt > 0:
                    logger.info(f"  재시도 {attempt}/{MAX_RETRIES}")
                    # 재시도시 메인으로 돌아감
                    automation.go_to_main()
                    time.sleep(1)

                success = automation.process_single(
                    pid, display_pid, is_first=(is_first and attempt == 0)
                )
                if success:
                    break
                time.sleep(2)

            if success:
                success_count += 1
                logger.info(f"  -> 성공 (누적 {success_count}건)")
            else:
                fail_count += 1
                automation.failed_items.append((display_pid, "작업 실패"))
                logger.warning(f"  -> 실패 (누적 {fail_count}건)")

            # 과도한 요청 방지
            if idx < len(items) - 1:
                time.sleep(1)

    except KeyboardInterrupt:
        logger.warning("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
    finally:
        # 4. 실패 목록 저장
        fail_file = automation.save_failed_items()

        # 5. 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("처리 결과 요약")
        logger.info("=" * 60)
        logger.info(f"전체: {total}건")
        logger.info(f"성공: {success_count}건")
        logger.info(f"실패: {fail_count}건")
        if fail_file:
            logger.info(f"실패 목록: {fail_file}")
        logger.info("=" * 60)

        automation.close()


if __name__ == "__main__":
    main()
