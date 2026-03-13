"""인터넷등기소 결제 처리 모듈

결제 방식별 자동 결제 로직을 처리합니다.

지원 결제 방식:
  1. 선불전자지급수단 (prepaid) - 미리 충전된 잔액으로 결제 (가장 자동화에 적합)
  2. 신용카드 (card) - ISP/안심클릭 없는 일반 결제
  3. 계좌이체 (transfer) - 수동 결제 (팝업 대기)
"""

import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoAlertPresentException,
)

import config

logger = logging.getLogger(__name__)


class PaymentHandler:
    """결제 처리 핸들러"""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.ELEMENT_WAIT_TIMEOUT)

    def process_payment(self):
        """설정된 결제 방식으로 결제를 처리한다.

        Returns:
            bool: 결제 성공 여부
        """
        method = config.PAYMENT_METHOD

        logger.info(f"결제 처리 시작 (방식: {method})")

        if method == "prepaid":
            return self._pay_with_prepaid()
        elif method == "card":
            return self._pay_with_card()
        elif method == "transfer":
            return self._pay_with_transfer()
        else:
            logger.error(f"지원하지 않는 결제 방식: {method}")
            return False

    # ──────────────────────────────────────────────────────────
    # 1. 선불전자지급수단 (충전잔액) 결제
    # ──────────────────────────────────────────────────────────

    def _pay_with_prepaid(self):
        """선불전자지급수단(충전잔액)으로 결제한다.

        인터넷등기소에서 미리 충전해 둔 잔액을 사용.
        결제 팝업에서 '선불전자지급수단' 선택 → 비밀번호 입력 → 결제.
        """
        try:
            # 결제수단 선택 영역 대기
            self._wait_for_payment_page()

            # '선불전자지급수단' 라디오/탭 선택
            prepaid_option = self._find_and_click(
                [
                    (By.XPATH, "//label[contains(text(), '선불전자')]"),
                    (By.XPATH, "//input[@value='prepaid']"),
                    (By.XPATH, "//a[contains(text(), '선불전자')]"),
                    (By.XPATH, "//li[contains(text(), '선불전자')]"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='PREPAID']"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='prepaid']"),
                ]
            )
            if not prepaid_option:
                logger.error("선불전자지급수단 옵션을 찾을 수 없습니다.")
                return False

            time.sleep(1)

            # 잔액 확인 (가능한 경우)
            balance = self._check_prepaid_balance()
            if balance is not None:
                unit_price = (
                    config.PRICE_VIEW
                    if config.ISSUE_MODE == "view"
                    else config.PRICE_ISSUE
                )
                if balance < unit_price:
                    logger.error(
                        f"잔액 부족: 잔액 {balance:,}원, 필요 {unit_price:,}원"
                    )
                    if config.ON_INSUFFICIENT_BALANCE == "stop":
                        raise InsufficientBalanceError(
                            f"잔액 부족 ({balance:,}원)"
                        )
                    return False

            # 비밀번호 입력 (필요한 경우)
            if config.PREPAID_PASSWORD:
                self._enter_prepaid_password(config.PREPAID_PASSWORD)

            # 결제 실행 버튼 클릭
            if not self._click_pay_button():
                return False

            # 결제 확인 알림/팝업 처리
            self._handle_confirm_dialogs()

            # 결제 완료 확인
            if self._verify_payment_success():
                logger.info("선불전자지급수단 결제 성공")
                return True
            else:
                logger.error("결제 완료를 확인할 수 없습니다.")
                return False

        except InsufficientBalanceError:
            raise
        except Exception as e:
            logger.error(f"선불전자지급수단 결제 실패: {e}")
            return False

    def _check_prepaid_balance(self):
        """선불전자지급수단 잔액을 확인한다.

        Returns:
            int: 잔액 (원) 또는 None (확인 불가 시)
        """
        try:
            balance_elem = self.driver.find_element(
                By.XPATH,
                "//*[contains(text(), '잔액') or contains(text(), '잔여')]"
                "/following-sibling::*"
                " | //*[contains(@class, 'balance')]"
            )
            text = balance_elem.text.strip()
            # "12,500원" → 12500
            amount = int(text.replace(",", "").replace("원", "").strip())
            logger.info(f"선불전자지급수단 잔액: {amount:,}원")
            return amount
        except (NoSuchElementException, ValueError):
            logger.debug("잔액 확인 불가 (정상적일 수 있음)")
            return None

    def _enter_prepaid_password(self, password):
        """선불전자지급수단 비밀번호를 입력한다."""
        try:
            pw_field = self._find_element(
                [
                    (By.CSS_SELECTOR, "input[type='password'][name*='prepaid']"),
                    (By.CSS_SELECTOR, "input[type='password'][name*='Pw']"),
                    (By.CSS_SELECTOR, "input[type='password'][id*='prepaid']"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                ]
            )
            if pw_field:
                pw_field.clear()
                pw_field.send_keys(password)
                logger.debug("선불전자지급수단 비밀번호 입력 완료")
            else:
                logger.debug("비밀번호 필드를 찾을 수 없음 (불필요할 수 있음)")
        except Exception as e:
            logger.debug(f"비밀번호 입력 건너뜀: {e}")

    # ──────────────────────────────────────────────────────────
    # 2. 신용카드 결제
    # ──────────────────────────────────────────────────────────

    def _pay_with_card(self):
        """신용카드로 결제한다.

        인터넷등기소 → 결제 팝업 → 신용카드 선택 →
        카드사/카드번호/유효기간/생년월일/비밀번호 입력 → 결제.

        ※ ISP(국민/BC 등) 결제는 별도 앱 인증이 필요하므로
           안심클릭 계열 카드(삼성/현대/롯데 등)가 자동화에 적합합니다.
        """
        try:
            if not all([
                config.CARD_COMPANY,
                config.CARD_NUMBER,
                config.CARD_EXPIRY,
                config.CARD_BIRTH,
                config.CARD_PASSWORD_2DIGIT,
            ]):
                logger.error(
                    "신용카드 정보가 불완전합니다. "
                    "환경변수를 확인하세요: IROS_CARD_COMPANY, IROS_CARD_NUMBER, "
                    "IROS_CARD_EXPIRY, IROS_CARD_BIRTH, IROS_CARD_PW2"
                )
                return False

            self._wait_for_payment_page()

            # '신용카드' 라디오/탭 선택
            card_option = self._find_and_click(
                [
                    (By.XPATH, "//label[contains(text(), '신용카드')]"),
                    (By.XPATH, "//input[@value='card']"),
                    (By.XPATH, "//a[contains(text(), '신용카드')]"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='CARD']"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='card']"),
                ]
            )
            if not card_option:
                logger.error("신용카드 옵션을 찾을 수 없습니다.")
                return False

            time.sleep(1)

            # 카드사 선택
            self._select_card_company(config.CARD_COMPANY)

            # 카드번호 입력 (4자리씩 분할 입력 또는 연속 입력)
            self._enter_card_number(config.CARD_NUMBER)

            # 유효기간 입력 (MM/YY)
            self._enter_card_expiry(config.CARD_EXPIRY)

            # 생년월일 / 사업자번호 입력
            self._enter_card_birth(config.CARD_BIRTH)

            # 비밀번호 앞 2자리
            self._enter_card_password(config.CARD_PASSWORD_2DIGIT)

            # 결제 버튼 클릭
            if not self._click_pay_button():
                return False

            # 결제 PG사 팝업/iframe 처리
            self._handle_pg_popup()

            # 결제 확인 알림/팝업 처리
            self._handle_confirm_dialogs()

            if self._verify_payment_success():
                logger.info("신용카드 결제 성공")
                return True
            else:
                logger.error("결제 완료를 확인할 수 없습니다.")
                return False

        except Exception as e:
            logger.error(f"신용카드 결제 실패: {e}")
            return False

    def _select_card_company(self, company_name):
        """카드사를 선택한다."""
        try:
            # select 드롭다운 방식
            select_elem = self._find_element(
                [
                    (By.CSS_SELECTOR, "select[name*='card']"),
                    (By.CSS_SELECTOR, "select[name*='Card']"),
                    (By.CSS_SELECTOR, "select[id*='card']"),
                    (By.CSS_SELECTOR, "select.card-company"),
                ]
            )
            if select_elem:
                select = Select(select_elem)
                # 텍스트에 카드사명이 포함된 옵션 선택
                for option in select.options:
                    if company_name in option.text:
                        select.select_by_visible_text(option.text)
                        logger.debug(f"카드사 선택: {option.text}")
                        return
                # 정확한 매칭 실패 시 부분 매칭 시도
                select.select_by_visible_text(company_name)
                return

            # 라디오/버튼 방식
            self._find_and_click(
                [
                    (By.XPATH, f"//label[contains(text(), '{company_name}')]"),
                    (By.XPATH, f"//a[contains(text(), '{company_name}')]"),
                    (By.XPATH, f"//button[contains(text(), '{company_name}')]"),
                ]
            )
        except Exception as e:
            logger.warning(f"카드사 선택 실패 (수동 선택 필요): {e}")

    def _enter_card_number(self, card_number):
        """카드번호를 입력한다."""
        clean_number = card_number.replace("-", "").replace(" ", "")

        # 4개 분할 필드 시도
        card_fields = self.driver.find_elements(
            By.CSS_SELECTOR,
            "input[name*='cardNo'], input[name*='card_no'], "
            "input[id*='cardNo'], input[class*='card-num']"
        )

        if len(card_fields) >= 4:
            # 4자리씩 분할 입력
            for i, field in enumerate(card_fields[:4]):
                part = clean_number[i * 4:(i + 1) * 4]
                field.clear()
                field.send_keys(part)
            logger.debug("카드번호 입력 완료 (4필드)")
        elif len(card_fields) == 1:
            card_fields[0].clear()
            card_fields[0].send_keys(clean_number)
            logger.debug("카드번호 입력 완료 (단일필드)")
        else:
            logger.warning("카드번호 입력 필드를 찾을 수 없습니다.")

    def _enter_card_expiry(self, expiry):
        """유효기간을 입력한다 (MMYY 형식)."""
        mm = expiry[:2]
        yy = expiry[2:4]

        # 월/년 분리 필드 시도
        month_field = self._find_element(
            [
                (By.CSS_SELECTOR, "input[name*='expMm'], select[name*='expMm']"),
                (By.CSS_SELECTOR, "input[name*='validMm'], select[name*='validMm']"),
                (By.CSS_SELECTOR, "input[id*='expMonth'], select[id*='expMonth']"),
            ]
        )
        year_field = self._find_element(
            [
                (By.CSS_SELECTOR, "input[name*='expYy'], select[name*='expYy']"),
                (By.CSS_SELECTOR, "input[name*='validYy'], select[name*='validYy']"),
                (By.CSS_SELECTOR, "input[id*='expYear'], select[id*='expYear']"),
            ]
        )

        if month_field and year_field:
            if month_field.tag_name == "select":
                Select(month_field).select_by_value(mm)
                Select(year_field).select_by_value(yy)
            else:
                month_field.clear()
                month_field.send_keys(mm)
                year_field.clear()
                year_field.send_keys(yy)
            logger.debug("유효기간 입력 완료")
        else:
            # 단일 필드
            expiry_field = self._find_element(
                [
                    (By.CSS_SELECTOR, "input[name*='expiry']"),
                    (By.CSS_SELECTOR, "input[name*='valid']"),
                ]
            )
            if expiry_field:
                expiry_field.clear()
                expiry_field.send_keys(expiry)

    def _enter_card_birth(self, birth):
        """생년월일 또는 사업자번호를 입력한다."""
        birth_field = self._find_element(
            [
                (By.CSS_SELECTOR, "input[name*='birth']"),
                (By.CSS_SELECTOR, "input[name*='Birth']"),
                (By.CSS_SELECTOR, "input[name*='authNo']"),
                (By.CSS_SELECTOR, "input[id*='birth']"),
            ]
        )
        if birth_field:
            birth_field.clear()
            birth_field.send_keys(birth)
            logger.debug("생년월일/사업자번호 입력 완료")

    def _enter_card_password(self, pw2):
        """카드 비밀번호 앞 2자리를 입력한다."""
        pw_field = self._find_element(
            [
                (By.CSS_SELECTOR, "input[name*='cardPw']"),
                (By.CSS_SELECTOR, "input[name*='card_pw']"),
                (By.CSS_SELECTOR, "input[name*='password'][maxlength='2']"),
                (By.CSS_SELECTOR, "input[type='password'][maxlength='2']"),
            ]
        )
        if pw_field:
            pw_field.clear()
            pw_field.send_keys(pw2)
            logger.debug("카드 비밀번호 입력 완료")

    def _handle_pg_popup(self):
        """PG사 결제 팝업/iframe을 처리한다."""
        time.sleep(3)

        # 새 창(팝업)이 열렸는지 확인
        windows = self.driver.window_handles
        if len(windows) > 1:
            # 마지막 팝업 창으로 전환
            self.driver.switch_to.window(windows[-1])
            logger.debug("결제 팝업 창으로 전환")
            time.sleep(2)

            # 팝업 내에서 '확인'/'결제' 버튼 클릭
            self._find_and_click(
                [
                    (By.XPATH, "//button[contains(text(), '확인')]"),
                    (By.XPATH, "//button[contains(text(), '결제')]"),
                    (By.XPATH, "//input[@value='확인']"),
                    (By.XPATH, "//input[@value='결제']"),
                ]
            )
            time.sleep(3)

            # 메인 창으로 복귀
            if len(self.driver.window_handles) > 0:
                self.driver.switch_to.window(self.driver.window_handles[0])

        # iframe 처리
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                if any(
                    keyword in src.lower()
                    for keyword in ["pay", "pg", "inicis", "kcp", "nice"]
                ):
                    self.driver.switch_to.frame(iframe)
                    logger.debug(f"결제 iframe 전환: {src}")

                    self._find_and_click(
                        [
                            (By.XPATH, "//button[contains(text(), '확인')]"),
                            (By.XPATH, "//button[contains(text(), '결제')]"),
                        ]
                    )
                    time.sleep(2)

                    self.driver.switch_to.default_content()
                    break
        except Exception as e:
            logger.debug(f"iframe 처리 건너뜀: {e}")
            self.driver.switch_to.default_content()

    # ──────────────────────────────────────────────────────────
    # 3. 계좌이체 결제 (수동 보조)
    # ──────────────────────────────────────────────────────────

    def _pay_with_transfer(self):
        """계좌이체로 결제한다 (수동 개입 필요).

        계좌이체는 은행 보안 앱 인증이 필요하므로
        결제 화면까지 자동 이동 후 사용자에게 수동 결제를 요청한다.
        """
        try:
            self._wait_for_payment_page()

            # '계좌이체' 선택
            transfer_option = self._find_and_click(
                [
                    (By.XPATH, "//label[contains(text(), '계좌이체')]"),
                    (By.XPATH, "//input[@value='transfer']"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='BANK']"),
                    (By.CSS_SELECTOR, "input[name='payMethod'][value='bank']"),
                ]
            )
            if not transfer_option:
                logger.warning("계좌이체 옵션을 찾을 수 없습니다.")

            logger.info("계좌이체 결제 화면입니다. 수동으로 결제를 완료해 주세요.")
            input(">> 결제 완료 후 Enter를 눌러주세요... ")

            if self._verify_payment_success():
                logger.info("계좌이체 결제 확인")
                return True
            else:
                # 사용자가 완료했다고 했으므로 True 반환
                logger.info("결제 완료로 간주합니다.")
                return True

        except Exception as e:
            logger.error(f"계좌이체 결제 실패: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # 공통 유틸리티
    # ──────────────────────────────────────────────────────────

    def _wait_for_payment_page(self):
        """결제 페이지/팝업이 로드될 때까지 대기한다."""
        time.sleep(2)

        # 새 창이 열렸는지 확인
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            logger.debug("결제 팝업 창 감지, 전환 완료")
            time.sleep(2)

    def _find_element(self, locators):
        """여러 로케이터 중 첫 번째로 찾은 요소를 반환한다.

        Args:
            locators: list of (By, selector) tuples

        Returns:
            WebElement 또는 None
        """
        for by, selector in locators:
            try:
                elem = self.driver.find_element(by, selector)
                if elem.is_displayed():
                    return elem
            except NoSuchElementException:
                continue
        return None

    def _find_and_click(self, locators):
        """여러 로케이터 중 첫 번째로 찾은 요소를 클릭한다.

        Returns:
            bool: 클릭 성공 여부
        """
        elem = self._find_element(locators)
        if elem:
            try:
                elem.click()
                return True
            except Exception:
                # JavaScript 클릭 폴백
                try:
                    self.driver.execute_script("arguments[0].click();", elem)
                    return True
                except Exception as e:
                    logger.debug(f"클릭 실패: {e}")
        return False

    def _click_pay_button(self):
        """결제 실행 버튼을 클릭한다."""
        time.sleep(1)
        clicked = self._find_and_click(
            [
                (By.XPATH, "//button[contains(text(), '결제하기')]"),
                (By.XPATH, "//button[contains(text(), '결제')]"),
                (By.XPATH, "//input[@value='결제하기']"),
                (By.XPATH, "//input[@value='결제']"),
                (By.XPATH, "//a[contains(text(), '결제하기')]"),
                (By.XPATH, "//button[contains(text(), '결제 요청')]"),
                (By.CSS_SELECTOR, "button.pay-btn, button.btn-pay"),
                (By.CSS_SELECTOR, "input[type='submit'][value*='결제']"),
            ]
        )
        if clicked:
            logger.debug("결제 버튼 클릭 완료")
            time.sleep(3)
            return True
        else:
            logger.error("결제 버튼을 찾을 수 없습니다.")
            return False

    def _handle_confirm_dialogs(self):
        """결제 후 확인 알림(alert)과 팝업을 처리한다."""
        # JavaScript alert 처리
        for _ in range(3):
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logger.debug(f"알림 메시지: {alert_text}")
                alert.accept()
                time.sleep(1)
            except NoAlertPresentException:
                break

        # 확인 버튼 팝업 처리
        self._find_and_click(
            [
                (By.XPATH, "//button[contains(text(), '확인')]"),
                (By.XPATH, "//input[@value='확인']"),
            ]
        )
        time.sleep(2)

        # 팝업 창이 닫히고 메인 창으로 돌아왔는지 확인
        windows = self.driver.window_handles
        if len(windows) >= 1:
            self.driver.switch_to.window(windows[0])

    def _verify_payment_success(self):
        """결제 성공 여부를 확인한다.

        Returns:
            bool: 결제 성공 여부
        """
        time.sleep(2)

        # 성공 메시지 확인
        success_indicators = [
            "결제가 완료",
            "결제 완료",
            "정상적으로 처리",
            "발급이 완료",
            "열람이 완료",
            "처리되었습니다",
        ]

        try:
            page_source = self.driver.page_source
            for indicator in success_indicators:
                if indicator in page_source:
                    logger.debug(f"결제 성공 확인: '{indicator}' 발견")
                    return True
        except Exception:
            pass

        # 실패 메시지 확인
        failure_indicators = [
            "결제 실패",
            "잔액 부족",
            "한도 초과",
            "카드 오류",
            "거래가 거절",
        ]

        try:
            page_source = self.driver.page_source
            for indicator in failure_indicators:
                if indicator in page_source:
                    logger.error(f"결제 실패 감지: '{indicator}'")
                    return False
        except Exception:
            pass

        # 명확한 성공/실패 신호가 없으면 True (다운로드 단계에서 재확인)
        logger.debug("결제 상태 불명확 - 다음 단계에서 확인")
        return True


class InsufficientBalanceError(Exception):
    """선불전자지급수단 잔액 부족 예외"""
    pass
