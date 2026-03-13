"""인터넷등기소(iros.go.kr) 등기부등본 자동 발급 모듈

Selenium을 사용하여 인터넷등기소에서 등기부등본을 자동으로 발급/다운로드합니다.

※ 주의사항:
  - 인터넷등기소 로그인이 필요합니다 (공인인증서 또는 간편인증).
  - 등기부등본 발급은 유료입니다 (열람 700원, 발급 1,000원).
  - 사이트 구조 변경 시 셀렉터 업데이트가 필요할 수 있습니다.
"""

import os
import re
import time
import glob
import shutil
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config

logger = logging.getLogger(__name__)


class IrosAutomation:
    """인터넷등기소 자동화 클래스"""

    def __init__(self, download_dir=None, headless=None):
        self.download_dir = os.path.abspath(download_dir or config.DOWNLOAD_DIR)
        self.headless = headless if headless is not None else config.HEADLESS
        self.driver = None

        # 다운로드 폴더 생성
        os.makedirs(self.download_dir, exist_ok=True)

    def _create_driver(self):
        """Chrome WebDriver를 생성한다."""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # 다운로드 경로 설정
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(5)

    def start(self):
        """브라우저를 시작하고 인터넷등기소에 접속한다."""
        logger.info("브라우저 시작 중...")
        self._create_driver()
        logger.info("인터넷등기소 접속 중...")
        self.driver.get(config.IROS_BASE_URL)
        time.sleep(3)

    def login(self, user_id=None, user_pw=None):
        """인터넷등기소에 로그인한다.

        ※ 인터넷등기소는 공인인증서/간편인증(카카오, PASS 등)으로
           로그인해야 합니다. ID/PW 로그인의 경우 아래 로직을 사용합니다.
           공인인증서 로그인은 수동 개입이 필요합니다.
        """
        uid = user_id or config.IROS_USER_ID
        upw = user_pw or config.IROS_USER_PW

        if not uid or not upw:
            logger.warning(
                "로그인 정보가 없습니다. 수동 로그인 후 Enter를 눌러주세요."
            )
            input(">> 브라우저에서 로그인 완료 후 Enter를 눌러주세요... ")
            return True

        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            # 로그인 페이지 이동
            self.driver.get(config.IROS_LOGIN_URL)
            time.sleep(2)

            # ID 입력
            id_input = wait.until(
                EC.presence_of_element_located((By.ID, "userId"))
            )
            id_input.clear()
            id_input.send_keys(uid)

            # PW 입력
            pw_input = self.driver.find_element(By.ID, "userPw")
            pw_input.clear()
            pw_input.send_keys(upw)

            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, "loginBtn")
            login_btn.click()
            time.sleep(3)

            logger.info("로그인 완료")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"로그인 실패: {e}")
            logger.info("수동 로그인이 필요합니다.")
            input(">> 브라우저에서 로그인 완료 후 Enter를 눌러주세요... ")
            return True

    def navigate_to_issue_page(self):
        """부동산등기 열람/발급 페이지로 이동한다."""
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            # 열람/발급 메뉴로 이동
            # ※ 인터넷등기소 메뉴 구조에 따라 셀렉터 조정 필요
            self.driver.get(
                f"{config.IROS_BASE_URL}/PMainJ.jsp"
            )
            time.sleep(2)

            # "부동산" 탭 클릭
            realty_tab = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), '부동산')]")
                )
            )
            realty_tab.click()
            time.sleep(1)

            # "열람하기" 또는 "발급하기" 클릭
            if config.ISSUE_MODE == "view":
                btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//a[contains(text(), '열람하기')]")
                    )
                )
            else:
                btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//a[contains(text(), '발급하기')]")
                    )
                )
            btn.click()
            time.sleep(2)

            logger.info("열람/발급 페이지 이동 완료")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"페이지 이동 실패: {e}")
            return False

    def search_by_property_id(self, property_id):
        """부동산고유번호로 등기부를 검색한다.

        Args:
            property_id: 부동산고유번호 (하이픈 없이 13자리 또는 14자리)
        """
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            # 고유번호 검색 탭 선택
            unique_tab = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), '고유번호')]")
                )
            )
            unique_tab.click()
            time.sleep(1)

            # 고유번호를 4-4-6 형식으로 분할 (예: 1234-5678-901234)
            # 인터넷등기소는 고유번호를 3개 필드로 나누어 입력받음
            part1 = property_id[:4]
            part2 = property_id[4:8]
            part3 = property_id[8:]

            # 입력 필드 찾기 및 입력
            # ※ 실제 셀렉터는 사이트 구조에 따라 조정 필요
            fields = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='text'][maxlength]"
            )

            # 고유번호 입력 필드가 3개일 경우
            if len(fields) >= 3:
                for field in fields[:3]:
                    field.clear()
                fields[0].send_keys(part1)
                fields[1].send_keys(part2)
                fields[2].send_keys(part3)
            else:
                # 단일 입력 필드일 경우
                search_input = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input.search-input, input#uniqueNo")
                    )
                )
                search_input.clear()
                search_input.send_keys(property_id)

            # 검색 버튼 클릭
            search_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), '검색')]"
                     " | //input[@value='검색']"
                     " | //a[contains(text(), '검색')]")
                )
            )
            search_btn.click()
            time.sleep(3)

            logger.info(f"고유번호 [{property_id}] 검색 완료")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"검색 실패 [{property_id}]: {e}")
            return False

    def select_cert_type(self):
        """등기부등본 유형을 선택한다 (전부사항/현재유효사항)."""
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            if config.CERT_TYPE == "full":
                # 전부사항 증명서 선택
                cert_radio = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//label[contains(text(), '전부')]"
                         " | //input[@value='full']")
                    )
                )
            else:
                # 현재유효사항 증명서 선택
                cert_radio = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//label[contains(text(), '현재유효')]"
                         " | //input[@value='current']")
                    )
                )
            cert_radio.click()
            time.sleep(1)
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"증명서 유형 선택 실패 (기본값 사용): {e}")
            return True  # 기본값으로 진행

    def request_issue(self):
        """등기부등본 열람/발급을 요청한다."""
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            # 열람/발급 요청 버튼 클릭
            if config.ISSUE_MODE == "view":
                issue_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//button[contains(text(), '열람')]"
                         " | //a[contains(text(), '열람하기')]"
                         " | //input[@value='열람하기']")
                    )
                )
            else:
                issue_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//button[contains(text(), '발급')]"
                         " | //a[contains(text(), '발급하기')]"
                         " | //input[@value='발급하기']")
                    )
                )
            issue_btn.click()
            time.sleep(2)

            # 결제 확인 팝업 처리
            try:
                confirm_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//button[contains(text(), '확인')]"
                         " | //input[@value='확인']")
                    )
                )
                confirm_btn.click()
                time.sleep(3)
            except TimeoutException:
                pass  # 확인 팝업이 없을 수 있음

            logger.info("발급 요청 완료")
            return True

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"발급 요청 실패: {e}")
            return False

    def download_pdf(self, property_id):
        """발급된 등기부등본 PDF를 다운로드하고 파일명을 변경한다.

        Args:
            property_id: 부동산고유번호 (파일명으로 사용)

        Returns:
            str: 저장된 파일 경로 또는 None
        """
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)

            # 다운로드 전 기존 파일 목록 기록
            existing_files = set(glob.glob(os.path.join(self.download_dir, "*")))

            # PDF 다운로드/인쇄 버튼 클릭
            download_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(text(), '다운로드')]"
                     " | //a[contains(text(), '저장')]"
                     " | //button[contains(text(), '인쇄')]"
                     " | //a[contains(@href, 'download')]")
                )
            )
            download_btn.click()

            # 다운로드 완료 대기 (최대 30초)
            downloaded_file = self._wait_for_download(existing_files, timeout=30)

            if downloaded_file:
                # 파일명을 부동산고유번호로 변경
                new_filename = f"{property_id}.pdf"
                new_filepath = os.path.join(self.download_dir, new_filename)

                # 동일 파일이 존재하면 덮어쓰기
                if os.path.exists(new_filepath):
                    os.remove(new_filepath)

                shutil.move(downloaded_file, new_filepath)
                logger.info(f"파일 저장 완료: {new_filepath}")
                return new_filepath
            else:
                logger.error("다운로드 파일을 찾을 수 없습니다.")
                return None

        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"다운로드 실패: {e}")
            return None

    def _wait_for_download(self, existing_files, timeout=30):
        """새 파일이 다운로드될 때까지 대기한다.

        Args:
            existing_files: 다운로드 전 기존 파일 set
            timeout: 최대 대기 시간 (초)

        Returns:
            str: 다운로드된 파일 경로 또는 None
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            current_files = set(glob.glob(os.path.join(self.download_dir, "*")))
            new_files = current_files - existing_files

            # .crdownload (Chrome 임시 파일) 제외
            completed_files = [
                f for f in new_files
                if not f.endswith(".crdownload") and not f.endswith(".tmp")
            ]

            if completed_files:
                return completed_files[0]

            time.sleep(1)

        return None

    def process_single(self, property_id):
        """단일 부동산고유번호에 대해 등기부등본을 발급한다.

        Args:
            property_id: 부동산고유번호

        Returns:
            bool: 성공 여부
        """
        logger.info(f"처리 시작: {property_id}")

        for attempt in range(config.MAX_RETRIES + 1):
            try:
                # 1. 열람/발급 페이지 이동
                if not self.navigate_to_issue_page():
                    continue

                # 2. 고유번호 검색
                if not self.search_by_property_id(property_id):
                    continue

                # 3. 증명서 유형 선택
                self.select_cert_type()

                # 4. 발급 요청
                if not self.request_issue():
                    continue

                # 5. PDF 다운로드 및 파일명 변경
                filepath = self.download_pdf(property_id)
                if filepath:
                    logger.info(f"발급 성공: {property_id} → {filepath}")
                    return True

            except WebDriverException as e:
                logger.error(
                    f"시도 {attempt + 1}/{config.MAX_RETRIES + 1} 실패: {e}"
                )
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY)

        logger.error(f"발급 최종 실패: {property_id}")
        return False

    def close(self):
        """브라우저를 종료한다."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("브라우저 종료")
