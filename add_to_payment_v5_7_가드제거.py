#!/usr/bin/env python3
"""인터넷등기소 부동산 등기부등본 결제대상 자동 추가 + 일괄결제·열람·저장 프로그램 v5.7

변경사항 (v5.7 from v5.6):
  - [정리] click_batch_save_with_verify() 내부의 "일괄저장 클릭 직전 가드"
           블록 제거.
      · 배경: v5.5 도입 당시 보수적 이중 안전망으로 추가했던 부분. 매 저장
        클릭 시도 직전에 _detect_pending_case_modal() 로 모달 잔존 여부를
        검사하고, 떠있으면 짧게(3회) 닫기를 시도하던 코드였음.
      · 제거 이유: 사이클의 [단계 2] _handle_pending_case_popup() 본 호출이
        이미 다음을 모두 보장:
          - DOM 모달이 사라질 때까지 능동 폴링 (close_wait=2초)
          - 사라진 직후 1.5초간 재발 감시 (recheck_wait)
          - 최대 10회 반복 (max_close_attempts=10, v5.6)
        본 호출이 정상 종료된 시점에는 "팝업이 닫혀있고 1.5초 동안 재등장하지
        않았음" 이 검증된 상태이므로, 그 직후 100ms 이내 시점에 다시 떠오를
        확률은 사실상 0. 가드가 실제로 발동할 시나리오가 거의 없으며, 매
        저장 클릭마다 미세한 오버헤드만 발생.
      · 만약 가드가 진짜로 무언가 잡아낸다면 그것은 본 호출이 막지 못한
        비정상 상황이라는 신호이고, 한 번 더 닫는다고 해결될 일이 아님
        (드라이버/페이지 자체에 문제가 있는 케이스).
      · 결과: 본 호출(_handle_pending_case_popup) 이 변경 예정 팝업 처리의
        단일 책임 지점이 됨. 코드가 더 명확해지고 정상 사이클 미세하게 빨라짐.
      - 그 외 모든 동작(Phase 1/2/3/4, --start-from 의미, 일괄저장 버튼,
        팝업 워치독, 점진적 회피, 다운로드 검증, 변경 예정 안내 팝업 본
        호출 등) 은 v5.6 과 완전히 동일.

변경사항 (v5.6 from v5.5):
  - [정리] 사이클에서 handle_batch_view_confirm_popup() 호출 제거.
      · 배경: 이 함수는 본문 식별 없이 페이지 전체에서 텍스트가 '확인' 인
        첫 번째 보이는 버튼을 무조건 클릭하던 함수였음. v5.5 에서 변경
        예정 안내 팝업 처리를 본문 식별 기반의 _handle_pending_case_popup
        ()으로 정확하게 옮긴 뒤에는, 이 함수가 처리중 바가 사라지기도
        전인 시점에 호출되어 진짜 변경 예정 팝업과는 무관한 다른 '확인'
        버튼을 헛클릭하고 있을 가능성이 컸음. 매 사이클 동일한 헛클릭이
        무해하게 발생하다가, 드물게 잘못된 버튼을 눌러 흐름이 어긋날
        위험이 있어 호출 자체를 제거.
      · 함께 짝이었던 _wait_until_modal_dismissed(max_wait=3.0) 도 같이
        제거. 어차피 바로 다음 단계의 _wait_until_processbar_gone() 가
        더 정확한 능동 대기를 수행하므로 손실 없음.
      · native alert 안전망은 사이클의 다른 _handle_alert(accept=True)
        호출이 그대로 담당하므로 회귀 위험 없음.
      · 함수 정의 자체는 코드에 남겨둠 (다른 경로에서 참조될 가능성 +
        롤백 용이성).
  - [개선] 로그 라벨 '[처리중 안내 팝업]' → '[변경 예정 안내 팝업]' 으로
           변경. 실제 팝업 본문 ("등기신청사건이 접수되어, 등기기록상에
           변경이 있을 예정입니다") 의 의미와 일치시켜 가독성 향상.
  - [개선] 변경 예정 안내 팝업 닫기 최대 시도 5회 → 10회 로 상향.
           연쇄로 떠오르는 케이스를 더 폭넓게 흡수.
      - 그 외 모든 동작(Phase 1/2/3/4, --start-from 의미, 일괄저장 버튼,
        팝업 워치독, 점진적 회피, 다운로드 검증 등) 은 v5.5 와 완전히 동일.

변경사항 (v5.5 from v5.4):
  - [수정] 일괄열람 → 일괄저장 단계의 안정성 강화. 처리중 팝업이 떴는데
           닫히지 않아 저장 클릭이 모두 흡수되어 ZIP 누락이 발생하던 사고
           해결.
      · 사고 재현: 100건 사이클에서 '등기신청사건이 접수되어, 등기기록상에
        변경이 있을 예정입니다' 확인 팝업이 떴음에도 _handle_pending_case_
        popup() 이 감지/처리 못하고 통과 → 그 위에서 일괄저장 클릭이 모달에
        흡수 → 3회 모두 다운로드 시작 안 됨 → 사이클 ZIP 누락.
      · 사용자 제안 3단계 사양으로 재설계:
          1) 일괄열람 클릭 후 '처리 중입니다.' 진행바(div[id*=processbar])
             가 화면에서 완전히 사라질 때까지 대기.
          2) 처리중 변경 안내 팝업 ('등기신청사건이 접수되어...') 을 본문
             문구 기반으로 정확히 감지하여 확인 버튼 클릭.
          3) 팝업이 DOM 상에서 완전히 사라진 것을 확인한 뒤 일괄저장 클릭.
      · 신규 메서드:
          - _wait_until_processbar_gone(max_wait=20): 처리중 바가 사라질
            때까지 0.2초 주기 폴링. 등기소 서버 응답 지연을 흡수.
          - _detect_pending_case_modal(): DOM 에서 처리중 안내 모달이
            현재 떠있는지 본문 문구로 확인. (등기신청사건이 접수, 변경 사항이
            반영, 출력을 원하지 않으면 등 키워드 중 하나라도 매치)
      · _handle_pending_case_popup() 재작성: 즉시 DOM 검사 → 미감지면 짧게
        (1초) 추가 폴링 → 발견 시 확인 클릭 → 닫힘 확인 → 1.5초 재발 감시
        (연쇄 팝업 대비 최대 5회 반복). 정상 사이클(처리중 건 없음) 은
        약 1초만 소요됨 (v5.4 까지는 alert 대기 3초 강제 낭비).
      · click_batch_save_with_verify(): max_attempts 기본값 3 → 10 으로
        상향. 매 클릭 직전 _detect_pending_case_modal() 가드 추가 (모달이
        다시 떠있으면 한 번 더 닫고 진행).
      - 그 외 모든 동작(Phase 1/2/3/4, --start-from 의미, 일괄저장 버튼,
        팝업 워치독, 점진적 회피, 오버레이 폭 등) 은 v5.4 와 완전히 동일.

변경사항 (v5.4 from v5.3):
  - [신규] 일괄저장 단계에 다운로드 검증 + 자동 재시도 로직 추가.
      · 배경: v5.3 까지 click_batch_save() 는 버튼 클릭 후 time.sleep(3)
        만 하고 닫기 단계로 넘어갔음. 클릭이 안 먹은 경우에도 감지 못 해
        해당 사이클의 ZIP 파일(등기부등본 10개 분량) 이 영구 누락되는
        사고가 발생.
      · 동작: 일괄저장 클릭 후 다운로드 폴더 (C:\\Users\\Administrator\\
        Downloads) 를 폴링하여 다음을 단계적으로 확인:
          - 1단계 (최대 3초, 0.3초 주기): 사이클 시작 이후 새로 생성된
            '부동산일괄저장*.zip' 또는 그 .crdownload 가 나타날 때까지 대기.
            → 안 나타나면 클릭이 안 먹은 것으로 판단, 즉시 재클릭.
          - 2단계 (최대 5초, 0.3초 주기): .crdownload 가 사라지고 정상
            .zip 파일이 완성될 때까지 대기.
            → 완료되면 닫기 진행. 타임아웃이면 경고 로그 후 닫기 진행.
        최대 3회까지 재시도. 3회 모두 실패하면 경고를 남기고 다음 사이클로
        진행 (현재 동작과 동일).
      · 정상 환경 영향: 10건 ZIP 은 보통 1~2초 내 다운로드 완료되므로
        기존 sleep(3) 대비 사이클당 1~2초 빨라짐. 클릭 미작동 케이스만
        +3~9초 추가되며, 이 경우는 오히려 누락을 방지하는 가치가 큼.
      · 식별 기준: 사이클 시작 시각 (start_time) 이후의 mtime 을 가진
        '부동산일괄저장*.zip[.crdownload]' 파일만 새 파일로 인정.
      · 폴백: 다운로드 폴더에 접근 못 하면 기존 sleep(3) 동작으로 폴백
        하여 동작 자체는 보장.
  - [개선] 진행상황 오버레이 폭을 600 → 500 으로 축소.
      · 동시에 일부 상태문/버튼 라벨을 짧게 정리하여 새 폭에 잘리지 않도록
        함. 주요 변경:
        - 일괄저장 시작 버튼: '▶▶ 일괄저장 시작' → '▶▶ 일괄저장'
        - 팝업 누적+휴식 안내: '⚠ OS 팝업 자동 닫음 N회 — 다음 건 시작 전
          휴식 예정 (M회 대기)' → '⚠ OS 팝업 N회 — 휴식 대기 M회'
        - 휴식 진행 표시: '⏸ 보안 모듈 회복 대기 N초 (남은 회분 M회)' →
          '⏸ 휴식 N초 (남은 M회)'
        - 종료 안내: '— 엔터를 누르면 창이 닫힙니다' → '— 엔터로 닫기'
        - Phase 2 안내·cmd 출력: '▶▶ 일괄저장 시작 버튼' → '▶▶ 일괄저장
          버튼' 으로 통일
      - 그 외 모든 동작(Phase 1/2/3/4, --start-from 의미, 일괄저장 버튼,
        팝업 워치독, 점진적 회피 등) 은 v5.3 과 완전히 동일.

변경사항 (v5.3 from v5.2):
  - [수정] --start-from 옵션의 의미를 직관적인 1-based "N번째 건부터 시작"
           으로 변경 (기존: "N건을 건너뛰기").
      · 배경: v5.2 까지 --start-from N 은 0-based skip 의미였음. 즉
        --start-from 112 = "112건 건너뛰고 113번째부터" 였음. 그러나
        진행상황 로그·오버레이는 모두 1-based ([112/135]) 로 표시되어
        사용자가 "112번째 건부터" 라는 의도로 --start-from 112 를 주면
        실제로는 113번째부터 처리되며, 추가로 verify_payment_count() 의
        expected 가 start_offset+idx+1 로 계산되어 결제대상 첫 건의
        예상값이 113 으로 잡혀 건수 불일치 재시도가 유발됨. 결과적으로
        112번째 건이 영영 누락되고 첫 건마다 재시도 1회씩 낭비됨.
      · 변경: --start-from N (N>=1) = "N번째 건부터 처리". 로그 표시와
        의미가 1:1 일치. 옵션 미지정 / --start-from 0 / --start-from 1
        은 모두 "처음부터" 와 동일하게 동작 (하위 호환).
      · 영향 라인:
        - items[start_offset:] → items[max(start_offset-1, 0):]
        - expected = start_offset + idx + 1 → expected = max(start_offset, 1) + idx
        - resume_from = start_offset + idx → resume_from = max(start_offset, 1) + idx
      · 마이그레이션: 기존에 "111건 완료 후 112번째부터 재개"하려면
          v5.2: --start-from 111
          v5.3: --start-from 112
        실패 시 코드가 출력하는 재개 명령은 새 의미로 자동 계산되므로
        그대로 복사해 쓰면 됨.
      - 그 외 모든 동작(Phase 1/2/3/4, 일괄저장 버튼, 팝업 워치독,
        점진적 회피, 일시정지/중단 등) 은 v5.2 와 완전히 동일.

변경사항 (v5.2 from v5.1):
  - [신규] Windows '응용 프로그램 오류' 팝업 자동 닫기 워치독 + 점진적 회피.
      · 배경: 등기소가 강제하는 네이티브 보안 모듈(V3 / nxKey / INISAFE 등)
        이 빠른 페이지 전환 누적으로 access violation 크래시를 일으키면
        Windows 가 0x... 메모리 참조 오류 팝업(WerFault) 을 띄움.
        이 팝업은 OS 모달이라 페이지 재접속·드라이버 재시작으로 사라지지
        않고, 사용자가 직접 '확인' 을 누를 때까지 남아 다른 클릭을 가로막음.
      · 동작 1 (자동 닫기): 별도 데몬 스레드 (PopupWatcher) 가 5초 주기로
        Win32 EnumWindows 폴링. 클래스 '#32770' (다이얼로그) 중 제목에
        '응용 프로그램 오류' / 'Application Error' 가 포함된 창만 화이트
        리스트로 한정해 닫음. 일반 작업 다이얼로그·등기소 알림 등은
        절대 건드리지 않음.
      · 동작 2 (점진적 회피): 팝업이 1회만 발생하면 일시적 사고로 간주하고
        그대로 진행. 2회 이상부터는 "보안 모듈에 누적 부하가 쌓이고 있다"
        고 판단, "다음 건 시작 직전에 10초 휴식 1회분" 을 부과. 매 발생
        마다 휴식 1회분이 추가됨 (예: 4회 발생 = 다음 3개 건 시작 전에
        각 10초 휴식). 한 번 휴식을 부여하면 해당 회분은 소비됨.
      · 안전성: 닫기 전 창 제목과 본문 텍스트를 logger.warning 으로 기록
        하여 사후 추적 가능. '확인'/'OK'/'예'/'Yes' 버튼이 보이면
        BM_CLICK 메시지, 못 찾으면 WM_CLOSE 폴백. 휴식은 PauseController.
        sleep() 으로 들어가 중단/일시정지에도 정상 반응.
      · 모니터링: 오버레이 상태줄에 누적 닫힘 횟수(⚠ OS 팝업 자동 닫음 N회)
        를 노출. 작업 종료 시 총 닫음 횟수 + 부여/소비된 휴식 횟수를
        요약 로그로 출력.
      · 플랫폼: Windows 전용. macOS/Linux 에서는 자동으로 비활성화되어
        본 작업에는 어떤 영향도 없음.
      - 그 외 모든 동작(Phase 1/2/3/4, 일괄저장 버튼, 일시정지/중단,
        오버레이 로그/진행률 등) 은 v5.1 과 완전히 동일하게 유지.

변경사항 (v5.1 from v5.0):
  - [개선] Phase 2 → Phase 3 진입 트리거를 cmd 창 엔터 입력에서 오버레이의
           '▶▶ 일괄저장 시작' 버튼 클릭으로 변경.
      · 기존: 일괄결제(Phase 2) 후 수동 결제를 마친 사용자가 cmd 창에 포커스를
        옮긴 뒤 Enter 키를 눌러야 일괄열람/저장(Phase 3) 이 개시되었음.
        cmd 창이 다른 창들에 가려져 있거나 포커스를 다시 잡기 번거로워 흐름이
        끊기는 문제가 있었음.
      · 수정: 진행상황 오버레이의 제어 버튼 영역에 '▶▶ 일괄저장 시작' 버튼을
        추가. 평소에는 비활성(회색) 상태이며, Phase 2 진입 시점 (수기 결제 대기
        상태) 에 자동으로 활성화(녹색 강조) 됨. 사용자가 결제 완료 후 이 버튼을
        클릭하면 즉시 Phase 3 (일괄열람/저장) 가 개시됨.
      · wait_for_manual_payment() 가 input() 대신 PauseController 의
        wait_for_batch_save() 를 호출하도록 변경. 내부적으로 threading.Event
        기반으로 동작하며 '중단' 버튼도 대기 중 정상 반응 (StopRequested).
      · 오버레이를 사용할 수 없는 환경(Tkinter 비활성) 에서는 자동으로
        기존 input() 입력 방식으로 폴백 → 어떤 환경에서도 동작 보장.
      - 일괄저장 버튼은 클릭 후 다시 비활성화 (이중 클릭 방지).
      - 그 외 모든 동작(Phase 1/2/3/4, 일시정지/중단, 오버레이 로그/진행률 등)
        은 v5.0 과 완전히 동일하게 유지.

변경사항 (v5.0 from v4.9):
  - [개선] 폐쇄 고유번호 즉시 저장 (작업 중단 대비).
      · 기존: Phase 1 종료 후에야 closed_YYYYMMDD_HHMMSS.txt 를 작업 폴더에
        한 번에 저장 → 사용자가 중간에 중단/오류 발생 시 어떤 고유번호가
        폐쇄였는지 영영 알 수 없었음.
      · 수정: 첫 폐쇄 감지 시점에 바탕화면(Desktop)에 'YYYYMMDD' 폴더를
        만들고(이미 있으면 그대로 사용), 그 안에 '폐쇄고유번호_YYYYMMDD_
        HHMMSS.txt' 파일을 즉시 생성. 이후 폐쇄가 추가될 때마다 같은
        파일에 한 줄씩 append. 파일 핸들은 매 추가마다 열고-쓰고-flush
        -close 하므로 강제 종료가 발생해도 직전까지 기록된 항목은 안전
        하게 디스크에 남음.
      · 폴더명을 'YYYYMMDD' 로 통일하여 Phase 4 의 일괄열람/저장 ZIP
        압축해제 결과물(바탕화면/YYYYMMDD)과 같은 폴더에 모이도록 함.
        결과적으로 작업이 끝나면 바탕화면/20260428 안에 폐쇄목록 텍스트
        파일과 등기부등본 PDF 들이 한 곳에 정리됨.
      · Phase 1 종료 후 표시되는 "★★★ 폐쇄 고유번호를 확인하세요 ★★★"
        알림은 기존과 동일하게 유지 (사용자 흐름 변경 없음).
      · save_closed_items() 는 호환성을 위해 유지하되, 이미 즉시 저장된
        파일이 있으면 그 파일 경로를 그대로 반환 (중복 저장 방지).
      · 바탕화면 접근 실패 시(권한/OneDrive 리다이렉트 등) 작업 폴더를
        폴백 위치로 사용 → 어떤 환경에서도 폐쇄 목록은 반드시 남도록 보장.

변경사항 (v4.9 from v4.8):
  - [수정] 결제대상 추가 직후 '0건 ≠ 예상 N건' 건수 불일치로 불필요한 재시도가
           발생하던 문제 해결.
      · 원인: verify_payment_count() 가 is_payment_target_page() 통과 즉시
        _extract_payment_count() 를 1회 호출하고 결과가 0건이어도 그대로 False
        를 반환했음. 페이지 골격(제목/일괄결제 버튼)은 빨리 로드되지만 표 안의
        데이터 행이 채워지기 전 시점에 추출하면 '전체 0건' 이 잡힘.
        결과적으로 1차에서는 사실상 추가 성공했는데 0건으로 오판 → 재시도 →
        2차에서 중복결제로 응답 → '중복결제 확인 기준 성공' 으로 우회 처리되어
        겉보기엔 동작하지만 매 항목마다 1회씩 추가 라운드가 발생.
        v4.7 시절에는 같은 0건 오판 후 재시도 시 중복결제 페이지를 못 잡아
        무한 재시도로 빠졌기 때문에 0건 이슈 자체는 같은 뿌리지만 표면 증상이
        달랐음 (v4.8 이 중복결제를 잘 잡으면서 숨어있던 버그가 드러남).
      · 수정: verify_payment_count 를 폴링 기반으로 재작성.
          - 0건/미달이 추출되어도 즉시 실패하지 않고 timeout(12s) 까지 0.5s
            간격으로 다시 검사.
          - DOM 테이블의 실제 데이터 행수도 동시에 카운트하여 텍스트 카운트와
            교차 검증 (_count_payment_rows_in_table 추가).
          - 텍스트 카운트가 expected 와 일치하더라도 DOM 행수가 부족하면
            잠깐 더 기다린 뒤 통과시킴 (반대 방향 동기화 지연 방지).

변경사항 (v4.8 from v4.7):
  - [수정] 유형선택 '다음' 클릭 후 중복결제 페이지를 놓치고 '다음' 버튼을 눌러
           중복하여 결제대상에 추가되거나 빈 화면으로 빠지던 문제 해결.
      · 원인: v4.7 의 분기 판별이 click_next_button 직후 즉시 1회만 호출되어
        서버 응답이 느릴 때는 페이지가 아직 렌더되지 않아 'duplicate'/'pending'
        모두 false 로 떨어지고 곧바로 최종확인 '다음' 이 클릭되어 중복결제
        페이지의 파란색 '다음' 버튼을 눌러버림 (안내문상 '중복하여 열람·발급').
      · 수정: 3가지 분기 페이지의 고유 키워드를 기준으로 결정적 폴링 판별을
        수행하는 wait_for_branch_after_type_next() 도입.
          - 중복결제   : '중복결제 확인' (제목)
          - 신청사건   : '등기신청사건 처리여부 확인' / '신청사건 처리중인 등기부'
          - 정상       : '(주민)등록번호 공개여부 확인' / '미공개' + '특정인공개'
        세 키워드 중 하나가 본문에 나타날 때까지 최대 BRANCH_DETECT_TIMEOUT
        초간 폴링. 셋 다 나타나지 않으면 None 반환 → 재시도.
      · 추가로 alert 형태로 뜨는 중복결제/이미결제 안내도 폴링 루프 안에서
        함께 잡도록 보강.

변경사항 (v4.7 from v4.6):
  - [수정] Phase 1 단계에서 '최초 건' 이 결제대상에 중복 추가되던 문제 해결.
      · 원인: 유형선택 '다음' 클릭 후 중복결제 확인 페이지를 즉시 1회만 체크하고
        곧바로 최종확인 '다음' 을 눌렀기 때문. 로그인 직후 세션 웜업으로 서버
        응답이 느릴 때는 중복결제 페이지가 아직 렌더되지 않아 감지를 놓치고,
        결과적으로 같은 고유번호가 결제대상에 2건으로 중복 추가됨.
      · 추가로 '결제대상 미도달(단기 3초) → 다음(추가) 강제 클릭' 우회 로직이
        중복결제 페이지를 덜 렌더된 상태에서 밀어버려 같은 증상을 가중시킴.
      · 수정: 유형선택 '다음' 클릭 후 분기 가능한 3가지 경우를 결정적으로 판별
        (정상 최종확인 / 중복결제 확인 / 신청사건 처리중). QUICK_PAYMENT_PAGE
        _WAIT_TIMEOUT(3초) 기반의 추측성 우회 로직 제거.

  - [추가] '신청사건 처리중인 등기부' 화면 자동 감지 및 통과 처리.
      · 유형선택 '다음' 클릭 후 '등기신청사건 처리여부 확인' / '신청사건 처리중'
        문구가 감지되면 다음 한 번 더 클릭하여 정상 최종확인 흐름으로 복귀.
      · 기존에는 이 화면을 능동적으로 판별하지 않고 '결제대상 미도달 →
        우회 클릭' 로직으로 어거지로 통과시켜서 불안정했음.

변경사항 (v4.6 from v4.5):
  - [추가] 오버레이 제어 버튼: ⏸ 일시정지 / ▶ 재개 / ⏹ 중단.
      · PauseController (threading.Event 기반) 로 메인 스레드와 안전하게 통신.
      · 체크포인트 위치: Phase 1 건 경계, Phase 1 라운드 쿨다운 10초 청크마다,
        Phase 3 사이클 경계.
      · 일시정지 누르면 현재 작업 중인 Step 을 마친 뒤 다음 체크포인트에서 블로킹
        (보통 수 초 내). 재개 누르면 거기서부터 계속.
      · 중단 누르면 StopRequested 예외가 안전하게 전파되어 브라우저 정리/로그
        저장/절전 해제까지 모두 수행 후 종료 (데이터 정합성 보장).
      · Phase 2(수기 결제) 는 어차피 사람이 개입하는 구간이라 체크포인트 없음.

변경사항 (v4.5 from v4.4):
  - [추가] 진행상황 오버레이 위젯.
      · 화면 우측 하단에 작은 다크 테마 플로팅 창을 띄워 실시간 로그/진행률을 표시.
      · Tkinter 기반. 별도 스레드에서 구동하여 메인 Selenium 루프에 영향 없음.
      · 항상 위(-topmost) + 반투명 + 테두리 없음, 타이틀바 드래그로 이동 가능.
      · logging.Handler 로 기존 logger 에 연결되어 본문 코드 수정 거의 없이
        모든 logger.info/warning/error 가 색상별로 오버레이에도 자동 표시.
      · 상단에 현재 Phase 상태줄 + 하단에 진행률 바 (Phase 1 건별).
      · Tk 를 못 쓰는 환경에서는 조용히 비활성화, 본 작업은 그대로 진행 (graceful).

변경사항 (v4.4 from v4.3):
  - [개선] Phase 3 일괄열람/저장 사이클 속도 개선.
      · 문제 1: [일괄열람출력] 클릭 후 '모두 열람완료 처리됩니다' 확인 팝업에서
        '확인' 을 누르기까지 6초 이상 소요되던 문제.
          원인: handle_batch_view_confirm_popup() 이 alert 를 기대하고 5초간
          대기했지만 실제 팝업은 DOM 모달이라 5초를 꼬박 낭비 → DOM 클릭 경로로
          전환 후 다시 1초 대기. batch_view_and_save_cycle 에서도 뒤에 추가로
          time.sleep(3) 대기.
          수정: alert 최대 대기를 5초→1초로 단축. 팝업 클릭 성공/실패 즉시 반환.
          cycle 내부의 고정 time.sleep(3) 을 능동 대기(_wait_until_modal_dismissed)
          로 교체 - 모달이 사라지면 즉시 다음 단계로, 최대 3초까지만 대기.
      · 문제 2: 한 사이클이 끝나고 다음 사이클 작업 개시까지 14초 이상 공백.
          원인: 닫기 버튼 후 time.sleep(2), alert 체크, 루프 말미 time.sleep(2),
          루프 시작부 time.sleep(1) 등 고정 대기 누적.
          수정: 고정 sleep 을 팝업 dismiss 기반 능동 대기로 교체. 누적 고정 대기
          7초 → 최대 3초 + 즉시 반환 구조. 서버가 정말 느린 환경에서는 기존과
          비슷하고, 정상 환경에서는 2~3초로 단축.

  - [참고] Phase 1 (결제대상 추가) 로직은 건드리지 않음. Phase 3 의 고정 대기만
    능동 대기로 바꿨으며, 타임아웃 상한은 기존과 같거나 약간 짧게 유지.

변경사항 (v4.3 from v4.2):
  - [수정] chromedriver 자동 설치의 SSL 인터셉션 문제 해결.
      · _resolve_chromedriver_path() 3단계 fallback: SSL 우회 → 로컬 캐시 → PATH.
      · os.environ['WDM_SSL_VERIFY'] = '0' 환경변수 폴백.

변경사항 (v4.2 from v4.1):
  - [추가] 작업 중 Windows 절전 모드 / 화면 꺼짐 / 화면보호기 방지.
      · SetThreadExecutionState API, main 진입시 활성화, finally 에서 해제.

변경사항 (v4.1 from v3.16):
  - [수정 1] ElementClickInterceptedException 시에만 processbar 강제 제거.
  - [수정 2] 10회 실패 시 60초 대기 후 재도전 라운드 (최대 2라운드).
  - [수정 3] .py 파일 더블클릭 실행 지원.

변경사항 (v3.16 from v3.15):
  - [수정] 일괄열람 사이클에서 '신청사건 처리중' 팝업이 떠도 닫히지 않던 문제 해결.

변경사항 (v3.14 from v3.13):
  - [수정] 세션 만료 감지 키워드 확장 ("서버와 연결이 끊어졌습니다")

사용법:
    - Windows 에서 add_to_payment_v4_7.py 더블클릭 (가장 간단)
    - python add_to_payment_v4_7.py
    - python add_to_payment_v4_7.py --file 고유번호목록.txt
    - python add_to_payment_v4_7.py --start-from 5
"""

import argparse
import ctypes
import glob
import os
import platform
import queue
import re
import shutil
import sys
import threading
import time
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

# v4.3: 기업/기관망의 SSL 인터셉션으로 인해 chromedriver 버전 조회가
# 자체서명 인증서 오류로 실패하는 문제 회피. webdriver_manager 내부에서 참조함.
# (ChromeDriverManager(ssl_verify=False) 가 동작하지 않는 옛 버전 호환용 폴백)
os.environ.setdefault("WDM_SSL_VERIFY", "0")


# ─── 설정 ──────────────────────────────────────────────────
IROS_BASE_URL = "http://www.iros.go.kr"
LOGIN_PAGE_URL = "http://www.iros.go.kr/pos1/pfrontservlet?vc_id=POPM10_P00_01"
ELEMENT_WAIT_TIMEOUT = 15
DEFAULT_FILE = "property_list.txt"
MAX_RETRY_PER_ITEM = 10
PAYMENT_PAGE_WAIT_TIMEOUT = 15
QUICK_PAYMENT_PAGE_WAIT_TIMEOUT = 3
# v4.8: 유형선택 '다음' 클릭 후 3가지 분기 페이지 중 하나가 렌더될 때까지의
#       최대 폴링 대기 시간. 서버 응답이 느릴 때 중복결제 페이지를 못 보고
#       곧바로 최종확인 다음을 눌러버리는 사고를 막기 위함.
BRANCH_DETECT_TIMEOUT = 8.0
BRANCH_DETECT_POLL    = 0.25

# v4.1: 같은 건이 1라운드(10회) 모두 실패하면 COOLDOWN_BETWEEN_ROUNDS_SEC 초 대기 후
# 2라운드 시도. 최대 MAX_ROUNDS_PER_ITEM 라운드까지 시도 후에도 실패하면 전체 종료.
MAX_ROUNDS_PER_ITEM = 2
COOLDOWN_BETWEEN_ROUNDS_SEC = 60

# ─── 로그인 정보 ─────────────────────────────────────────────
LOGIN_ID = "hfrpa25"
LOGIN_PW = "khfc0301!!"

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


# ─── v4.5: 진행상황 오버레이 ───────────────────────────────
# 우측 하단에 작은 플로팅 창을 띄워 실시간 로그/진행률을 표시.
# Tkinter 를 별도 스레드에서 돌려 메인 Selenium 루프를 블로킹하지 않음.
# logging.Handler 로 기존 logger 에 붙이므로, logger.info(...) 호출부는
# 단 한 줄도 수정할 필요 없이 자동으로 오버레이에 반영됨.
# 설치 환경에 Tk 가 없거나 오류가 나도 본 작업에는 영향을 주지 않음 (graceful fallback).
class ProgressOverlay:
    """우측 하단 플로팅 로그 오버레이."""

    def __init__(self, max_lines=10, width=500, height=290, margin=24, alpha=0.7,
                 controller=None):
        self.max_lines = max_lines
        self.width = width
        self.height = height
        self.margin = margin
        self.alpha = alpha
        self.controller = controller  # v4.6: PauseController 참조 (버튼 콜백용)
        self._q = queue.Queue()
        self._thread = None
        self._ready = threading.Event()
        self._stopped = threading.Event()

    @classmethod
    def start(cls, **kwargs):
        obj = cls(**kwargs)
        obj._thread = threading.Thread(target=obj._run_tk, name="overlay-tk", daemon=True)
        obj._thread.start()
        obj._ready.wait(timeout=2.0)
        return obj

    def log(self, level, message):
        self._q.put(("log", (level, message)))

    def set_status(self, text):
        self._q.put(("status", text))

    def set_progress(self, current, total):
        self._q.put(("progress", (current, total)))

    def set_pause_indicator(self, paused):
        """일시정지 상태 표시 갱신 (버튼 활성/비활성)."""
        self._q.put(("pause_state", bool(paused)))

    def set_stopped(self):
        """중단 요청됨 → 버튼 전부 비활성."""
        self._q.put(("stopped", None))

    def set_batch_save_enabled(self, enabled):
        """v5.1: '일괄저장 시작' 버튼 활성/비활성 토글.
        Phase 2 (수기 결제 대기) 진입 시 True, 클릭되면 False 로 호출."""
        self._q.put(("batch_save_state", bool(enabled)))

    def attach_to_logger(self, target_logger, level=logging.INFO,
                         fmt="%(asctime)s %(message)s", datefmt="%H:%M:%S"):
        h = TkOverlayHandler(self)
        h.setLevel(level)
        h.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        target_logger.addHandler(h)
        return h

    def stop(self):
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._q.put(("__quit__", None))
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run_tk(self):
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception as e:
            print(f"[overlay] Tkinter 사용 불가, 오버레이 비활성화: {e}")
            self._ready.set()
            return

        root = tk.Tk()
        root.title("진행상황")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", self.alpha)
        except tk.TclError:
            pass

        root.update_idletasks()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = screen_w - self.width - self.margin
        y = screen_h - self.height - self.margin - 48
        if y < 0:
            y = self.margin
        root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # 다크 테마 색상
        BG        = "#1e1e1e"
        BG_HEADER = "#2d2d30"
        FG        = "#e8e8e8"
        FG_MUTED  = "#9a9a9a"
        ACCENT    = "#4ea1ff"
        ERR       = "#ff6b6b"
        WARN      = "#ffb86b"

        root.configure(bg=BG)

        # 타이틀바 (드래그 이동 가능)
        title_bar = tk.Frame(root, bg=BG_HEADER, height=26)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)
        title_lbl = tk.Label(title_bar, text="● 진행상황",
                             bg=BG_HEADER, fg=FG,
                             font=("Segoe UI", 9, "bold"), padx=10)
        title_lbl.pack(side="left")
        close_btn = tk.Label(title_bar, text="✕",
                             bg=BG_HEADER, fg=FG_MUTED,
                             font=("Segoe UI", 10, "bold"),
                             padx=10, cursor="hand2")
        close_btn.pack(side="right")

        def _close(_e=None):
            try:
                root.destroy()
            except Exception:
                pass
        close_btn.bind("<Button-1>", _close)
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=ERR))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=FG_MUTED))

        drag_state = {"x": 0, "y": 0}
        def _start_move(e):
            drag_state["x"], drag_state["y"] = e.x, e.y
        def _do_move(e):
            nx = root.winfo_x() + (e.x - drag_state["x"])
            ny = root.winfo_y() + (e.y - drag_state["y"])
            root.geometry(f"+{nx}+{ny}")
        for w in (title_bar, title_lbl):
            w.bind("<Button-1>", _start_move)
            w.bind("<B1-Motion>", _do_move)

        # 상태 영역 (상태 텍스트 + 진행률바 + 진행률 텍스트)
        status_frame = tk.Frame(root, bg=BG)
        status_frame.pack(fill="x", side="top", padx=10, pady=(6, 0))
        status_lbl = tk.Label(status_frame, text="대기 중…",
                              bg=BG, fg=ACCENT,
                              font=("Segoe UI", 9), anchor="w")
        status_lbl.pack(fill="x", side="top")
        progress_lbl = tk.Label(status_frame, text="",
                                bg=BG, fg=FG_MUTED,
                                font=("Segoe UI", 8), anchor="w")
        progress_lbl.pack(fill="x", side="top")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "overlay.Horizontal.TProgressbar",
            troughcolor=BG_HEADER, background=ACCENT,
            bordercolor=BG_HEADER, lightcolor=ACCENT, darkcolor=ACCENT,
            thickness=6,
        )
        pbar = ttk.Progressbar(status_frame,
                               style="overlay.Horizontal.TProgressbar",
                               mode="determinate", maximum=100)
        pbar.pack(fill="x", side="top", pady=(4, 4))

        # v4.6: 제어 버튼 영역 (일시정지 / 재개 / 중단)
        BTN_BG        = "#2d2d30"
        BTN_BG_HOVER  = "#3e3e42"
        BTN_BG_ACTIVE = "#094771"
        BTN_FG        = "#e8e8e8"
        BTN_FG_DIS    = "#5a5a5a"

        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(fill="x", side="top", padx=10, pady=(2, 4))

        ctrl = self.controller  # PauseController 또는 None

        def _make_btn(parent, text, on_click):
            b = tk.Label(parent, text=text, bg=BTN_BG, fg=BTN_FG,
                         font=("Segoe UI", 9), padx=10, pady=3,
                         cursor="hand2")
            b._enabled = True
            b._base_bg = BTN_BG
            def _enter(_e):
                if b._enabled:
                    b.config(bg=BTN_BG_HOVER)
            def _leave(_e):
                if b._enabled:
                    b.config(bg=b._base_bg)
            def _click(_e):
                if b._enabled:
                    try:
                        on_click()
                    except Exception as ex:
                        logger.debug(f"button click error: {ex}")
            b.bind("<Enter>", _enter)
            b.bind("<Leave>", _leave)
            b.bind("<Button-1>", _click)
            return b

        def _set_enabled(btn, enabled, base_bg=None):
            btn._enabled = enabled
            if base_bg is not None:
                btn._base_bg = base_bg
            if enabled:
                btn.config(fg=BTN_FG, bg=btn._base_bg, cursor="hand2")
            else:
                btn.config(fg=BTN_FG_DIS, bg=BTN_BG, cursor="arrow")

        def _on_pause():
            if ctrl is not None:
                ctrl.pause()
                logger.info("[UI] 일시정지 요청 — 현재 작업이 안전 지점에 도달하면 멈춥니다")

        def _on_resume():
            if ctrl is not None:
                ctrl.resume()
                logger.info("[UI] 재개 요청")

        def _on_stop():
            if ctrl is not None:
                ctrl.request_stop()
                logger.warning("[UI] 중단 요청 — 현재 건을 마치고 안전 종료합니다")

        def _on_batch_save():
            # v5.1: 일괄저장 시작 버튼 → Phase 2 의 수기 결제 대기를 종료하고
            #       Phase 3 (일괄열람/저장) 진입을 트리거.
            if ctrl is not None:
                ctrl.signal_batch_save()
                logger.info("[UI] 일괄저장 시작 요청 → Phase 3 진입")

        pause_btn  = _make_btn(btn_frame, "⏸ 일시정지", _on_pause)
        resume_btn = _make_btn(btn_frame, "▶ 재개",     _on_resume)
        stop_btn   = _make_btn(btn_frame, "⏹ 중단",     _on_stop)
        # v5.1: 일괄저장 시작 버튼 (Phase 2 수기 결제 후 클릭)
        # v5.4: 500px 폭에 맞춰 라벨 단축 ('▶▶ 일괄저장 시작' → '▶▶ 일괄저장')
        batch_save_btn = _make_btn(btn_frame, "▶▶ 일괄저장", _on_batch_save)
        pause_btn.pack(side="left", padx=(0, 4))
        resume_btn.pack(side="left", padx=(0, 4))
        stop_btn.pack(side="left", padx=(0, 4))
        batch_save_btn.pack(side="left")

        # 초기 상태: 컨트롤러 없으면 전부 비활성. 있으면 재개 비활성(지금 실행 중이니까).
        if ctrl is None:
            _set_enabled(pause_btn, False)
            _set_enabled(resume_btn, False)
            _set_enabled(stop_btn, False)
            _set_enabled(batch_save_btn, False)
        else:
            _set_enabled(pause_btn, True, BTN_BG)
            _set_enabled(resume_btn, False)  # 아직 일시정지 아님
            _set_enabled(stop_btn, True, "#5a2020")  # 중단은 빨강 계열
            # v5.1: 일괄저장 버튼은 Phase 2 진입 시점에 set_batch_save_enabled(True)
            #       로 활성화될 때까지 비활성.
            _set_enabled(batch_save_btn, False)

        # 로그 영역
        log_frame = tk.Frame(root, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        txt = tk.Text(log_frame, bg=BG, fg=FG,
                      font=("Consolas", 9),
                      borderwidth=0, highlightthickness=0,
                      wrap="none", state="disabled", cursor="arrow")
        txt.pack(fill="both", expand=True)
        txt.tag_configure("INFO",    foreground=FG)
        txt.tag_configure("DEBUG",   foreground=FG_MUTED)
        txt.tag_configure("WARNING", foreground=WARN)
        txt.tag_configure("ERROR",   foreground=ERR)

        self._ready.set()

        def _pump():
            drained = 0
            while drained < 30:
                try:
                    kind, payload = self._q.get_nowait()
                except queue.Empty:
                    break
                drained += 1
                try:
                    if kind == "__quit__":
                        try:
                            root.destroy()
                        except Exception:
                            pass
                        return
                    elif kind == "log":
                        level, message = payload
                        tag = level if level in ("INFO", "DEBUG", "WARNING", "ERROR") else "INFO"
                        txt.configure(state="normal")
                        txt.insert("end", message.rstrip() + "\n", tag)
                        line_count = int(txt.index("end-1c").split(".")[0])
                        if line_count > self.max_lines:
                            txt.delete("1.0", f"{line_count - self.max_lines + 1}.0")
                        txt.see("end")
                        txt.configure(state="disabled")
                    elif kind == "status":
                        status_lbl.config(text=str(payload))
                    elif kind == "progress":
                        cur, tot = payload
                        if tot > 0:
                            pct = max(0, min(100, int(cur * 100 / tot)))
                            pbar["value"] = pct
                            progress_lbl.config(text=f"[{cur}/{tot}] ({pct}%)")
                        else:
                            pbar["value"] = 0
                            progress_lbl.config(text="")
                    elif kind == "pause_state":
                        # v4.6: 일시정지 상태 변경 → 버튼 활성/비활성 전환
                        paused = bool(payload)
                        if paused:
                            _set_enabled(pause_btn, False)
                            _set_enabled(resume_btn, True, BTN_BG_ACTIVE)
                        else:
                            _set_enabled(pause_btn, True, BTN_BG)
                            _set_enabled(resume_btn, False)
                    elif kind == "stopped":
                        # v4.6: 중단 요청됨 → 모든 버튼 비활성
                        _set_enabled(pause_btn, False)
                        _set_enabled(resume_btn, False)
                        _set_enabled(stop_btn, False)
                        _set_enabled(batch_save_btn, False)
                    elif kind == "batch_save_state":
                        # v5.1: 일괄저장 시작 버튼 활성/비활성 토글
                        if bool(payload):
                            # 활성화: 녹색 강조 배경
                            _set_enabled(batch_save_btn, True, "#1f6f1f")
                        else:
                            _set_enabled(batch_save_btn, False)
                except Exception:
                    pass
            try:
                root.after(80, _pump)
            except Exception:
                pass

        root.after(50, _pump)
        try:
            root.mainloop()
        except Exception:
            pass


class TkOverlayHandler(logging.Handler):
    """logging → ProgressOverlay 브릿지 핸들러."""

    def __init__(self, overlay):
        super().__init__()
        self._overlay = overlay

    def emit(self, record):
        try:
            msg = self.format(record)
            self._overlay.log(record.levelname, msg)
        except Exception:
            self.handleError(record)


# 전역 오버레이 인스턴스 (main 에서 초기화). 없으면 no-op.
_overlay = None


# ─── v4.6: 일시정지/중단 컨트롤러 ──────────────────────────
class StopRequested(Exception):
    """사용자가 오버레이에서 '중단' 을 눌렀을 때 발생. 체크포인트에서 던져짐."""
    pass


class PauseController:
    """작업 일시정지/재개/중단 상태 관리.

    사용 패턴:
      - 메인 루프 내 안전 지점(건 경계, 사이클 경계)에서 checkpoint() 호출.
        paused 면 재개될 때까지 블로킹, stopping 이면 StopRequested 발생.
      - 긴 고정 대기(쿨다운 60초 등)는 sleep() 으로 교체하면 중단 응답성 확보.

    Thread-safe: Tk 버튼 콜백(Tk 스레드)과 메인 Selenium 스레드 사이 통신.
    """

    def __init__(self):
        self._paused = threading.Event()   # set = paused
        self._stopping = threading.Event() # set = 중단 요청됨
        self._batch_save = threading.Event()  # v5.1: 일괄저장 시작 버튼 클릭됨
        self._on_state_change = None       # (paused: bool) -> None

    def set_state_callback(self, fn):
        """상태 변경 시 호출될 콜백(주로 오버레이 UI 업데이트용)."""
        self._on_state_change = fn

    @property
    def is_paused(self):
        return self._paused.is_set()

    @property
    def is_stopping(self):
        return self._stopping.is_set()

    def pause(self):
        if self._stopping.is_set():
            return
        self._paused.set()
        if self._on_state_change:
            try:
                self._on_state_change(True)
            except Exception:
                pass

    def resume(self):
        self._paused.clear()
        if self._on_state_change:
            try:
                self._on_state_change(False)
            except Exception:
                pass

    def request_stop(self):
        """중단 요청. 체크포인트/sleep 에서 StopRequested 로 반환됨."""
        self._stopping.set()
        self._paused.clear()  # paused 상태에서도 즉시 빠져나오도록

    def checkpoint(self):
        """안전 지점 체크. paused 면 재개까지 블로킹, stopping 이면 StopRequested."""
        if self._stopping.is_set():
            raise StopRequested()
        if self._paused.is_set():
            logger.info("⏸ 일시정지 (오버레이 '재개' 버튼을 누르면 계속)")
            try:
                overlay_status("⏸ 일시정지됨")
            except Exception:
                pass
            # 재개 또는 중단까지 대기
            while self._paused.is_set() and not self._stopping.is_set():
                time.sleep(0.2)
            if self._stopping.is_set():
                raise StopRequested()
            logger.info("▶ 재개")

    def sleep(self, seconds):
        """중단 가능한 sleep. 대기 중 stop 이 오면 StopRequested, pause 면 대기 연장."""
        end = time.time() + seconds
        while True:
            if self._stopping.is_set():
                raise StopRequested()
            # paused 중이면 카운트다운을 멈춤 (pause 동안은 시간이 안 흐르는 느낌)
            if self._paused.is_set():
                self.checkpoint()   # 재개 대기
                # 재개 후에는 원래 요청한 만큼 다시 대기
                end = time.time() + seconds
                continue
            remaining = end - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    # ─── v5.1: 일괄저장 시작 시그널 (Phase 2 → Phase 3 전환 트리거) ───
    def signal_batch_save(self):
        """오버레이의 '일괄저장 시작' 버튼 클릭 시 호출됨 (Tk 스레드)."""
        self._batch_save.set()

    def reset_batch_save(self):
        """다음 대기를 위해 시그널 리셋 (메인 스레드)."""
        self._batch_save.clear()

    def wait_for_batch_save(self):
        """일괄저장 버튼 클릭까지 블로킹 대기.
        대기 중 stop 이 오면 StopRequested, pause/resume 은 정상 동작.
        Phase 2 의 input() 대체용.
        """
        while True:
            if self._stopping.is_set():
                raise StopRequested()
            if self._batch_save.is_set():
                # 시그널을 소비하고 반환
                self._batch_save.clear()
                return
            # 일시정지 상태도 정상 반응 (paused 면 checkpoint 가 블로킹)
            if self._paused.is_set():
                self.checkpoint()
                continue
            time.sleep(0.15)


# 전역 컨트롤러 (main 에서 초기화)
_pause = None

# v5.2: 팝업 워치독 (main 에서 초기화) ─ Windows 전용
_popup_watcher = None


# ─── v5.2: Windows '응용 프로그램 오류' 팝업 자동 닫기 워치독 ────────────
#
# 배경: 등기소 보안 모듈(V3, nxKey, INISAFE 등) 이 누적 페이지 전환으로
#   access violation 크래시를 일으키면 Windows 가 0x... 메모리 참조 오류
#   모달을 띄움. 이 모달은 OS 레벨이라 브라우저 재시작/페이지 새로고침으로
#   사라지지 않으며, 다른 클릭을 가로막아 자동화가 멈춤.
#
# 동작:
#   - 5초 주기로 EnumWindows 폴링 → 화이트리스트 키워드 매칭 다이얼로그
#     (#32770) 의 '확인' 버튼 자동 클릭.
#   - 1회 발생: 닫기만, 페이스 그대로.
#   - 2회 이상부터: 매 발생마다 휴식 회분(_pending_rest)+1. 메인 루프가
#     건 사이에서 회분을 1씩 소비하며 10초씩 쉼.
#
# 안전성: 닫기 전 창 제목·본문 로그 기록. 일반 다이얼로그·등기소 알림은
#   화이트리스트에 안 걸리므로 절대 건드리지 않음.
class PopupWatcher:
    """Windows 응용 프로그램 오류 팝업 자동 닫기 데몬 + 휴식 회분 관리.

    Windows 가 아니면 무동작. start()/stop() 으로 라이프사이클 제어.
    consume_rest_if_due() 를 메인 루프 건 사이에서 호출하면 회분을 소비함.
    """

    # 닫을 대상의 화이트리스트 키워드 (창 제목에 포함되어야 함). 대소문자 무시.
    _TITLE_KEYWORDS = (
        "응용 프로그램 오류",
        "Application Error",
        "응용 프로그램이 응답하지 않습니다",  # 무응답 모달도 함께 처리
    )
    # 클릭할 버튼 후보 (자식 윈도우 텍스트). 위에서부터 시도.
    _BUTTON_TEXTS = ("확인", "OK", "예", "Yes", "닫기", "Close")

    # Win32 상수
    _BM_CLICK   = 0x00F5
    _WM_CLOSE   = 0x0010
    _WM_GETTEXT = 0x000D
    _WM_GETTEXTLENGTH = 0x000E
    _GW_HWNDNEXT = 2
    _GW_CHILD    = 5

    def __init__(self, poll_interval=5.0, rest_seconds=10, rest_threshold=2):
        """
        poll_interval  : 폴링 주기 (초)
        rest_seconds   : 1회분 휴식 길이 (초)
        rest_threshold : 누적 N회째부터 휴식 회분 부여 시작 (기본 2:
                          1회는 일시적 사고로 간주, 2회부터 누적 부하로 판단)
        """
        self.poll_interval = float(poll_interval)
        self.rest_seconds = int(rest_seconds)
        self.rest_threshold = int(rest_threshold)

        self._stop_evt = threading.Event()
        self._thread = None
        self._enabled = (platform.system() == "Windows")

        # 통계 / 상태 (워치독 스레드와 메인 스레드 모두 접근 → Lock 보호)
        self._lock = threading.Lock()
        self.dismiss_count = 0       # 누적 자동 닫음 횟수
        self._pending_rest = 0       # 부여됐으나 아직 소비 안 된 휴식 회분
        self.rest_granted_total = 0  # 누적 부여 회분
        self.rest_consumed_total = 0 # 누적 소비 회분

        # 같은 hwnd 를 중복 처리하지 않기 위한 최근 처리 캐시
        self._recent_handled = {}    # hwnd -> timestamp

    # ─── 라이프사이클 ───
    def start(self):
        if not self._enabled:
            logger.info("팝업 워치독 건너뜀 (Windows 아님)")
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, name="popup-watcher", daemon=True
        )
        self._thread.start()
        logger.info(
            f"팝업 워치독 시작 (폴링 {self.poll_interval:.0f}초, "
            f"{self.rest_threshold}회째부터 발생 시마다 {self.rest_seconds}초 "
            f"휴식 1회분 부여)"
        )
        return True

    def stop(self):
        if not self._enabled:
            return
        self._stop_evt.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None

    # ─── 메인 루프가 건 사이에서 호출: 휴식 회분 1회 소비 ───
    def consume_rest_if_due(self):
        """대기 중인 휴식 회분이 있으면 1회 소비 (rest_seconds 만큼 대기) 후 True.
        없으면 False 반환 (즉시 종료, 추가 sleep 없음).
        대기는 PauseController.sleep() 으로 수행되어 중단/일시정지에 반응.
        """
        if not self._enabled:
            return False
        with self._lock:
            if self._pending_rest <= 0:
                return False
            self._pending_rest -= 1
            self.rest_consumed_total += 1
            remaining = self._pending_rest
            secs = self.rest_seconds
        logger.warning(
            f"[팝업워치독] OS 팝업 후속 휴식 {secs}초 부여 — "
            f"보안 모듈 회복 시간 확보 (남은 회분 {remaining}회)"
        )
        try:
            if _overlay is not None:
                _overlay.set_status(
                    f"⏸ 휴식 {secs}초 (남은 {remaining}회)"
                )
        except Exception:
            pass
        # 일시정지/중단에 정상 반응하는 중단 가능한 sleep 사용
        if _pause is not None:
            _pause.sleep(secs)
        else:
            time.sleep(secs)
        return True

    # ─── 메인 폴링 루프 ───
    def _run(self):
        try:
            user32 = ctypes.windll.user32
        except Exception as e:
            logger.debug(f"팝업 워치독 비활성 (user32 로드 실패: {e})")
            return

        while not self._stop_evt.is_set():
            try:
                self._scan_once(user32)
            except Exception as e:
                # 폴링 자체가 죽지 않도록 모든 예외 흡수
                logger.debug(f"팝업 워치독 스캔 예외 (무시): {e}")
            # 중단 응답성을 위해 짧게 쪼개 sleep
            end = time.time() + self.poll_interval
            while time.time() < end:
                if self._stop_evt.is_set():
                    return
                time.sleep(0.2)

    # ─── 한 번 스캔 ───
    def _scan_once(self, user32):
        # 오래된 캐시 청소 (60초 초과 제거)
        now = time.time()
        if self._recent_handled:
            self._recent_handled = {
                h: t for h, t in self._recent_handled.items() if now - t < 60
            }

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )
        hits = []

        def _cb(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                # 클래스명 확인 → 다이얼로그(#32770) 만 후보
                cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, cls, 64)
                if cls.value != "#32770":
                    return True
                # 창 제목 가져오기
                title = self._get_window_text(user32, hwnd)
                if not title:
                    return True
                # 화이트리스트 매칭 (대소문자 무시)
                low = title.lower()
                if not any(k.lower() in low for k in self._TITLE_KEYWORDS):
                    return True
                hits.append((hwnd, title))
            except Exception:
                pass
            return True

        user32.EnumWindows(EnumWindowsProc(_cb), 0)

        for hwnd, title in hits:
            # 최근에 이미 처리한 hwnd 는 건너뜀 (재시도 도중 잠깐 안 닫혔을 때
            # 같은 창을 중복 카운트하지 않기 위함)
            if hwnd in self._recent_handled:
                continue
            self._dismiss(user32, hwnd, title)
            self._recent_handled[hwnd] = time.time()

    # ─── 창 텍스트 가져오기 ───
    def _get_window_text(self, user32, hwnd):
        try:
            length = user32.SendMessageW(
                hwnd, self._WM_GETTEXTLENGTH, 0, 0
            )
            if length <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 2)
            user32.SendMessageW(
                hwnd, self._WM_GETTEXT, length + 1, ctypes.byref(buf)
            )
            return buf.value or ""
        except Exception:
            return ""

    # ─── 본문 텍스트 모으기 (모든 자식 윈도우 텍스트 결합) ───
    def _collect_body_text(self, user32, hwnd):
        texts = []
        try:
            child = user32.GetWindow(hwnd, self._GW_CHILD)
            seen = 0
            while child and seen < 30:
                seen += 1
                t = self._get_window_text(user32, child)
                if t:
                    texts.append(t)
                child = user32.GetWindow(child, self._GW_HWNDNEXT)
        except Exception:
            pass
        return " | ".join(texts)

    # ─── 실제 닫기 + 카운터/회분 갱신 ───
    def _dismiss(self, user32, hwnd, title):
        body = self._collect_body_text(user32, hwnd)
        logger.warning(
            f"[팝업워치독] OS 오류 팝업 감지 → 자동 닫기 시도\n"
            f"  · 제목: {title}\n"
            f"  · 내용: {body[:300]}"
        )

        # 1) '확인' 등 버튼을 자식에서 찾아 BM_CLICK
        clicked = self._click_button(user32, hwnd)

        # 2) 버튼을 못 찾았으면 WM_CLOSE 폴백
        if not clicked:
            try:
                user32.PostMessageW(hwnd, self._WM_CLOSE, 0, 0)
                logger.info("[팝업워치독] 버튼 미검출 → WM_CLOSE 폴백 전송")
            except Exception as e:
                logger.debug(f"[팝업워치독] WM_CLOSE 실패: {e}")

        # 카운터 및 휴식 회분 갱신 (Lock 보호)
        with self._lock:
            self.dismiss_count += 1
            count = self.dismiss_count
            # 임계치 이상 발생부터 매번 휴식 1회분 부여
            if count >= self.rest_threshold:
                self._pending_rest += 1
                self.rest_granted_total += 1
                pending = self._pending_rest
            else:
                pending = 0

        # 오버레이 상태줄 갱신
        try:
            if _overlay is not None:
                if count >= self.rest_threshold:
                    # v5.4: 500px 폭에 맞춰 메시지 단축
                    _overlay.set_status(
                        f"⚠ OS 팝업 {count}회 — 휴식 대기 {pending}회"
                    )
                else:
                    _overlay.set_status(f"⚠ OS 팝업 자동 닫음 {count}회")
        except Exception:
            pass

    def _click_button(self, user32, parent_hwnd):
        """parent_hwnd 의 자식 중 Button 클래스이며 텍스트가 매칭되는 첫 버튼 클릭."""
        try:
            child = user32.GetWindow(parent_hwnd, self._GW_CHILD)
            seen = 0
            while child and seen < 30:
                seen += 1
                cls = ctypes.create_unicode_buffer(32)
                user32.GetClassNameW(child, cls, 32)
                if cls.value.lower() == "button":
                    txt = self._get_window_text(user32, child)
                    # 액셀러레이터(&) 제거 후 비교
                    clean = txt.replace("&", "").strip()
                    if clean in self._BUTTON_TEXTS or any(
                        b in clean for b in self._BUTTON_TEXTS
                    ):
                        user32.SendMessageW(child, self._BM_CLICK, 0, 0)
                        logger.info(
                            f"[팝업워치독] '{clean}' 버튼 클릭 전송 → 팝업 닫힘"
                        )
                        return True
                child = user32.GetWindow(child, self._GW_HWNDNEXT)
        except Exception as e:
            logger.debug(f"[팝업워치독] 버튼 클릭 예외: {e}")
        return False


def overlay_status(text):
    """상태줄 업데이트 헬퍼. 오버레이가 없어도 안전."""
    try:
        if _overlay is not None:
            _overlay.set_status(text)
    except Exception:
        pass


def overlay_progress(current, total):
    """진행률 업데이트 헬퍼. 오버레이가 없어도 안전."""
    try:
        if _overlay is not None:
            _overlay.set_progress(current, total)
    except Exception:
        pass


# ─── v4.2: 절전/화면보호기 방지 ────────────────────────────
# Windows 전용. SetThreadExecutionState 로 "지금 작업 중이니 절전 걸지 말아라" 요청.
# - 프로세스 생명주기에 묶여 있어, 스크립트가 어떻게 종료되든 OS 가 자동 원복.
# - 관리자 권한/외부 라이브러리 불필요 (ctypes 는 표준 라이브러리).
# - 한계: GPO(그룹정책) 로 강제된 잠금화면은 본 API 로 우회 불가.
_ES_CONTINUOUS        = 0x80000000
_ES_SYSTEM_REQUIRED   = 0x00000001  # 시스템 절전 방지
_ES_DISPLAY_REQUIRED  = 0x00000002  # 디스플레이 절전/화면보호기 방지


def prevent_sleep():
    """작업 중 절전/화면 꺼짐/화면보호기 방지 시작"""
    if platform.system() != "Windows":
        logger.info("절전 방지 건너뜀 (Windows 아님)")
        return False
    try:
        result = ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED
        )
        if result == 0:
            logger.warning("절전 방지 요청이 거부됨 (이전 상태 반환값 0)")
            return False
        logger.info("절전/화면 꺼짐/화면보호기 방지 활성화")
        return True
    except Exception as e:
        logger.warning(f"절전 방지 설정 실패 (무시하고 계속): {e}")
        return False


def allow_sleep():
    """원상 복구 - 작업 종료 시 OS 에 '이제 절전 걸어도 됨' 통보"""
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
        logger.info("절전/화면보호기 방지 해제")
    except Exception as e:
        logger.debug(f"절전 방지 해제 실패 (무시): {e}")


def load_property_ids(file_path):
    items = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            display_id = line
            clean_id = re.sub(r"[^0-9]", "", line)
            if not clean_id:
                continue
            items.append({"property_id": clean_id, "property_id_display": display_id})
    return items


class PaymentQueueAutomation:

    def __init__(self):
        self.driver = None
        self.failed_items = []
        self.closed_items = []  # v3.13: 폐쇄 등기 고유번호 목록
        # v5.0: 폐쇄 고유번호를 감지 즉시 디스크에 기록하기 위한 파일 경로.
        #       첫 폐쇄 감지 시 _ensure_closed_items_file() 에서 생성됨.
        self._closed_items_file = None  # 즉시 저장용 파일의 절대경로
        self._closed_items_dir = None   # 바탕화면에 만들어진 날짜 폴더의 절대경로

    # ── 유틸 ──────────────────────────────────────────────

    def _dismiss_any_alert(self):
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
            time.sleep(1)
            return True
        except NoAlertPresentException:
            return False

    def _dismiss_modal_popup(self):
        """v2.13: 잔존 모달 팝업(_modal)을 JS로 강제 제거"""
        try:
            removed = self.driver.execute_script("""
                var modal = document.getElementById('_modal');
                if (modal && modal.style.display === 'block') {
                    modal.style.display = 'none';
                    return true;
                }
                // w2modal_popup 클래스 모달도 제거
                var modals = document.querySelectorAll('div.w2modal_popup[style*="display: block"]');
                var found = false;
                for (var i = 0; i < modals.length; i++) {
                    modals[i].style.display = 'none';
                    found = true;
                }
                return found;
            """)
            if removed:
                logger.info("잔존 모달 팝업 강제 제거")
                time.sleep(0.5)
            return removed
        except Exception:
            return False

    # ── v4.1: processbar 오버레이 처리 ─────────────────────
    def _wait_until_processbar_gone(self, max_wait=20.0, poll=0.2):
        """v5.5: '처리 중입니다.' 진행바 오버레이가 화면에서 완전히 사라질
        때까지 대기.

        등기소가 일괄열람 클릭 후 서버측 검증/조회 동안 띄우는 진행바이며,
        이 바가 사라지기 전에는 후속 팝업(처리중 변경 안내) 이 아직 안 떴을
        수 있고, 일괄저장 버튼 클릭도 흡수될 수 있다. 따라서 이 단계에서
        능동 대기해 후속 흐름을 안전하게 만든다.

        Args:
          max_wait: 최대 대기 시간 (초). 기본 20초 — 등기소 서버 지연 흡수.
          poll: 폴링 주기.

        Returns:
          (gone: bool, waited: float)
            gone: 시간 안에 사라졌으면 True, 타임아웃이면 False.
            waited: 실제 대기한 시간 (로그용).
        """
        start = time.time()
        deadline = start + max_wait
        # _kill_processbar_overlay 와 동일한 셀렉터 사용 (일관성)
        # 단, w2modal 은 다른 종류의 모달도 매칭될 수 있으므로 여기서는
        # 진행바만 정확히 보기 위해 id*=processbar 만 기준으로 함.
        js = """
            var bars = document.querySelectorAll('div[id*="processbar"]');
            for (var i = 0; i < bars.length; i++) {
                var s = window.getComputedStyle(bars[i]);
                if (s.display !== 'none' && s.visibility !== 'hidden') {
                    return true;  // 아직 보임
                }
            }
            return false;
        """
        while time.time() < deadline:
            try:
                visible = self.driver.execute_script(js)
            except Exception:
                # 페이지 전환 중 일시적 예외는 무시하고 계속 폴링
                visible = False
            if not visible:
                waited = time.time() - start
                if waited > 0.5:
                    logger.info(f"[처리중 바] 사라짐 확인 (대기 {waited:.1f}초)")
                return True, waited
            time.sleep(poll)
        waited = time.time() - start
        logger.warning(
            f"[처리중 바] {max_wait:.0f}초 대기 후에도 사라지지 않음 → 계속 진행"
        )
        return False, waited

    def _kill_processbar_overlay(self):
        """
        v4.1: 인터넷등기소의 '처리중' 오버레이(___processbar2 등)가 걷히지 않아
        클릭이 intercept 되는 경우에만 호출. 정상 동작 중에는 호출되지 않으며,
        이미 안 보이는 오버레이는 건드리지 않는다.

        매칭 대상:
          - <div id="...processbar..." style="display:block">  (언더스코어/번호 무관)
          - <div class="w2modal" style="display:block">         (일반 w2modal)

        Returns:
          제거한 요소 개수 (0이면 원래 보이는 오버레이가 없었던 것)
        """
        try:
            killed = self.driver.execute_script("""
                var bars = document.querySelectorAll(
                    'div[id*="processbar"], div.w2modal'
                );
                var cnt = 0;
                for (var i = 0; i < bars.length; i++) {
                    var s = window.getComputedStyle(bars[i]);
                    if (s.display !== 'none' && s.visibility !== 'hidden') {
                        bars[i].style.display = 'none';
                        cnt++;
                    }
                }
                return cnt;
            """)
            if killed:
                logger.warning(f"processbar 오버레이 {killed}개 강제 제거 (click intercept 복구)")
                time.sleep(0.3)
            return killed or 0
        except Exception as e:
            logger.debug(f"processbar 제거 중 오류 (무시): {e}")
            return 0

    def _click_with_processbar_retry(self, element, label="click"):
        """
        v4.1: 클릭 시 ElementClickInterceptedException 이 발생하면 processbar
        오버레이를 강제 제거하고 한 번 더 클릭한다. 그래도 실패하면 마지막으로
        JS click 으로 폴백. 정상 케이스에는 전혀 영향 없음.

        Args:
          element: 클릭할 WebElement
          label:   로그용 설명
        Returns:
          True  - 클릭 성공 (최초든 복구 후든)
          False - 모든 경로 실패
        """
        try:
            element.click()
            return True
        except ElementClickInterceptedException as e:
            logger.warning(f"[{label}] click intercepted → processbar 제거 후 재시도")
            killed = self._kill_processbar_overlay()
            # processbar 를 실제로 지운 경우에만 재시도 가치가 있음
            if killed > 0:
                try:
                    element.click()
                    logger.info(f"[{label}] processbar 제거 후 재클릭 성공")
                    return True
                except Exception:
                    pass
            # 마지막 폴백: JS click
            try:
                self.driver.execute_script("arguments[0].click();", element)
                logger.info(f"[{label}] JS click 폴백 성공")
                return True
            except Exception as e2:
                logger.error(f"[{label}] 모든 클릭 경로 실패: {e2}")
                return False
        except Exception as e:
            logger.debug(f"[{label}] click 예외(intercept 아님): {e}")
            raise

    def _handle_alert(self, accept=True):
        try:
            alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            text = alert.text
            logger.info(f"알림: {text[:60]}")
            alert.accept() if accept else alert.dismiss()
            time.sleep(1)
            return text
        except TimeoutException:
            return None

    # ── 세션 만료 감지 ────────────────────────────────────

    def _is_session_expired(self):
        # 1) alert 체크 (세션 만료 alert 팝업)
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            if any(kw in alert_text for kw in ["세션", "만료", "시간", "로그인",
                                                "연결이 끊어", "다시 로그인", "서버와 연결"]):
                logger.warning(f"세션 만료 alert: {alert_text[:80]}")
                alert.accept()
                time.sleep(2)
                return True
            # 기타 alert는 수락하고 계속
            alert.accept()
            time.sleep(1)
        except NoAlertPresentException:
            pass

        # 2) 모달 팝업 형태의 세션 만료 처리 (클릭 후 로그인 화면으로 이동)
        #    v3.14: "서버와 연결이 끊어졌습니다" 팝업도 감지
        try:
            session_keywords = ["세션", "만료", "자동 로그아웃", "자동로그아웃",
                                "연결이 끊어", "다시 로그인", "서버와 연결"]
            for kw in session_keywords:
                elems = self.driver.find_elements(
                    By.XPATH, f"//*[contains(text(),'{kw}')]")
                for elem in elems:
                    try:
                        if not elem.is_displayed():
                            continue
                        logger.warning(f"세션 만료 팝업 감지: {elem.text[:60]}")
                        # 팝업 내 버튼 찾아 클릭
                        popup_root = elem
                        for _ in range(6):
                            try:
                                popup_root = popup_root.find_element(By.XPATH, "..")
                                btns = popup_root.find_elements(
                                    By.XPATH,
                                    ".//input[@type='button'] | .//button | .//a[contains(@class,'btn')]")
                                for btn in btns:
                                    if btn.is_displayed():
                                        try:
                                            btn.click()
                                        except Exception:
                                            self.driver.execute_script(
                                                "arguments[0].click();", btn)
                                        time.sleep(2)
                                        logger.info("세션 만료 팝업 버튼 클릭")
                                        return True
                            except Exception:
                                break
                    except Exception:
                        continue
        except Exception:
            pass

        # 3) 헤더의 로그인 그룹이 visible → 로그아웃 상태
        try:
            grp_login = self.driver.find_element(
                By.ID, "mf_wfm_potal_main_wf_header_grp_login")
            grp_logout = self.driver.find_element(
                By.ID, "mf_wfm_potal_main_wf_header_grp_logout")
            login_style = grp_login.get_attribute("style") or ""
            logout_style = grp_logout.get_attribute("style") or ""
            # 로그인 그룹이 보이고 로그아웃 그룹이 숨겨져 있으면 만료
            if ("display: none" not in login_style and "visibility: hidden" not in login_style and
                    ("display: none" in logout_style or "visibility: hidden" in logout_style)):
                return True
        except Exception:
            pass

        # 4) 현재 페이지가 로그인 페이지인지 확인
        try:
            if "로그인" in self.driver.title:
                return True
        except Exception:
            pass

        return False

    def ensure_logged_in(self):
        # v3.12: 보안 프로그램 설치 페이지 감지 → 자동 복구
        if self._is_security_install_page():
            self._recover_from_security_page()

        if self._is_session_expired():
            logger.warning("세션 만료 → 재로그인")
            self._dismiss_any_alert()
            time.sleep(2)
            self._wait_for_page_content(max_retries=2)
            self._dismiss_modal_popup()
            self.login()
        return True

    # ── 브라우저 ──────────────────────────────────────────

    def _is_page_blank(self):
        """페이지가 빈 화면인지 JS로 즉시 확인"""
        try:
            text_len = self.driver.execute_script(
                "return (document.body && document.body.innerText || '').trim().length;")
            return text_len < 30
        except Exception:
            return True

    def _wait_for_page_content(self, max_retries=3):
        """페이지 로드 후 빈 화면이면 즉시 새로고침 (최대 max_retries회)"""
        for attempt in range(max_retries):
            # readyState 완료 대기
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass
            self._dismiss_any_alert()

            # 빈 화면 체크 - 즉시 확인
            if not self._is_page_blank():
                return True

            logger.warning(f"빈 화면 감지 → 즉시 새로고침 (시도 {attempt+1}/{max_retries})")
            try:
                self.driver.refresh()
            except Exception:
                self.driver.get(IROS_BASE_URL)

        logger.warning("빈 화면 새로고침 재시도 모두 실패 → 계속 진행")
        return False

    def _is_security_install_page(self):
        """v3.12: TouchEn nxKey 등 보안 프로그램 설치 페이지인지 감지"""
        try:
            title = self.driver.title or ""
            if "TouchEn" in title or "보안" in title or "제품 설치" in title:
                return True
            url = self.driver.current_url or ""
            if "touchen" in url.lower() or "nxkey" in url.lower():
                return True
            body = self._get_body_text()[:500] if hasattr(self, '_get_body_text') else ""
            if "보안 프로그램 설치" in body or "TouchEn" in body:
                return True
        except Exception:
            pass
        return False

    def _recover_from_security_page(self):
        """v3.12: 보안 프로그램 설치 페이지에서 인터넷등기소 메인으로 복구"""
        logger.warning("보안 프로그램 설치 페이지 감지 → 인터넷등기소로 복구")
        try:
            self.driver.get(IROS_BASE_URL)
            self._wait_for_page_content(max_retries=3)
            if self._is_security_install_page():
                logger.warning("복구 실패 → 재시도")
                time.sleep(2)
                self.driver.get(IROS_BASE_URL)
                self._wait_for_page_content(max_retries=3)
            return not self._is_security_install_page()
        except Exception as e:
            logger.error(f"보안 페이지 복구 실패: {e}")
            return False

    def _resolve_chromedriver_path(self):
        """v4.3: ChromeDriver 경로를 다단계 fallback 으로 획득.

        기업/기관망의 SSL 인터셉션(자체서명 인증서)으로 webdriver_manager 의
        버전 조회(https://googlechromelabs.github.io/...)가 실패하는 환경에서도
        스크립트가 실행되도록 한다.

        시도 순서:
          1) ChromeDriverManager(ssl_verify=False).install()  — SSL 검증 우회
          2) 로컬 webdriver_manager 캐시(~\\.wdm\\drivers\\chromedriver\\...) 에서
             가장 최근 mtime 의 chromedriver 직접 사용
          3) 모두 실패 시 None 반환 → Service() 로 PATH 기본 탐색에 위임
        """
        # 1) SSL 검증을 끈 상태로 webdriver_manager 에 위임
        try:
            try:
                mgr = ChromeDriverManager(ssl_verify=False)
            except TypeError:
                # 옛 webdriver_manager 버전: 생성자에 ssl_verify 파라미터 없음
                # → 상단에서 세팅한 WDM_SSL_VERIFY=0 환경변수에 의존
                mgr = ChromeDriverManager()
            path = mgr.install()
            if path and os.path.isfile(path):
                logger.info(f"ChromeDriver: webdriver_manager 로 획득 ({path})")
                return path
        except Exception as e:
            logger.warning(
                f"webdriver_manager 획득 실패 ({type(e).__name__}): "
                f"{str(e)[:120]}"
            )

        # 2) 로컬 캐시 폴더에서 가장 최근 버전 직접 탐색
        try:
            cache_root = Path.home() / ".wdm" / "drivers" / "chromedriver"
            if cache_root.is_dir():
                candidates = list(cache_root.rglob("chromedriver.exe")) \
                             + list(cache_root.rglob("chromedriver"))
                candidates = [c for c in candidates if c.is_file()]
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                if candidates:
                    path = str(candidates[0])
                    logger.info(f"ChromeDriver: 로컬 캐시에서 획득 ({path})")
                    return path
                logger.warning(
                    f"ChromeDriver 캐시 폴더는 존재하나 드라이버 없음: {cache_root}"
                )
            else:
                logger.warning(f"ChromeDriver 캐시 폴더 없음: {cache_root}")
        except Exception as e:
            logger.warning(f"로컬 캐시 탐색 실패: {e}")

        # 3) PATH 에서 chromedriver 탐색 (Selenium 기본 동작에 위임)
        logger.warning("ChromeDriver: PATH 에서 탐색 시도 (Selenium 기본 동작)")
        return None

    def _prepare_selenium_profile(self):
        """v3.13: 기존 Chrome 프로필에서 보안 프로그램 관련 데이터만 복사한 경량 프로필 생성

        기존 프로필 전체를 직접 사용하면:
          - 프로필 용량이 커서 Selenium 타임아웃 발생
          - Chrome이 열려있으면 잠금 충돌
        경량 복사 방식은 이 두 문제를 모두 해결함.
        """
        chrome_src = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
        if not chrome_src.is_dir():
            logger.info("Chrome 프로필 경로 없음 → 기본 프로필 사용")
            return None

        # 작업 폴더에 경량 프로필 생성
        selenium_profile = Path.home() / ".selenium_chrome_profile"
        default_src = chrome_src / "Default"
        default_dst = selenium_profile / "Default"

        try:
            default_dst.mkdir(parents=True, exist_ok=True)

            # 보안 프로그램 인식에 필요한 핵심 폴더/파일만 복사
            copy_targets = [
                "Local Storage",       # 사이트별 저장 데이터 (보안 프로그램 인식)
                "IndexedDB",           # 보안 관련 DB
                "Extension State",     # 확장프로그램 상태
                "Extensions",          # 확장프로그램 본체
                "Preferences",         # 설정 파일
                "Secure Preferences",  # 보안 설정
            ]

            for target in copy_targets:
                src = default_src / target
                dst = default_dst / target
                if not src.exists():
                    continue
                try:
                    if src.is_dir():
                        if dst.exists():
                            shutil.rmtree(str(dst), ignore_errors=True)
                        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(src), str(dst))
                except Exception:
                    pass  # 일부 파일 복사 실패는 무시

            # 상위 레벨 파일도 복사 (Local State 등)
            for fname in ["Local State"]:
                src_f = chrome_src / fname
                if src_f.is_file():
                    try:
                        shutil.copy2(str(src_f), str(selenium_profile / fname))
                    except Exception:
                        pass

            logger.info(f"경량 Chrome 프로필 생성 완료: {selenium_profile}")
            return selenium_profile

        except Exception as e:
            logger.warning(f"경량 프로필 생성 실패: {e}")
            return None

    def start(self):
        logger.info("브라우저 시작 중...")
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])  # "자동화된 테스트" 알림바 숨김
        opts.add_experimental_option("useAutomationExtension", False)

        # v3.13: 기존 프로필에서 보안 관련 데이터만 복사한 경량 프로필 사용
        #   - 기존 프로필 전체를 쓰면 용량 문제로 타임아웃 발생
        #   - 경량 복사 → Chrome이 열려있어도 충돌 없음
        profile_dir = self._prepare_selenium_profile()
        if profile_dir:
            opts.add_argument(f"--user-data-dir={profile_dir}")
            opts.add_argument("--profile-directory=Default")

        # v4.3: ChromeDriver 경로를 다단계 fallback 으로 획득 (SSL 오류 회피)
        driver_path = self._resolve_chromedriver_path()
        service = Service(driver_path) if driver_path else Service()
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.set_page_load_timeout(30)
        self.driver.get(IROS_BASE_URL)
        self._wait_for_page_content(max_retries=3)
        logger.info("인터넷등기소 접속 완료")

    # ── 자동 로그인 ───────────────────────────────────────

    def _login_form_visible(self):
        try:
            el = self.driver.find_element(
                By.ID, "mf_wfm_potal_main_wfm_content_sbx_user_id_g___input")
            return self.driver.execute_script(
                "return arguments[0].offsetParent !== null;", el)
        except Exception:
            return False

    def _safe_click(self, elem):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", elem)
        except Exception:
            pass

        for action in (
            lambda: elem.click(),
            lambda: ActionChains(self.driver).move_to_element(elem).pause(0.2).click(elem).perform(),
            lambda: self.driver.execute_script("arguments[0].click();", elem),
        ):
            try:
                action()
                return True
            except (
                ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException,
            ):
                continue
            except Exception:
                continue
        return False

    def _click_any_visible(self, selectors, timeout=3, label=None):
        for by, sel in selectors:
            try:
                elems = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((by, sel))
                )
            except TimeoutException:
                continue

            for elem in elems:
                try:
                    if not elem.is_displayed():
                        continue
                    if self._safe_click(elem):
                        if label:
                            logger.info(f"{label} 클릭")
                        time.sleep(1)
                        return True
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
        return False

    def _try_open_login_from_current_page(self, label_prefix=""):
        self._dismiss_any_alert()

        top_login_selectors = [
            (By.ID, "mf_wfm_potal_main_wf_header_btn_login"),
            (By.XPATH, "//*[@id='mf_wfm_potal_main_wf_header_grp_login']//*[self::a or self::button][contains(normalize-space(.), '로그인')]"),
            (By.XPATH, "//*[contains(@id,'grp_login')]//*[self::a or self::button][contains(normalize-space(.), '로그인')]"),
            (By.XPATH, "//a[contains(normalize-space(.), '로그인')][ancestor::*[contains(@id,'header')]]"),
        ]
        dropdown_login_selectors = [
            (By.ID, "mf_wfm_potal_main_wf_header_wq_uuid_2529"),
            (By.XPATH, "//*[@id='mf_wfm_potal_main_wf_header_grp_login']//div[contains(@class,'box-link')]//*[self::a or self::button][contains(normalize-space(.), '로그인')]"),
            (By.XPATH, "//*[contains(@class,'box-link')]//*[self::a or self::button][contains(normalize-space(.), '로그인')]"),
        ]

        if self._click_any_visible(top_login_selectors, timeout=2, label=f"{label_prefix}상단 로그인"):
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda d: d.execute_script(
                        "var box = document.querySelector('#mf_wfm_potal_main_wf_header_grp_login .box-link');"
                        "return !!(box && getComputedStyle(box).display !== 'none' && getComputedStyle(box).visibility !== 'hidden');"
                    )
                )
            except TimeoutException:
                pass

        try:
            self.driver.execute_script("""
                var grp = document.getElementById('mf_wfm_potal_main_wf_header_grp_login');
                if (grp) { grp.classList.add('on'); }
                var box = document.querySelector('#mf_wfm_potal_main_wf_header_grp_login .box-link');
                if (box) {
                    box.style.display = 'block';
                    box.style.visibility = 'visible';
                    box.style.opacity = '1';
                    box.style.pointerEvents = 'auto';
                }
            """)
        except Exception:
            pass

        if self._click_any_visible(dropdown_login_selectors, timeout=2, label=f"{label_prefix}드롭다운 로그인"):
            try:
                WebDriverWait(self.driver, 5).until(lambda d: self._login_form_visible())
                logger.info(f"{label_prefix}드롭다운 로그인 클릭 후 로그인 폼 로드 완료")
                return True
            except TimeoutException:
                pass

        return self._login_form_visible()

    def _open_login_form(self):
        if self._login_form_visible():
            return True

        self._dismiss_any_alert()

        # 1) 현재 떠 있는 첫 화면에서 바로 시도
        try:
            if self._try_open_login_from_current_page():
                return True
        except Exception as e:
            logger.warning(f"현재 화면에서 로그인 진입 실패: {e}")

        # 2) 현재 페이지가 꼬였을 때만 메인으로 한 번 이동 후 재시도
        try:
            current_url = self.driver.current_url or ""
        except Exception:
            current_url = ""

        if IROS_BASE_URL not in current_url:
            try:
                self.driver.get(IROS_BASE_URL)
                WebDriverWait(self.driver, 8).until(
                    lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
                )
                self._dismiss_any_alert()
                if self._try_open_login_from_current_page(label_prefix="메인 재진입 후 "):
                    return True
            except Exception as e:
                logger.warning(f"메인 재진입 후 로그인 실패: {e}")

        # 3) 직접 로그인 페이지 이동은 fallback으로만 사용
        for url in [LOGIN_PAGE_URL, f"{IROS_BASE_URL}/pos1/pfrontservlet?vc_id=POPM10_P00_01"]:
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 8).until(
                    lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
                )
                self._dismiss_any_alert()
                if self._login_form_visible():
                    logger.info("로그인 페이지 직접 이동 성공")
                    return True
            except Exception:
                continue

        # 4) 마지막 JS fallback
        try:
            self.driver.execute_script("""
                var grp = document.getElementById('mf_wfm_potal_main_wf_header_grp_login');
                if (grp) { grp.classList.add('on'); }
                var box = document.querySelector('#mf_wfm_potal_main_wf_header_grp_login .box-link');
                if (box) {
                    box.style.display = 'block';
                    box.style.visibility = 'visible';
                    box.style.opacity = '1';
                    box.style.pointerEvents = 'auto';
                }
                var explicit = document.getElementById('mf_wfm_potal_main_wf_header_wq_uuid_2529');
                if (explicit) {
                    explicit.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
                    explicit.click();
                    return true;
                }
                var links = document.querySelectorAll('#mf_wfm_potal_main_wf_header_grp_login a, #mf_wfm_potal_main_wf_header_grp_login button');
                for (var i = 0; i < links.length; i++) {
                    var txt = (links[i].innerText || links[i].textContent || '').trim();
                    if (txt === '로그인' || txt.indexOf('로그인') >= 0) {
                        links[i].dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
                        links[i].click();
                        return true;
                    }
                }
                if (window.scwin && typeof scwin.cmm_fn_menu_click === 'function') {
                    scwin.cmm_fn_menu_click('POPM10_P00_01');
                    return true;
                }
                return false;
            """)
            WebDriverWait(self.driver, 5).until(lambda d: self._login_form_visible())
            logger.info("JS fallback으로 로그인 폼 로드 완료")
            return True
        except Exception as e:
            logger.warning(f"JS fallback 로그인 진입 실패: {e}")

        return self._login_form_visible()

    def login(self):
        self._dismiss_any_alert()

        # ── 이미 로그인 상태 확인 ──────────────────────────────
        try:
            logout_grp = self.driver.find_element(By.ID, "mf_wfm_potal_main_wf_header_grp_logout")
            style = logout_grp.get_attribute("style") or ""
            if "display: none" not in style and "visibility: hidden" not in style:
                logger.info("이미 로그인 상태")
                return True
        except Exception:
            pass

        logger.info("로그인 시도...")

        if not self._open_login_form():
            logger.error("로그인 페이지 진입 실패")
            return False

        # v2.13: 로그인 폼 진입 후 잔존 모달 강제 제거
        self._dismiss_modal_popup()
        self._dismiss_any_alert()

        # ID/PW 입력 (v2.13: 최대 2회 재시도)
        for login_attempt in range(2):
            try:
                wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)

                # v2.13: 두 필드 모두 element_to_be_clickable로 대기
                id_field = wait.until(EC.element_to_be_clickable(
                    (By.ID, "mf_wfm_potal_main_wfm_content_sbx_user_id_g___input")))
                pw_field = wait.until(EC.element_to_be_clickable(
                    (By.ID, "mf_wfm_potal_main_wfm_content_sct_mbr_pw_g")))

                # ID 입력
                id_field.click()
                time.sleep(0.2)
                id_field.clear()
                id_field.send_keys(LOGIN_ID)
                time.sleep(0.2)

                # v2.13: ID 값 검증
                actual_id = id_field.get_attribute("value") or ""
                if actual_id != LOGIN_ID:
                    logger.warning(f"ID 입력값 불일치: '{actual_id}' → JS 재입력")
                    self.driver.execute_script(
                        "var e=arguments[0]; e.value=''; e.value=arguments[1];"
                        "e.dispatchEvent(new Event('input',{bubbles:true}));"
                        "e.dispatchEvent(new Event('change',{bubbles:true}));",
                        id_field, LOGIN_ID)
                    time.sleep(0.2)

                # PW 입력
                pw_field.click()
                time.sleep(0.2)
                pw_field.clear()
                pw_field.send_keys(LOGIN_PW)
                time.sleep(0.2)

                # v2.13: PW 값 검증 → 비어있으면 JS 직접 입력으로 재시도
                actual_pw = pw_field.get_attribute("value") or ""
                if not actual_pw:
                    logger.warning("PW send_keys 실패 (빈 값) → JS 직접 입력")
                    self.driver.execute_script(
                        "var e=arguments[0]; e.focus(); e.value=''; e.value=arguments[1];"
                        "e.dispatchEvent(new Event('input',{bubbles:true}));"
                        "e.dispatchEvent(new Event('change',{bubbles:true}));",
                        pw_field, LOGIN_PW)
                    time.sleep(0.3)
                    actual_pw = pw_field.get_attribute("value") or ""

                if not actual_pw:
                    logger.error(f"PW 입력 실패 (시도 {login_attempt+1}/2)")
                    if login_attempt == 0:
                        # 모달 제거 후 재시도
                        self._dismiss_modal_popup()
                        self._dismiss_any_alert()
                        time.sleep(1)
                        continue
                    return False

                logger.info("ID/PW 입력 완료 (검증 통과)")

                # 로그인 버튼 클릭
                login_btn = wait.until(EC.element_to_be_clickable(
                    (By.ID, "mf_wfm_potal_main_wfm_content_btn_login")))
                self._safe_click(login_btn)
                time.sleep(3)
                self._dismiss_any_alert()

                # 로그인 성공 확인
                for _ in range(8):
                    try:
                        logout_grp = self.driver.find_element(
                            By.ID, "mf_wfm_potal_main_wf_header_grp_logout")
                        style = logout_grp.get_attribute("style") or ""
                        if "display: none" not in style and "visibility: hidden" not in style:
                            logger.info("로그인 완료")
                            return True
                    except Exception:
                        pass

                    try:
                        btn_logout = self.driver.find_element(
                            By.ID, "mf_wfm_potal_main_wf_header_btn_logout")
                        if btn_logout.is_displayed():
                            logger.info("로그인 완료")
                            return True
                    except Exception:
                        pass

                    try:
                        current_url = self.driver.current_url or ""
                        current_title = self.driver.title or ""
                        if not self._login_form_visible() and "로그인" not in current_title and "POPM10_P00_01" not in current_url:
                            logger.info("로그인 완료(폼 종료 기준)")
                            return True
                    except Exception:
                        pass

                    time.sleep(1)

                # v2.13: 로그인 실패 시 "비밀번호 입력" 알림이 떴는지 확인
                alert_text = self._handle_alert(accept=True)
                if alert_text and ("패스워드" in alert_text or "비밀번호" in alert_text):
                    logger.warning(f"비밀번호 미입력 알림 감지: {alert_text[:60]} → 재시도")
                    if login_attempt == 0:
                        self._dismiss_modal_popup()
                        time.sleep(1)
                        continue
                    return False

                logger.error("로그인 후에도 로그인 화면에서 벗어나지 못함")
                if login_attempt == 0:
                    logger.info("로그인 재시도...")
                    self._dismiss_modal_popup()
                    self._dismiss_any_alert()
                    time.sleep(1)
                    continue
                return False

            except Exception as e:
                logger.error(f"로그인 실패: {e}")
                if login_attempt == 0:
                    self._dismiss_modal_popup()
                    self._dismiss_any_alert()
                    time.sleep(1)
                    continue
                return False

        return False

    # ── 페이지 이동 ───────────────────────────────────────

    def go_to_main(self):
        self._dismiss_any_alert()
        # v3.12: 보안 프로그램 설치 페이지에 있으면 먼저 복구
        if self._is_security_install_page():
            self._recover_from_security_page()
        try:
            logo = self.driver.find_element(By.ID, "mf_wfm_potal_main_wf_header_btn_home")
            self.driver.execute_script("arguments[0].click();", logo)
        except Exception:
            self.driver.get(IROS_BASE_URL)
        self._wait_for_page_content(max_retries=3)
        logger.info("메인 페이지 이동")
        return True

    # ── 워크플로우 단계 ───────────────────────────────────

    def click_realty_view_issue(self):
        self._dismiss_any_alert()
        # JS로 즉시 클릭 시도 (implicitly_wait/WebDriverWait 없이 빠르게)
        clicked = self.driver.execute_script("""
            // 1) ID로 직접 찾기
            var el = document.getElementById('mf_wfm_potal_main_wf_header_gen_depth1_0_gen_depth2_0_gen_depth3_0_btn_top_menu3a');
            if (el) { el.click(); return true; }
            // 2) alt 속성으로 이미지 부모 찾기
            var imgs = document.querySelectorAll('img[alt*="열람"]');
            for (var i = 0; i < imgs.length; i++) {
                if (imgs[i].alt.indexOf('발급') >= 0 || imgs[i].parentElement) {
                    imgs[i].parentElement.click(); return true;
                }
            }
            // 3) 텍스트로 링크 찾기
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {
                var txt = (links[i].textContent || '').trim();
                if (txt === '열람·발급' || (txt.indexOf('열람') >= 0 && txt.indexOf('발급') >= 0)) {
                    links[i].click(); return true;
                }
            }
            return false;
        """)
        if clicked:
            time.sleep(0.5)
            logger.info("[부동산 열람·발급] 클릭")
            return True
        # JS 실패 시 Selenium fallback (짧은 timeout)
        try:
            elem = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(
                (By.ID, "mf_wfm_potal_main_wf_header_gen_depth1_0_gen_depth2_0_gen_depth3_0_btn_top_menu3a")))
            elem.click()
            time.sleep(0.5)
            logger.info("[부동산 열람·발급] 클릭 (폴백)")
            return True
        except Exception:
            pass
        logger.error("[부동산 열람·발급] 실패")
        return False

    def handle_existing_payment_popup(self):
        time.sleep(1)
        try:
            modal = self.driver.find_element(By.ID, "_modal")
            if modal.is_displayed():
                logger.info("결제대상 팝업 감지")
                for xpath in ["//a[contains(text(), '취소')]", "//button[contains(text(), '취소')]"]:
                    for btn in self.driver.find_elements(By.XPATH, xpath):
                        if btn.is_displayed():
                            try:
                                btn.click()
                            except ElementClickInterceptedException:
                                self.driver.execute_script("arguments[0].click();", btn)
                            logger.info("[취소] 클릭")
                            time.sleep(2)
                            return True
        except NoSuchElementException:
            pass
        try:
            alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            if any(k in alert.text for k in ["결제", "등기사항증명서"]):
                alert.dismiss()
                time.sleep(1)
                return True
            alert.accept()
            time.sleep(1)
        except TimeoutException:
            pass
        return False

    def select_unique_number_tab(self):
        wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)
        tab_id = "mf_wfm_potal_main_wfm_content_tac_rlrg_appl_tab_tab_pin_srch_tabHTML"
        try:
            tab = wait.until(EC.element_to_be_clickable((By.ID, tab_id)))
            tab.click()
            time.sleep(0.5)
            logger.info("[고유번호검색] 탭 선택")
            return True
        except Exception:
            try:
                tab = self.driver.find_element(By.ID, tab_id)
                self.driver.execute_script("arguments[0].click();", tab)
                time.sleep(0.5)
                return True
            except Exception:
                pass
        logger.error("[고유번호검색] 탭 실패")
        return False

    def enter_property_id_and_search(self, property_id):
        wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)
        try:
            # 모달 잔존 처리
            try:
                WebDriverWait(self.driver, 1).until_not(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.w2modal_popup[style*='display: block']")))
            except TimeoutException:
                self.handle_existing_payment_popup()
                time.sleep(1)

            inp = wait.until(EC.element_to_be_clickable(
                (By.ID, "mf_wfm_potal_main_wfm_content_sbx_real_pin___input")))
            # v4.1: 고유번호 입력창 클릭은 processbar 오버레이에 의해 intercept 되는
            # 경우가 관측됨 → 예외 시 오버레이 제거 후 재시도하는 래퍼 사용
            if not self._click_with_processbar_retry(inp, label="고유번호 입력창"):
                return False
            time.sleep(0.3)
            inp.clear()
            time.sleep(0.2)
            try:
                inp.send_keys(property_id)
            except Exception:
                self.driver.execute_script(
                    "var e=arguments[0];e.value='';e.value=arguments[1];"
                    "e.dispatchEvent(new Event('input',{bubbles:true}));"
                    "e.dispatchEvent(new Event('change',{bubbles:true}));",
                    inp, property_id)
            logger.info(f"고유번호 입력: {property_id}")
            time.sleep(0.3)

            btn = wait.until(EC.element_to_be_clickable(
                (By.ID, "mf_wfm_potal_main_wfm_content_btn_pin_srch")))
            # v4.1: 검색 버튼 클릭도 동일 래퍼 사용 (기존 intercept 폴백 흡수)
            if not self._click_with_processbar_retry(btn, label="검색 버튼"):
                return False
            time.sleep(1)

            alert_text = self._handle_alert(accept=True)
            if alert_text and ("없습니다" in alert_text or "오류" in alert_text):
                logger.error(f"검색 실패: {alert_text}")
                return False
            return True
        except Exception as e:
            logger.error(f"입력/검색 실패: {e}")
            return False

    def _click_next_button_ultra_fast(self, desc="다음"):
        """신청사건처리중 우회용 초고속 다음 클릭"""
        btn_id = "mf_wfm_potal_main_wfm_content_btn_next"
        try:
            clicked = self.driver.execute_script("""
                var btn = document.getElementById(arguments[0]);
                if (!btn) return false;
                var style = window.getComputedStyle(btn);
                if (btn.offsetParent === null || style.display === 'none' || style.visibility === 'hidden') return false;
                try { btn.focus(); } catch(e) {}
                try { btn.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true, view:window})); } catch(e) {}
                try { btn.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, cancelable:true, view:window})); } catch(e) {}
                try { btn.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window})); } catch(e) {}
                try { btn.click(); } catch(e) {}
                return true;
            """, btn_id)
            if clicked:
                self._handle_alert(accept=True)
                logger.info(f"[{desc}] 클릭")
                return True
        except Exception:
            pass

        try:
            btn = self.driver.find_element(By.ID, btn_id)
            self.driver.execute_script("arguments[0].focus(); arguments[0].click();", btn)
            self._handle_alert(accept=True)
            logger.info(f"[{desc}] 클릭 (초고속 폴백)")
            return True
        except Exception:
            pass

        logger.error(f"[{desc}] 실패")
        return False

    def click_next_button(self, desc="다음"):
        # 신청사건처리중 우회용 추가 클릭은 대기 없이 즉시 실행
        if "추가" in desc:
            return self._click_next_button_ultra_fast(desc)

        # 검색결과 다음은 즉시 클릭, 나머지는 짧은 대기
        if "검색결과" not in desc:
            time.sleep(0.3)

        btn_id = "mf_wfm_potal_main_wfm_content_btn_next"

        # JS로 즉시 클릭 시도
        clicked = self.driver.execute_script("""
            var btn = document.getElementById(arguments[0]);
            if (btn && btn.offsetParent !== null) {
                btn.click();
                return true;
            }
            return false;
        """, btn_id)

        if clicked:
            time.sleep(0.5)
            self._handle_alert(accept=True)
            logger.info(f"[{desc}] 클릭")
            return True

        # JS 즉시 실패 → 짧은 WebDriverWait 폴백
        try:
            btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, btn_id)))
            visible = self.driver.execute_script(
                "var e=document.getElementById(arguments[0]);"
                "return e&&e.offsetParent!==null&&"
                "getComputedStyle(e).display!=='none'&&"
                "getComputedStyle(e).visibility!=='hidden';", btn_id)
            if not visible:
                time.sleep(2)
            # v4.1: intercept 시 processbar 오버레이 제거 후 재시도
            self._click_with_processbar_retry(btn, label=desc)
            time.sleep(0.5)
            self._handle_alert(accept=True)
            logger.info(f"[{desc}] 클릭")
            return True
        except Exception:
            pass
        try:
            b = self.driver.find_element(By.XPATH, "//a[text()='다음']")
            if b.is_displayed():
                b.click()
                time.sleep(0.5)
                self._handle_alert(accept=True)
                logger.info(f"[{desc}] 클릭 (폴백)")
                return True
        except Exception:
            pass
        logger.error(f"[{desc}] 실패")
        return False

    def select_current_valid_option(self):
        time.sleep(0.5)
        sel_id = "mf_wfm_potal_main_wfm_content_sel_cpab_kncd_input_0"
        try:
            self.driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
            time.sleep(0.3)
            elem = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, sel_id)))
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
            time.sleep(0.3)
            Select(elem).select_by_visible_text("현재유효사항")
            time.sleep(0.3)
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", elem)
            time.sleep(0.3)
            logger.info("[현재유효사항] 선택")
            return True
        except Exception as e:
            logger.warning(f"[현재유효사항] 실패: {e}")
            return False

    def is_closed_registry(self):
        """v2.14: 검색결과 테이블에서 선택된 행의 등기상태가 '폐쇄'인지 감지

        검색결과 테이블 컬럼 순서: 체크박스 | 부동산고유번호 | 부동산구분 | 부동산표시 | 소유자 | 등기상태
        등기상태는 마지막(6번째) 컬럼이며, 폐쇄 시 빨간색 텍스트로 표시됨.
        """
        try:
            # 방법1: WebSquare gridView 데이터에서 직접 읽기
            closed = self.driver.execute_script("""
                // WebSquare gridView에서 선택된 행의 등기상태 컬럼 확인
                // gridView의 체크된 행 데이터를 읽는다
                try {
                    // 체크된(선택된) 행 찾기: 체크박스가 체크된 tr의 마지막 td
                    var checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
                    for (var c = 0; c < checkboxes.length; c++) {
                        var row = checkboxes[c].closest('tr');
                        if (!row) continue;
                        var cells = row.querySelectorAll('td');
                        if (cells.length < 3) continue;  // 헤더의 전체선택 체크박스 제외
                        // 마지막 셀이 등기상태
                        var lastCell = cells[cells.length - 1];
                        var statusText = (lastCell.textContent || '').trim();
                        if (statusText === '폐쇄') {
                            return true;
                        }
                    }
                } catch(e) {}

                // 방법2: gridView 내 데이터 행에서 '폐쇄' 텍스트를 가진 셀 확인
                // 등기상태 컬럼(마지막 컬럼)의 텍스트만 확인
                try {
                    var dataRows = document.querySelectorAll('tr[data-rowindex], tr[class*="w2grid"]');
                    for (var r = 0; r < dataRows.length; r++) {
                        var cells = dataRows[r].querySelectorAll('td');
                        if (cells.length < 3) continue;
                        var lastCell = cells[cells.length - 1];
                        var txt = (lastCell.textContent || '').trim();
                        if (txt === '폐쇄') {
                            return true;
                        }
                    }
                } catch(e) {}

                // 방법3: 빨간색(color: red 계열) 텍스트 중 '폐쇄'인 것 확인
                // 인터넷등기소에서 폐쇄 등기상태는 빨간색으로 표시됨
                try {
                    var spans = document.querySelectorAll('td span, td div, td');
                    for (var s = 0; s < spans.length; s++) {
                        var txt = (spans[s].textContent || '').trim();
                        if (txt !== '폐쇄') continue;
                        // 자식 요소가 없거나 최소한의 leaf 노드인지 확인 (정확한 매칭)
                        if (spans[s].children.length > 2) continue;
                        var style = window.getComputedStyle(spans[s]);
                        var color = style.color || '';
                        // 빨간색 계열 확인 (rgb(255,0,0), red, #ff0000 등)
                        if (color.indexOf('255') >= 0 && color.indexOf('0') >= 0) {
                            return true;
                        }
                        // 클래스에 red, error, closed 등이 포함된 경우
                        var cls = (spans[s].className || '') + ' ' + (spans[s].parentElement.className || '');
                        if (cls.match(/red|error|closed|close/i)) {
                            return true;
                        }
                    }
                } catch(e) {}

                return false;
            """)
            if closed:
                logger.info("[폐쇄] 등기상태 감지 → 유형 변경 없이 진행")
                return True
        except Exception as e:
            logger.warning(f"폐쇄 감지 중 오류: {e}")

        return False



    # ── 결제대상/중복결제 화면 판별 ─────────────────────────

    def _get_body_text(self):
        try:
            return self.driver.execute_script(
                "return (document.body && (document.body.innerText || document.body.textContent)) || '';"
            ) or ""
        except Exception:
            try:
                return self.driver.find_element(By.TAG_NAME, "body").text or ""
            except Exception:
                return ""

    def _is_pending_case_page(self):
        """v3.3: '신청사건 처리중' 페이지인지 감지 (다음 클릭 실패 시에만 호출)"""
        try:
            text = self._get_body_text()
            if "신청사건 처리중" in text:
                return True
            if "등기신청사건 처리여부" in text:
                return True
        except Exception:
            pass
        return False

    # ── v5.5: 처리중 변경 안내 팝업 ('등기신청사건이 접수되어...') 처리 ───
    #
    # 본문 식별 키워드: 사진과 실 페이지 텍스트 기준
    #   "등기신청사건이 접수"
    #   "변경 사항이 반영"
    #   "출력을 원하지 않으면"
    # 위 셋 중 하나만 매치되어도 처리중 변경 안내 팝업으로 판정.
    _PENDING_MODAL_KEYWORDS = (
        "등기신청사건이 접수",
        "변경 사항이 반영",
        "출력을 원하지 않으면",
    )

    def _detect_pending_case_modal(self):
        """v5.5: 처리중 변경 안내 팝업이 현재 화면에 떠있는지 본문 문구로 감지.

        Returns:
          bool — 떠있으면 True.
        """
        try:
            keywords_js = "[" + ",".join(
                '"' + k.replace('"', '\\"') + '"'
                for k in self._PENDING_MODAL_KEYWORDS
            ) + "]"
            visible = self.driver.execute_script(f"""
                var kws = {keywords_js};
                var body = document.body;
                if (!body) return false;
                // 보이는 모달 후보를 모두 훑되, 본문에 키워드 매치만 인정.
                var nodes = document.querySelectorAll('div, section, article');
                for (var i = 0; i < nodes.length; i++) {{
                    var el = nodes[i];
                    var s = window.getComputedStyle(el);
                    if (s.display === 'none' || s.visibility === 'hidden') continue;
                    if (el.offsetParent === null) continue;
                    var txt = (el.innerText || el.textContent || "");
                    if (txt.length > 2000) continue;   // 너무 큰 영역은 페이지 본문
                    for (var k = 0; k < kws.length; k++) {{
                        if (txt.indexOf(kws[k]) !== -1) return true;
                    }}
                }}
                return false;
            """)
            return bool(visible)
        except Exception as e:
            logger.debug(f"처리중 팝업 감지 중 예외 (무시): {e}")
            return False

    def _click_confirm_in_pending_modal(self):
        """v5.5: 처리중 안내 모달의 '확인' 버튼만 정확히 클릭.

        '취소' 가 아니라 '확인' 을 눌러야 다음 사이클로 진행됨. 모달 내부에
        있는 버튼 중 텍스트가 '확인' 인 것만 클릭.
        """
        try:
            keywords_js = "[" + ",".join(
                '"' + k.replace('"', '\\"') + '"'
                for k in self._PENDING_MODAL_KEYWORDS
            ) + "]"
            clicked = self.driver.execute_script(f"""
                var kws = {keywords_js};
                // 본문 키워드를 포함한 모달 컨테이너 찾기
                var nodes = document.querySelectorAll('div, section, article');
                var modal = null;
                for (var i = 0; i < nodes.length; i++) {{
                    var el = nodes[i];
                    var s = window.getComputedStyle(el);
                    if (s.display === 'none' || s.visibility === 'hidden') continue;
                    if (el.offsetParent === null) continue;
                    var txt = (el.innerText || el.textContent || "");
                    if (txt.length > 2000) continue;
                    var hit = false;
                    for (var k = 0; k < kws.length; k++) {{
                        if (txt.indexOf(kws[k]) !== -1) {{ hit = true; break; }}
                    }}
                    if (hit) {{
                        modal = el;
                        break;
                    }}
                }}
                if (!modal) return false;
                // 모달 내부의 '확인' 버튼 클릭
                var btns = modal.querySelectorAll('a, button, input[type="button"], input[type="submit"]');
                for (var j = 0; j < btns.length; j++) {{
                    var b = btns[j];
                    var t = (b.textContent || b.value || "").trim();
                    if (t === '확인' && b.offsetParent !== null) {{
                        b.click();
                        return true;
                    }}
                }}
                return false;
            """)
            return bool(clicked)
        except Exception as e:
            logger.debug(f"처리중 팝업 확인 클릭 중 예외 (무시): {e}")
            return False

    def _handle_pending_case_popup(self, initial_wait=1.0, max_close_attempts=10,
                                   close_wait=2.0, recheck_wait=1.5):
        """v5.5 재작성: 변경 예정 안내 팝업이 떴으면 닫고, 안 떴으면 빠르게 패스.

        흐름:
          1. DOM 즉시 검사. 떠있으면 곧장 닫기 단계로.
          2. 안 떠있으면 initial_wait (기본 1초) 동안 짧게 폴링 — 늦게 뜨는
             경우 대비. 그래도 안 뜨면 정상 종료 (총 ~1초 소요).
          3. 떠있으면: '확인' 클릭 → 모달 사라질 때까지 close_wait (기본 2초)
             폴링 → 사라진 뒤 recheck_wait (기본 1.5초) 동안 재발 감시.
             재발하면 또 닫음. v5.6: 최대 max_close_attempts (기본 10) 회 반복.
          4. 어떤 경로로든 끝나면 True 반환 (단 안 닫힌 상태로 끝나면 False).

        Returns:
          bool — 호출 종료 시점에 모달이 더 이상 보이지 않으면 True.
                 (False 면 클릭이 안 먹는 상태라 호출자가 대응 필요)

        v3.3~v5.4: alert 3초 + DOM '확인' 1회 클릭 방식이었음. 본문 식별이
        없어서 다른 모달과 혼동 우려가 있었고, 연쇄 팝업 케이스를 못 처리.

        v5.6: 로그 라벨을 '[처리중 안내 팝업]' → '[변경 예정 안내 팝업]' 으로
              변경 (실제 팝업 본문 의미와 일치). 기본 시도 횟수 5 → 10.
        """
        # 1) 우선 alert (native) 인지 짧게 확인. 알림창이면 그게 우선.
        try:
            alert = WebDriverWait(self.driver, 0.3).until(EC.alert_is_present())
            alert_text = alert.text
            logger.info(f"[변경 예정 안내(alert)] {alert_text[:80]}")
            alert.accept()
            time.sleep(0.3)
            return True
        except TimeoutException:
            pass

        # 2) DOM 모달 즉시 검사
        present = self._detect_pending_case_modal()

        # 3) 즉시 안 보이면 짧게 추가 폴링 (서버 응답 지연으로 늦게 뜨는 경우)
        if not present:
            deadline = time.time() + initial_wait
            poll = 0.2
            while time.time() < deadline:
                if self._detect_pending_case_modal():
                    present = True
                    break
                time.sleep(poll)

        # 4) 안 떴으면 정상 종료 (정상 사이클: 약 1초 소요)
        if not present:
            return True

        # 5) 떴으면 닫기 + 재발 감시 루프
        logger.info("[변경 예정 안내 팝업] 감지 → 닫기 시도")
        for attempt in range(1, max_close_attempts + 1):
            if not self._detect_pending_case_modal():
                # 사라진 상태 → 끝
                return True

            clicked = self._click_confirm_in_pending_modal()
            if not clicked:
                logger.warning(
                    f"[변경 예정 안내 팝업] '확인' 버튼 클릭 실패 "
                    f"(시도 {attempt}/{max_close_attempts})"
                )
                time.sleep(0.5)
                continue

            logger.info(f"[변경 예정 안내 팝업] '확인' 클릭 (시도 {attempt}/{max_close_attempts})")
            # 모달이 사라질 때까지 close_wait 동안 폴링
            disappeared = False
            deadline = time.time() + close_wait
            while time.time() < deadline:
                if not self._detect_pending_case_modal():
                    disappeared = True
                    break
                time.sleep(0.2)

            if not disappeared:
                logger.warning(
                    f"[변경 예정 안내 팝업] {close_wait:.0f}초 내 사라지지 않음 → 재시도"
                )
                continue

            # 잠깐 재발 감시 (연쇄 팝업 케이스 대비)
            deadline = time.time() + recheck_wait
            recurred = False
            while time.time() < deadline:
                if self._detect_pending_case_modal():
                    recurred = True
                    break
                time.sleep(0.2)

            if not recurred:
                return True
            logger.info("[변경 예정 안내 팝업] 재발 감지 → 다시 닫기")

        logger.error(
            f"[변경 예정 안내 팝업] {max_close_attempts}회 시도해도 닫히지 않음 → 계속 진행"
        )
        return False

    def _wait_until_modal_dismissed(self, max_wait=3.0, poll=0.2):
        """
        v4.4: 화면 위에 떠 있는 모달/확인 팝업이 사라질 때까지 짧게 폴링.
        고정 time.sleep(3) 을 대체하기 위한 능동 대기.

        매칭 대상 (이 중 하나라도 보이면 '아직 팝업이 떠 있다' 로 간주):
          - div.w2modal_popup[style*="display: block"]     (일반 팝업)
          - div#_modal[style*="display: block"]            (구형 모달)
          - div[id*="processbar"][style*="display: block"] (처리중 오버레이)

        모든 팝업이 사라진 순간 즉시 반환. max_wait 초 내에 안 사라지면 그대로 반환.
        처리중 오버레이가 좀비 상태로 오래 남는 경우는 별도로 _kill_processbar_overlay
        가 예외 기반으로 잡아주므로 여기서는 건드리지 않는다.

        Returns:
          True  - max_wait 내에 모달이 사라짐
          False - max_wait 까지 팝업이 남아있음 (호출측은 그래도 계속 진행)
        """
        deadline = time.time() + max_wait
        try:
            while time.time() < deadline:
                visible = self.driver.execute_script("""
                    var sel = 'div.w2modal_popup, div#_modal, div[id*="processbar"]';
                    var nodes = document.querySelectorAll(sel);
                    for (var i = 0; i < nodes.length; i++) {
                        var s = window.getComputedStyle(nodes[i]);
                        if (s.display !== 'none' && s.visibility !== 'hidden') {
                            return true;
                        }
                    }
                    return false;
                """)
                if not visible:
                    return True
                time.sleep(poll)
        except Exception as e:
            logger.debug(f"모달 대기 중 오류 (무시): {e}")
        return False

    def is_duplicate_payment_page(self):
        """
        v4.8: 중복결제 확인 페이지 판별.
        고유 신호 (스크린샷 기준):
          - 제목 '중복결제 확인'
          - 안내 '다음의 부동산은 이미 결제하여 열람발급이 가능하거나 요청 처리중입니다'
        """
        try:
            text = self._get_body_text()
            if "중복결제 확인" in text:
                return True
            # 보조 신호: '이미 결제' 또는 '이미 결재' + 안내문 핵심 토큰
            if ("이미 결제" in text or "이미 결재" in text) and \
               ("요청 처리중" in text or "처리중입니다" in text or "결제대상목록" in text):
                return True
        except Exception:
            pass
        return False

    def is_pending_case_branch_page(self):
        """
        v4.8: '등기신청사건 처리여부 확인' 분기 페이지 판별.
        스크린샷 기준 본문 키워드:
          - 제목 '등기신청사건 처리여부 확인'
          - 빨간 강조 '신청사건 처리중인 등기부 입니다'
        주의: 기존 _is_pending_case_page 는 '다음 클릭 실패 시' 호출용으로
              남겨두고, 분기 폴링용은 조금 더 엄격하게 페이지 단위 키워드만 본다.
        """
        try:
            text = self._get_body_text()
            if "등기신청사건 처리여부" in text:
                return True
            if "신청사건 처리중인 등기부" in text:
                return True
        except Exception:
            pass
        return False

    def is_normal_final_branch_page(self):
        """
        v4.8: '(주민)등록번호 공개여부 확인' 정상 페이지 판별.
        스크린샷 기준 본문 키워드:
          - 제목 '(주민)등록번호 공개여부 확인'
          - 라디오 라벨 '미공개', '특정인공개'
          - 안내 '미공개'선택 시 등기기록에 기재된 (주민)등록번호 뒤 7자리는 미공개
        """
        try:
            text = self._get_body_text()
            if "(주민)등록번호 공개여부" in text:
                return True
            # 라디오 라벨 양쪽이 동시에 보이고, 다른 분기 키워드는 없을 때
            if ("미공개" in text and "특정인공개" in text
                    and "중복결제" not in text
                    and "신청사건 처리중인 등기부" not in text):
                return True
        except Exception:
            pass
        return False

    def wait_for_branch_after_type_next(self,
                                        timeout=BRANCH_DETECT_TIMEOUT,
                                        poll=BRANCH_DETECT_POLL):
        """
        v4.8: 유형선택 '다음' 클릭 직후 발생 가능한 3가지 분기를 폴링으로
        결정적으로 판별한다.

        Returns:
          "duplicate" - 중복결제 확인 페이지
          "pending"   - 등기신청사건 처리여부 확인 페이지
          "final"     - (주민)등록번호 공개여부 확인 (정상 최종확인 직전) 페이지
          None        - timeout 안에 셋 다 안 나타남 (호출측은 retry)

        검사 우선순위:
          1) alert (중복결제/이미결제 안내가 alert 로 뜨는 케이스)
          2) duplicate  (가장 먼저 끝내야 하는 케이스)
          3) pending    (다음 1번 더 눌러야 하는 케이스)
          4) final      (정상 흐름)
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            # 1) alert 우선 처리
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text or ""
                if any(k in alert_text for k in
                       ("중복결제", "이미 결제", "이미 결재")):
                    logger.info(f"중복결제 alert 감지: {alert_text[:60]}")
                    try:
                        alert.accept()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    return "duplicate"
                # 그 외 alert 는 그냥 수락 후 계속 폴링
                logger.info(f"분기 대기 중 alert: {alert_text[:60]}")
                try:
                    alert.accept()
                except Exception:
                    pass
                time.sleep(0.3)
            except NoAlertPresentException:
                pass
            except Exception:
                pass

            # 2) 중복결제 (가장 먼저 검사 — 이걸 놓치면 중복 추가 사고 발생)
            if self.is_duplicate_payment_page():
                return "duplicate"

            # 3) 신청사건 처리중
            if self.is_pending_case_branch_page():
                return "pending"

            # 4) 정상 (주민등록번호 공개여부) 페이지
            if self.is_normal_final_branch_page():
                return "final"

            time.sleep(poll)

        # 타임아웃: 마지막으로 한 번 더 본다 (poll 간격 사이에 렌더된 경우 대비)
        if self.is_duplicate_payment_page():
            return "duplicate"
        if self.is_pending_case_branch_page():
            return "pending"
        if self.is_normal_final_branch_page():
            return "final"
        return None

    def is_payment_target_page(self):
        try:
            text = self._get_body_text()
            if "결제대상 확인" in text and ("일괄결제" in text or "선택삭제" in text or "장바구니목록" in text):
                return True
            if re.search(r"전체\s*\d+\s*건", text):
                return True
        except Exception:
            pass
        return False

    def wait_for_payment_result_page(self, timeout=PAYMENT_PAGE_WAIT_TIMEOUT):
        deadline = time.time() + timeout
        last_state = None

        while time.time() < deadline:
            self._dismiss_any_alert()

            if self.is_duplicate_payment_page():
                logger.info("중복결제 확인 페이지 감지 → 이미 성공한 것으로 처리")
                return "duplicate"

            if self.is_payment_target_page():
                logger.info("결제대상 확인 화면 로드 완료")
                return "payment"

            try:
                ready_state = self.driver.execute_script("return document.readyState")
                current_url = self.driver.current_url or ""
                current_title = self.driver.title or ""
                state = f"{ready_state}|{current_title}|{current_url}"
                if state != last_state:
                    logger.info(f"결제대상 화면 대기 중... ({ready_state})")
                    last_state = state
            except Exception:
                pass

            time.sleep(1)

        logger.warning(f"결제대상/중복결제 화면 대기 {timeout}초 초과")
        return None

    # ── 결제대상 건수 검증 ────────────────────────────────

    def _extract_payment_count(self):
        texts = []

        try:
            body_text = self._get_body_text()
            if body_text:
                texts.append(body_text)
        except Exception:
            pass

        xpaths = [
            "//*[contains(normalize-space(.), '전체') and contains(normalize-space(.), '건')]",
            "//*[contains(normalize-space(.), '결제대상 확인')]/following::*[contains(normalize-space(.), '전체')]",
            "//*[contains(@class, 'total') or contains(@class, 'count')]",
        ]

        for xpath in xpaths:
            try:
                elems = self.driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    try:
                        if elem.is_displayed():
                            txt = (elem.text or "").strip()
                            if txt:
                                texts.append(txt)
                    except Exception:
                        continue
            except Exception:
                continue

        patterns = [
            r"전체\s*([0-9]+)\s*건",
            r"전체\s*([0-9]+)",
        ]

        for txt in texts:
            compact = re.sub(r"\s+", " ", txt)
            for pat in patterns:
                m = re.search(pat, compact)
                if m:
                    return int(m.group(1)), compact

        return None, None

    def _count_payment_rows_in_table(self):
        """
        v4.9: 결제대상 테이블의 실제 데이터 행(tr) 개수를 센다.
        '전체 N건' 텍스트가 잠깐 0 으로 보일 때(테이블 미채워짐) 보조 검증용.
        Returns:
          int  - 감지한 데이터 행 수 (0 가능)
          None - 테이블 자체를 못 찾음
        """
        try:
            # 결제대상 테이블 안의 데이터 행만 카운트.
            # 헤더(thead)/빈 안내(td colspan) 제외.
            count = self.driver.execute_script("""
                // 결제대상 테이블 후보 탐색
                var tables = document.querySelectorAll('table');
                var maxData = -1;
                for (var i = 0; i < tables.length; i++) {
                    var t = tables[i];
                    var caption = (t.caption && t.caption.textContent) || '';
                    var headText = '';
                    var thead = t.querySelector('thead');
                    if (thead) headText = thead.textContent || '';
                    // '부동산 고유번호' + '수수료' 가 동시에 들어간 표가 결제대상 표
                    var marker = caption + ' ' + headText;
                    if (marker.indexOf('부동산 고유번호') < 0 || marker.indexOf('수수료') < 0) {
                        continue;
                    }
                    var tbody = t.querySelector('tbody') || t;
                    var rows = tbody.querySelectorAll('tr');
                    var dataRows = 0;
                    for (var j = 0; j < rows.length; j++) {
                        var tds = rows[j].querySelectorAll('td');
                        if (tds.length === 0) continue;
                        // colspan 이 1보다 큰 단일 셀 = 빈 안내행
                        if (tds.length === 1) {
                            var cs = parseInt(tds[0].getAttribute('colspan') || '1', 10);
                            if (cs > 1) continue;
                        }
                        // 부동산 고유번호 형식(####-####-######)이 한 셀에 보여야 데이터 행
                        var rowText = rows[j].textContent || '';
                        if (/\\d{4}-\\d{4}-\\d{6}/.test(rowText)) {
                            dataRows++;
                        }
                    }
                    if (dataRows > maxData) maxData = dataRows;
                }
                return maxData;  // -1 이면 테이블 자체 없음
            """)
            if count is None or count < 0:
                return None
            return int(count)
        except Exception as e:
            logger.debug(f"테이블 행 카운트 실패 (무시): {e}")
            return None

    def verify_payment_count(self, expected, timeout=12):
        """
        v4.9: 결제대상 건수 검증을 폴링 기반으로 강화.

        기존 v4.8 버그:
          페이지 골격(제목/일괄결제 버튼)은 빨리 로드되지만 테이블 데이터가
          채워지기 전에 _extract_payment_count() 가 '전체 0건' 을 한 번 잡아
          버리면 즉시 False 반환 → 잘 추가됐는데도 건수 불일치 재시도가 발생.

        수정 v4.9:
          1) 0건 또는 expected 미만이 추출되어도 즉시 False 하지 않고
             timeout 까지 0.5초 간격으로 폴링.
          2) 추출된 카운트가 expected 와 일치하는 즉시 True.
          3) DOM 테이블 행 수도 같이 보아서, 텍스트 카운트와 행 수가
             동시에 expected 에 도달할 때만 안전하게 True.
          4) timeout 내내 0/미달이면 그때야 False 반환 (마지막 카운트 로깅).
        """
        deadline = time.time() + timeout
        last_actual = None
        last_text   = None
        last_rows   = None

        while time.time() < deadline:
            # 중복결제 페이지로 빠진 케이스(다음 진행 후 중복 응답) 우선 처리
            if self.is_duplicate_payment_page():
                logger.info("중복결제 확인 페이지 기준으로 이미 성공 처리")
                return True

            if not self.is_payment_target_page():
                time.sleep(0.5)
                continue

            actual, matched_text = self._extract_payment_count()
            rows = self._count_payment_rows_in_table()

            if actual is not None:
                last_actual = actual
                last_text   = matched_text
            if rows is not None:
                last_rows = rows

            # 정상 일치: 텍스트 카운트 우선, DOM 행수 보조
            if actual == expected:
                # 행수도 같이 봐서 동기화 확인 (행수 None 이면 텍스트만 신뢰)
                if rows is None or rows >= expected:
                    logger.info(f"✓ 결제대상 {actual}건 확인 (예상 {expected}건)")
                    return True
                # 텍스트는 일치하지만 행이 아직 미반영 → 잠깐 더 대기
                time.sleep(0.5)
                continue

            # DOM 행수 기준이라도 expected 에 도달했다면 OK
            if rows is not None and rows >= expected:
                logger.info(f"✓ 결제대상 {rows}건 확인 (DOM 행 기준, 예상 {expected}건)")
                return True

            # 아직 0건이거나 미달 → 폴링 계속
            time.sleep(0.5)

        # 타임아웃
        if last_actual is None and last_rows is None:
            logger.warning("건수 텍스트/테이블 모두 못 찾음")
            return False
        if last_actual is not None and last_actual != expected:
            logger.warning(
                f"✗ 건수 불일치: {last_actual}건 ≠ 예상 {expected}건 "
                f"(DOM 행={last_rows}) | 감지텍스트: {last_text}"
            )
        elif last_rows is not None:
            logger.warning(
                f"✗ DOM 행 불일치: {last_rows}행 ≠ 예상 {expected}건 "
                f"(텍스트 카운트={last_actual})"
            )
        return False

    # ── 단일 처리 ─────────────────────────────────────────

    def process_single(self, property_id, display_id):
        try:
            if self.is_duplicate_payment_page():
                logger.info(f"중복결제 페이지에서 시작됨 → 이미 성공 처리: {display_id}")
                return "duplicate"

            if not self.click_realty_view_issue():
                return "retry"
            self.handle_existing_payment_popup()
            time.sleep(0.3)

            if self.is_duplicate_payment_page():
                logger.info(f"중복결제 페이지 감지 → 이미 성공 처리: {display_id}")
                return "duplicate"

            if not self.select_unique_number_tab():
                return "retry"
            if not self.enter_property_id_and_search(property_id):
                return "retry"

            # v2.14: 검색결과 화면에서 폐쇄 등기 여부 미리 감지
            is_closed = self.is_closed_registry()

            if not self.click_next_button("다음(검색결과)"):
                return "retry"

            # 검색결과 다음 클릭 후 중복결제 확인 체크
            if self.is_duplicate_payment_page():
                logger.info(f"검색결과 다음 후 중복결제 감지 → 성공 처리: {display_id}")
                return "duplicate"

            # v2.14: 폐쇄 등기 → 유형 변경 없이 바로 다음 클릭
            if is_closed:
                logger.info(f"[폐쇄] 유형 변경 건너뜀 → 바로 다음 클릭: {display_id}")
                if display_id not in self.closed_items:
                    self.closed_items.append(display_id)
                    # v5.0: 메모리 리스트에 추가하는 즉시 디스크에도 기록.
                    #       작업이 중간에 중단되어도 폐쇄 고유번호를 잃지 않도록
                    #       바탕화면의 오늘날짜 폴더 내 파일에 한 줄 append.
                    self._append_closed_item_immediate(display_id)
            else:
                if not self.select_current_valid_option():
                    return "retry"
            if not self.click_next_button("다음(유형선택)"):
                return "retry"

            # v4.8: 유형선택 '다음' 클릭 후 발생 가능한 3가지 분기를 폴링으로
            # 결정적으로 판별. 페이지가 렌더되기 전에 즉시 1회만 보던 v4.7 의
            # 사고(중복결제 페이지의 '다음' 을 눌러 중복 추가) 를 막기 위함.
            #   1) duplicate → 성공 처리하고 메인으로 (다음 작업 진행)
            #   2) pending   → '다음' 한 번 더 눌러 정상 흐름으로 복귀
            #   3) final     → 그대로 '다음(최종확인)' 진행
            #   None         → 셋 다 미감지 → retry
            branch = self.wait_for_branch_after_type_next()

            if branch == "duplicate":
                logger.info(f"유형선택 다음 후 중복결제 감지 → 성공 처리: {display_id}")
                return "duplicate"

            if branch == "pending":
                logger.info(f"신청사건 처리중 감지 → 다음 클릭 후 정상 흐름 진입: {display_id}")
                if not self.click_next_button("다음(처리중 통과)"):
                    return "retry"
                # 처리중 통과 후에는 정상 페이지(주민등록번호 공개여부)가 떠야 함.
                # 방어적으로 한 번 더 분기 폴링 (드물게 처리중→중복결제로 빠질 수도).
                branch2 = self.wait_for_branch_after_type_next(timeout=4.0)
                if branch2 == "duplicate":
                    logger.info(f"처리중 통과 후 중복결제 감지 → 성공 처리: {display_id}")
                    return "duplicate"
                if branch2 is None:
                    # 정상 페이지도 중복결제도 신청사건도 아님 → 재시도
                    logger.warning(f"처리중 통과 후 분기 페이지 미감지 → 재시도: {display_id}")
                    return "retry"
                # branch2 == "final" 또는 "pending"(드문 케이스) → 정상 흐름 진행

            elif branch is None:
                # 어느 분기에도 해당하지 않음 (서버 응답 지연/빈 화면/예상 외 페이지)
                # 여기서 무리하게 '다음' 을 눌러 중복결제 페이지를 건너뛰던
                # 기존 사고를 막기 위해 곧바로 재시도 처리.
                logger.warning(f"유형선택 다음 후 분기 페이지 미감지 ({BRANCH_DETECT_TIMEOUT}s) → 재시도: {display_id}")
                # 혹시 alert 가 남아있다면 정리
                self._dismiss_any_alert()
                return "retry"

            # branch == "final" 또는 pending→final 통과: 정상 최종확인 다음 클릭
            if not self.click_next_button("다음(최종확인)"):
                if self.is_duplicate_payment_page():
                    logger.info(f"최종확인 다음 실패했으나 중복결제 감지 → 성공 처리: {display_id}")
                    return "duplicate"
                if self.is_payment_target_page():
                    logger.info(f"최종확인 다음 실패했으나 결제대상 화면 감지 → 성공: {display_id}")
                    return "success"
                return "retry"

            # v4.7: 단기(3초) 타임아웃 + 추가 다음 우회 로직 제거
            #       결제대상/중복결제 페이지가 뜰 때까지 정상 타임아웃으로 한 번만 대기
            result = self.wait_for_payment_result_page(PAYMENT_PAGE_WAIT_TIMEOUT)
            if result == "payment":
                logger.info(f"결제대상 추가: {display_id}")
                return "success"
            if result == "duplicate":
                logger.info(f"중복결제 확인으로 성공 처리: {display_id}")
                return "duplicate"

            logger.warning(f"결제대상 화면 진입 지연 → 재시도 대상: {display_id}")
            return "retry"

        except UnexpectedAlertPresentException:
            self._dismiss_any_alert()
            return "retry"
        except Exception as e:
            logger.error(f"처리 실패 [{display_id}]: {e}")
            self._dismiss_any_alert()
            return "retry"

    # ══════════════════════════════════════════════════════════
    # v3.1/3.2 – 후속 자동화
    # ══════════════════════════════════════════════════════════

    def click_batch_payment(self):
        """페이지 하단의 '일괄결제' 버튼 클릭"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception:
            pass

        clicked = self.driver.execute_script("""
            var links = document.querySelectorAll('a, button, input[type="button"]');
            for (var i = 0; i < links.length; i++) {
                var txt = (links[i].textContent || links[i].value || '').trim();
                if (txt === '일괄결제') {
                    links[i].scrollIntoView({block:'center'});
                    links[i].click();
                    return true;
                }
            }
            for (var i = 0; i < links.length; i++) {
                var txt = (links[i].textContent || links[i].value || '').trim();
                if (txt.indexOf('일괄결제') >= 0 && txt.indexOf('열람') < 0 && txt.indexOf('저장') < 0) {
                    links[i].scrollIntoView({block:'center'});
                    links[i].click();
                    return true;
                }
            }
            return false;
        """)
        if clicked:
            logger.info("[일괄결제] 버튼 클릭")
            time.sleep(1)
            self._handle_alert(accept=True)
            return True

        logger.error("[일괄결제] 버튼을 찾을 수 없습니다")
        return False

    def wait_for_manual_payment(self):
        """사용자에게 수기 결제를 안내하고 오버레이의 '일괄저장 시작' 버튼 클릭을 대기.

        v5.1: 기존엔 cmd 창에서 Enter 입력을 받았으나, 사용자가 결제 후 cmd 창
              포커스를 다시 잡기 번거로워 오버레이 버튼 클릭으로 변경.
              오버레이/컨트롤러를 사용할 수 없으면 기존 input() 방식으로 폴백.
        """
        logger.info("=" * 60)
        logger.info("★ 수동 결제 완료 후 오버레이의 '▶▶ 일괄저장' 버튼을 누르세요 ★")
        logger.info("=" * 60)
        print("\n" + "=" * 60)
        print("★★★ 수동 결제 후 오버레이의 '▶▶ 일괄저장' 버튼을 클릭하세요 ★★★")
        print("    (오버레이가 비활성화된 환경에서는 이 창에서 Enter 를 누르세요)")
        print("=" * 60 + "\n")

        # v5.1: 오버레이 + 컨트롤러가 모두 살아있으면 버튼 클릭을 기다리고,
        #       어느 하나라도 없으면 기존 Enter 입력 방식으로 폴백.
        use_button = (_overlay is not None) and (_pause is not None)

        if use_button:
            try:
                # 다음 대기를 위해 이전 시그널이 남아있을 가능성 차단
                _pause.reset_batch_save()
                # 오버레이의 일괄저장 시작 버튼을 활성화 (녹색 강조)
                _overlay.set_batch_save_enabled(True)
                overlay_status("Phase 2: 수기 결제 후 '▶▶ 일괄저장' 클릭")
                # 버튼 클릭(또는 중단) 까지 블로킹. StopRequested 는 상위로 전파.
                _pause.wait_for_batch_save()
            finally:
                # 클릭됐든 중단됐든 다음 단계 진입 전 버튼은 비활성화
                try:
                    _overlay.set_batch_save_enabled(False)
                except Exception:
                    pass
            logger.info("일괄저장 시작 버튼 클릭 감지 → 후속 작업 진행")
        else:
            # 폴백: 기존 동작 그대로 (cmd 창 Enter)
            try:
                input()
            except Exception:
                pass
            logger.info("엔터 입력 감지 → 후속 작업 진행")

        time.sleep(1)

    def _extract_unissued_count(self):
        """미발급 전체 건수를 추출 (전체 N건 형태)"""
        try:
            body_text = self._get_body_text()
            m = re.search(r"전체\s*(\d+)\s*건", body_text)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return None

    def click_select_all_checkbox(self):
        """'전체 N 건' 표시 바로 밑 전체체크 박스를 클릭

        v3.2 개선: 인터넷등기소(WebSquare) 그리드는 일반 <input type="checkbox">
        외에도 <div>, <span>, <img> 등 커스텀 요소를 체크박스로 사용할 수 있음.
        스크린샷 기준으로 '전체 20 건' 텍스트 아래 테이블 헤더행의
        첫 번째 셀(번호 컬럼 왼쪽)에 전체선택 체크박스가 위치.
        """
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception:
            pass

        result = self.driver.execute_script("""
            // ─── 전략 1: WebSquare gridView의 헤더 체크박스 ───
            // WebSquare grid에서 헤더의 전체선택은 보통
            // w2grid_column_header_* 또는 gridView 헤더 영역에 있음
            var gridHeaders = document.querySelectorAll(
                '[class*="w2grid"] [class*="header"] input[type="checkbox"], ' +
                '[class*="w2grid"] thead input[type="checkbox"], ' +
                '[class*="grid"] [class*="header"] input[type="checkbox"]'
            );
            for (var i = 0; i < gridHeaders.length; i++) {
                if (gridHeaders[i].offsetParent !== null) {
                    gridHeaders[i].click();
                    return 'grid_header_cb';
                }
            }

            // ─── 전략 2: 일반 th 안의 체크박스 ───
            var thCbs = document.querySelectorAll('th input[type="checkbox"], thead input[type="checkbox"]');
            for (var i = 0; i < thCbs.length; i++) {
                if (thCbs[i].offsetParent !== null) {
                    thCbs[i].click();
                    return 'th_cb';
                }
            }

            // ─── 전략 3: '전체 N 건' 텍스트 이후 첫 번째 체크박스 (위치 기반) ───
            // '전체 N 건' 요소를 찾고, 그 아래(DOM 순서상 뒤)에 있는 첫 체크박스
            var walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, null, false);
            var totalNode = null;
            while (walker.nextNode()) {
                var txt = walker.currentNode.textContent.trim();
                if (/^전체\\s*\\d+\\s*건$/.test(txt)) {
                    totalNode = walker.currentNode.parentElement;
                    break;
                }
            }
            if (totalNode) {
                // totalNode 이후의 모든 요소에서 체크박스 찾기
                var allAfter = document.querySelectorAll('input[type="checkbox"]');
                var totalRect = totalNode.getBoundingClientRect();
                for (var i = 0; i < allAfter.length; i++) {
                    var cb = allAfter[i];
                    if (cb.offsetParent === null) continue;
                    var cbRect = cb.getBoundingClientRect();
                    // 전체 N 건 텍스트보다 아래에 있고, 가장 첫 번째인 것
                    if (cbRect.top >= totalRect.bottom - 5) {
                        cb.click();
                        return 'after_total_text';
                    }
                }
            }

            // ─── 전략 4: 커스텀 체크박스 (div/span/img 기반) ───
            // WebSquare는 체크박스를 div나 span으로 렌더링하기도 함
            // role="checkbox" 또는 체크박스 관련 클래스 찾기
            var customCbs = document.querySelectorAll(
                '[role="checkbox"], ' +
                '[class*="checkbox"], [class*="chk"], [class*="check"], ' +
                'div[class*="w2grid"] img[src*="chk"], ' +
                'div[class*="w2grid"] img[src*="check"]'
            );
            for (var i = 0; i < customCbs.length; i++) {
                var el = customCbs[i];
                if (el.offsetParent === null) continue;
                // 헤더 영역에 있는 것만 (데이터 행 제외)
                var parent = el;
                var isHeader = false;
                for (var p = 0; p < 10; p++) {
                    parent = parent.parentElement;
                    if (!parent) break;
                    var cls = (parent.className || '').toLowerCase();
                    var tag = parent.tagName.toLowerCase();
                    if (cls.indexOf('header') >= 0 || tag === 'thead' || tag === 'th') {
                        isHeader = true;
                        break;
                    }
                }
                if (isHeader) {
                    el.click();
                    return 'custom_header_cb';
                }
            }

            // ─── 전략 5: 페이지에서 가장 첫 번째 visible 체크박스 ───
            var allCbs = document.querySelectorAll('input[type="checkbox"]');
            for (var j = 0; j < allCbs.length; j++) {
                if (allCbs[j].offsetParent !== null) {
                    allCbs[j].click();
                    return 'first_visible_cb';
                }
            }

            return false;
        """)

        if result and result != False:
            logger.info(f"[전체선택] 체크박스 클릭 (방법: {result})")
            time.sleep(1)
            return True

        logger.error("[전체선택] 체크박스를 찾을 수 없습니다")
        return False

    def click_batch_view_print(self):
        """최하단에 '일괄열람출력' 버튼 클릭"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception:
            pass

        clicked = self.driver.execute_script("""
            var links = document.querySelectorAll('a, button, input[type="button"]');
            for (var i = 0; i < links.length; i++) {
                var txt = (links[i].textContent || links[i].value || '').replace(/\\s+/g, '').trim();
                if (txt.indexOf('일괄열람출력') >= 0) {
                    links[i].scrollIntoView({block:'center'});
                    links[i].click();
                    return true;
                }
            }
            return false;
        """)
        if clicked:
            logger.info("[일괄열람출력] 클릭")
            time.sleep(1)
            return True

        logger.error("[일괄열람출력] 버튼을 찾을 수 없습니다")
        return False

    def handle_batch_view_confirm_popup(self):
        """
        '일괄열람출력 진행 시...' 팝업에서 '확인' 클릭.

        v4.4: alert 대기 5초 → 1초로 단축. 인터넷등기소의 해당 팝업은 DOM 모달로
        뜨는 것이 관측되므로 alert 대기에 긴 시간을 쓰지 않는다. DOM 모달일
        경우 즉시 2단계로 폴백. 클릭 성공 시 짧은 대기(0.3초) 후 반환.
        """
        # 1) 혹시라도 native alert 인 경우 대비 (짧게 1초만)
        try:
            alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            alert_text = alert.text
            logger.info(f"일괄열람 확인 팝업(alert): {alert_text[:80]}")
            alert.accept()
            time.sleep(0.3)
            return True
        except TimeoutException:
            pass

        # 2) DOM 모달 내 '확인' 버튼 클릭 (실제 관측되는 케이스)
        try:
            confirmed = self.driver.execute_script("""
                var btns = document.querySelectorAll('a, button, input[type="button"]');
                for (var i = 0; i < btns.length; i++) {
                    var txt = (btns[i].textContent || btns[i].value || '').trim();
                    if (txt === '확인' && btns[i].offsetParent !== null) {
                        btns[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if confirmed:
                logger.info("[일괄열람 확인 팝업] '확인' 클릭")
                time.sleep(0.3)
                return True
        except Exception:
            pass

        logger.warning("일괄열람 확인 팝업을 찾을 수 없음")
        return False

    # v3.5: wait_for_processing_complete 삭제 (처리중 표시는 빠르게 사라져 대기 불필요)

    def click_batch_save(self):
        """'일괄저장' 버튼 클릭 — 실제 클릭 우선, JS click은 마지막 폴백.

        v5.4: 내부 클릭 동작은 _click_batch_save_button_once() 로 분리.
              본 메서드는 기존 호환을 위해 클릭 후 3초 대기까지 그대로 수행.
        """
        clicked = self._click_batch_save_button_once()
        if clicked:
            logger.info("[일괄저장] 클릭")
            time.sleep(3)
            self._handle_alert(accept=True)
            return True
        return False

    def _click_batch_save_button_once(self):
        """v5.4: 일괄저장 버튼을 한 번 클릭만 수행 (성공/실패 여부 반환).

        창 전환·스크롤·셀렉터 탐색·다양한 클릭 전략은 그대로지만, 클릭 후
        sleep / alert 처리는 호출자가 담당. 검증 로직과 결합할 때 중복
        대기를 피하기 위해 분리.
        """
        main_handle = None
        try:
            main_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles
            for handle in all_handles:
                if handle != main_handle:
                    self.driver.switch_to.window(handle)
                    logger.info(f"새 팝업 창으로 전환: {self.driver.title}")
                    break
        except Exception:
            pass

        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception:
            pass

        btn = None
        selectors = [
            "//a[normalize-space()='일괄저장']",
            "//button[normalize-space()='일괄저장']",
            "//input[@type='button' and @value='일괄저장']",
            "//a[contains(normalize-space(), '일괄저장')]",
            "//button[contains(normalize-space(), '일괄저장')]",
            "//input[@type='button' and contains(@value, '일괄저장')]",
        ]

        for xpath in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    try:
                        if elem.is_displayed():
                            btn = elem
                            break
                    except Exception:
                        continue
                if btn is not None:
                    break
            except Exception:
                continue

        if btn is None:
            logger.error("[일괄저장] 버튼을 찾을 수 없습니다")
            if main_handle:
                try:
                    self.driver.switch_to.window(main_handle)
                except Exception:
                    pass
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.2)
        except Exception:
            pass

        for action in (
            lambda: btn.click(),
            lambda: ActionChains(self.driver).move_to_element(btn).pause(0.1).click(btn).perform(),
            lambda: self.driver.execute_script(
                "arguments[0].focus();"
                "arguments[0].dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
                "arguments[0].dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
                "arguments[0].dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));",
                btn,
            ),
            lambda: self.driver.execute_script("arguments[0].click();", btn),
        ):
            try:
                action()
                return True
            except Exception:
                continue

        logger.error("[일괄저장] 클릭 실패")
        if main_handle:
            try:
                self.driver.switch_to.window(main_handle)
            except Exception:
                pass
        return False

    def click_batch_save_with_verify(self, max_attempts=10,
                                     phase1_timeout=3.0, phase2_timeout=5.0,
                                     poll_interval=0.3):
        """v5.4: 일괄저장 클릭 + 다운로드 폴더 검증 + 자동 재시도.

        v5.5: max_attempts 기본값 3 → 10 으로 상향. 매 클릭 직전 변경 예정
              안내 팝업이 다시 떴는지 확인하는 가드 추가.
        v5.7: 가드 제거. 사이클의 [단계 2] 본 호출이 이미 충분히 견고하여
              가드의 추가 가치 없음 (자세한 내용은 파일 헤더 v5.7 변경사항).

        흐름:
          1) 사이클 시작 시각 (start_time) 기록.
          2) 클릭 1회 수행.
          3) [1단계] phase1_timeout 안에 '부동산일괄저장*.zip' 또는
             '*.crdownload' 가 start_time 이후 mtime 으로 새로 등장하는지
             감시. 등장하면 4단계로, 안 등장하면 클릭이 안 먹은 것으로
             판단하여 재시도.
          4) [2단계] phase2_timeout 안에 .crdownload 가 사라지고 정상
             .zip 파일이 존재하는지 감시. 완료되면 True 반환.
             타임아웃이면 경고 로그 후 True 반환 (닫기는 진행).
          5) 1~4 를 max_attempts 까지 반복. 모두 실패해도 닫기는 진행
             하므로 본 메서드는 False 만 반환하고 호출자가 결정.

        반환:
          True  - 클릭 성공 + 다운로드 완료 (또는 시도는 성공했고 다운로드
                  완성 여부는 불확실하지만 닫기 진행 가능)
          False - 모든 시도에서 클릭 자체가 안 먹음
        """
        try:
            downloads_dir = self._resolve_downloads_dir()
            if not downloads_dir.is_dir():
                raise RuntimeError(f"다운로드 폴더 없음: {downloads_dir}")
        except Exception as e:
            # 폴백: 검증 불가 → 기존 동작 (단순 클릭 + sleep) 으로
            logger.warning(
                f"[일괄저장] 다운로드 폴더 접근 실패 → 검증 없이 진행: {e}"
            )
            return self.click_batch_save()

        for attempt in range(1, max_attempts + 1):
            cycle_start = time.time()

            # v5.7: '클릭 직전 모달 가드' 제거. 사이클의 [단계 2] 본 호출이
            #       이미 닫힘 확인 + 재발 감시까지 완료했으므로 여기서 다시
            #       검사할 필요 없음.

            # 클릭 1회
            if not self._click_batch_save_button_once():
                logger.warning(
                    f"[일괄저장] 클릭 자체 실패 (시도 {attempt}/{max_attempts})"
                )
                # 클릭 자체가 안 됐으면 검증해봐야 의미 없음. 짧게 쉬고 재시도.
                time.sleep(0.5)
                continue

            logger.info(f"[일괄저장] 클릭 (시도 {attempt}/{max_attempts})")
            self._handle_alert(accept=True)

            # ── 1단계: 다운로드 시작 감지 ─────────────────────────
            started, started_file = self._wait_download_started(
                downloads_dir, cycle_start, phase1_timeout, poll_interval
            )
            if not started:
                logger.warning(
                    f"[일괄저장] {phase1_timeout:.0f}초 내 다운로드가 "
                    f"시작되지 않음 → 클릭 미작동으로 판단, 재시도"
                )
                # 짧게 쉬고 재시도 (페이지 상태 안정화 여유)
                time.sleep(0.5)
                continue

            logger.info(
                f"[일괄저장] 다운로드 시작 감지: {started_file.name if started_file else '(파일명 불명)'}"
            )

            # ── 2단계: 다운로드 완료 감지 ────────────────────────
            completed, final_file = self._wait_download_completed(
                downloads_dir, cycle_start, phase2_timeout, poll_interval
            )
            if completed:
                size_str = ""
                try:
                    size_str = f" ({final_file.stat().st_size:,}bytes)"
                except Exception:
                    pass
                logger.info(
                    f"[일괄저장] ✓ 다운로드 완료: {final_file.name}{size_str}"
                )
                return True
            else:
                # 시작은 됐는데 완료를 못 본 경우. 클릭은 먹은 거니까 재시도
                # 하면 중복 다운로드가 될 위험이 있음. 경고만 남기고 진행.
                logger.warning(
                    f"[일괄저장] 다운로드 시작은 감지됐으나 "
                    f"{phase2_timeout:.0f}초 내 완료를 확인하지 못함 → 닫기 진행"
                )
                return True

        # 모든 시도에서 클릭이 안 먹은 경우
        logger.error(
            f"[일괄저장] {max_attempts}회 시도 모두 다운로드 시작을 감지하지 "
            f"못함 → 닫기 진행 (이 사이클의 ZIP 누락 가능성 있음)"
        )
        return False

    def _wait_download_started(self, downloads_dir, since_ts, timeout, poll_interval):
        """v5.4: since_ts 이후 mtime 으로 '부동산일괄저장*.zip[.crdownload]'
        가 등장할 때까지 최대 timeout 초 폴링.

        반환: (started: bool, file: Path|None)
        """
        deadline = time.time() + timeout
        # mtime 비교에 0.5초 여유를 둠 (파일 시스템 mtime 정밀도 + 시계 차)
        threshold = since_ts - 0.5
        while time.time() < deadline:
            try:
                # 정상 zip + 다운로드 중인 .crdownload 둘 다 검사
                candidates = (
                    list(downloads_dir.glob("부동산일괄저장*.zip"))
                    + list(downloads_dir.glob("부동산일괄저장*.zip.crdownload"))
                    + list(downloads_dir.glob("부동산일괄저장*.crdownload"))
                )
                for f in candidates:
                    try:
                        if f.stat().st_mtime >= threshold:
                            return True, f
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(poll_interval)
        return False, None

    def _wait_download_completed(self, downloads_dir, since_ts, timeout, poll_interval):
        """v5.4: since_ts 이후 새로 생긴 '부동산일괄저장*.zip' 파일이 .crdownload
        없이 안정 상태가 될 때까지 최대 timeout 초 폴링.

        반환: (completed: bool, file: Path|None)
        """
        deadline = time.time() + timeout
        threshold = since_ts - 0.5
        while time.time() < deadline:
            try:
                # since_ts 이후 새로 생성된 zip 파일 중 짝꿍 .crdownload 가
                # 없는 것이 있으면 완료된 것으로 인정.
                zips = [
                    f for f in downloads_dir.glob("부동산일괄저장*.zip")
                    if f.stat().st_mtime >= threshold
                ]
                for zf in zips:
                    cr = downloads_dir / (zf.name + ".crdownload")
                    if not cr.exists():
                        # 추가 안정성: 1회 더 동일 사이즈 확인 (작은 파일이라
                        # 한 번만 확인해도 사실상 충분하지만 안전 차원)
                        try:
                            size1 = zf.stat().st_size
                            time.sleep(0.15)
                            size2 = zf.stat().st_size
                            if size1 == size2 and size1 > 0:
                                return True, zf
                        except Exception:
                            return True, zf
            except Exception:
                pass
            time.sleep(poll_interval)
        return False, None

    def click_close_button(self):
        """'닫기' 버튼 클릭"""
        clicked = self.driver.execute_script("""
            var btns = document.querySelectorAll('a, button, input[type="button"]');
            for (var i = 0; i < btns.length; i++) {
                var txt = (btns[i].textContent || btns[i].value || '').trim();
                if (txt === '닫기' && btns[i].offsetParent !== null) {
                    btns[i].click();
                    return true;
                }
            }
            return false;
        """)
        if clicked:
            logger.info("[닫기] 클릭")
            time.sleep(1)
            self._handle_alert(accept=True)
            try:
                handles = self.driver.window_handles
                if len(handles) >= 1:
                    self.driver.switch_to.window(handles[0])
            except Exception:
                pass
            return True

        try:
            handles = self.driver.window_handles
            if len(handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(handles[0])
                logger.info("팝업 창 직접 닫기 → 메인 창 복귀")
                return True
        except Exception:
            pass

        logger.warning("[닫기] 버튼을 찾을 수 없음")
        return False

    def batch_view_and_save_cycle(self):
        """
        v3.16: 전체체크 → 일괄열람출력 → 확인 → (신청사건 처리중 팝업 확인) → 일괄저장 → 닫기
        v4.4: 고정 time.sleep 을 _wait_until_modal_dismissed 기반 능동 대기로 교체.
              정상 환경에서 사이클당 ~4~5초 단축.
        """
        if not self.click_select_all_checkbox():
            return False
        time.sleep(0.3)   # v4.4: 0.5 → 0.3

        if not self.click_batch_view_print():
            return False

        # v5.6: handle_batch_view_confirm_popup() 호출 제거.
        #   본문 식별 없이 페이지 전체에서 '확인' 텍스트 버튼을 무조건 누르던
        #   함수로, 처리중 바가 사라지기도 전인 시점에 실행되어 헛클릭 위험이
        #   있었음. 진짜 변경 예정 안내 팝업은 아래 _handle_pending_case_popup()
        #   이 본문 식별 기반으로 정확히 처리.
        # v5.6: 짝꿍이던 _wait_until_modal_dismissed(max_wait=3.0) 도 함께 제거.
        #   다음 단계의 _wait_until_processbar_gone() 가 더 정확한 대기 수행.

        # native alert 안전망은 유지 (등기소가 가끔 native alert 로 띄울 가능성)
        self._handle_alert(accept=True)

        # ──────────────────────────────────────────────────────────
        # v5.5: 사용자 요청에 따른 3단계 안전 절차
        #   1) '처리 중입니다.' 진행바가 완전히 사라질 때까지 대기
        #   2) 변경 예정 안내 팝업이 떴으면 감지하여 확인 클릭
        #   3) 팝업이 완전히 사라진 뒤 일괄저장 클릭 (최대 10회 재시도)
        # ──────────────────────────────────────────────────────────

        # [단계 1] 처리중 진행바 사라질 때까지 대기 (등기소 서버 응답 지연 흡수)
        self._wait_until_processbar_gone(max_wait=20.0)

        # [단계 2] 변경 예정 안내 팝업 처리 (있으면 닫고, 없으면 ~1초 후 패스)
        self._handle_pending_case_popup()

        # [단계 3] 일괄저장 클릭 (클릭 직전 모달 가드는 내부에서 수행)
        if not self.click_batch_save_with_verify():
            logger.warning("[일괄저장] 모든 시도 실패 → 닫기 시도")

        self.click_close_button()
        # v4.4: 고정 sleep(2) → 능동 대기로 교체
        self._handle_alert(accept=True)
        self._wait_until_modal_dismissed(max_wait=2.0)

        try:
            handles = self.driver.window_handles
            self.driver.switch_to.window(handles[0])
        except Exception:
            pass
        time.sleep(0.3)   # v4.4: 1 → 0.3 (윈도우 전환 직후 최소 안정화)

        return True

    def run_batch_view_save_loop(self):
        """
        미발급 전체 건수가 0건이 될 때까지 10건씩 일괄열람 후 일괄저장 반복.
        v4.4: 사이클 간 고정 대기 축소 (2초 + 1초 → 각 0.3초 + 능동 대기).
        """
        cycle = 0
        max_cycles = 100

        while cycle < max_cycles:
            cycle += 1
            # v4.4: 고정 sleep(1) 제거 — 직전 사이클 말미에서 이미 능동 대기 수행됨

            # v4.6: 사이클 경계 체크포인트
            if _pause is not None:
                _pause.checkpoint()

            remaining = self._extract_unissued_count()
            if remaining is not None:
                logger.info(f"[사이클 {cycle}] 미발급 잔여: {remaining}건")
                overlay_status(f"Phase 3: 사이클 {cycle} | 잔여 {remaining}건")
                if remaining == 0:
                    logger.info("★ 미발급 전체 건수 0건 → 일괄열람/저장 완료!")
                    return True
            else:
                logger.warning(f"[사이클 {cycle}] 미발급 건수 추출 실패 → 한 번 더 시도")
                time.sleep(1)   # v4.4: 2 → 1 (추출 재시도 직전 짧은 안정화)
                remaining = self._extract_unissued_count()
                if remaining is not None and remaining == 0:
                    logger.info("★ 미발급 전체 건수 0건 → 일괄열람/저장 완료!")
                    return True
                elif remaining is None:
                    logger.error("미발급 건수를 읽을 수 없음 → 루프 종료")
                    return False

            logger.info(f"[사이클 {cycle}] 일괄열람/저장 시작 (잔여 {remaining}건)")
            if not self.batch_view_and_save_cycle():
                logger.error(f"[사이클 {cycle}] 일괄열람/저장 사이클 실패")
                return False

            # v4.4: 고정 sleep(2) 제거 → 능동 대기로 대체
            self._handle_alert(accept=True)
            self._wait_until_modal_dismissed(max_wait=2.0)

        return True

    @staticmethod
    def _resolve_desktop_dir_static():
        """v5.0: Phase 4 (move_and_extract_zip_files) 와 폐쇄목록 즉시저장이
        동일한 바탕화면을 가리키도록 하기 위한 staticmethod 버전.

        OneDrive 리다이렉트가 있는 환경에서는 Path.home()/Desktop 이 실제
        바탕화면과 다를 수 있어, OneDrive\\Desktop 을 우선 검사한다.
        """
        try:
            if os.name == "nt":
                onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
                if onedrive:
                    cand = os.path.join(onedrive, "Desktop")
                    if os.path.isdir(cand):
                        return Path(cand)
                    cand_kr = os.path.join(onedrive, "바탕 화면")
                    if os.path.isdir(cand_kr):
                        return Path(cand_kr)
                userprofile = os.environ.get("USERPROFILE") or str(Path.home())
                for sub in ("Desktop", "바탕 화면"):
                    cand = os.path.join(userprofile, sub)
                    if os.path.isdir(cand):
                        return Path(cand)
                return Path(userprofile) / "Desktop"
            return Path.home() / "Desktop"
        except Exception:
            return Path.home() / "Desktop"

    @staticmethod
    def _resolve_downloads_dir():
        """v5.4: 다운로드 폴더 결정 (저장 검증과 ZIP 이동에서 공용 사용).

        고정 경로(C:\\Users\\Administrator\\Downloads) 우선, 없으면 사용자
        홈의 Downloads 로 폴백.
        """
        d = Path(r"C:\Users\Administrator\Downloads")
        if d.is_dir():
            return d
        return Path.home() / "Downloads"

    @staticmethod
    def move_and_extract_zip_files():
        """v3.5: C:\\Users\\Administrator\\Downloads 에서 부동산일괄저장 ZIP 파일을
        바탕화면 오늘날짜 폴더로 이동 → 압축해제 → PDF 파일명 정리

        변경사항:
          - 다운로드 경로를 C:\\Users\\Administrator\\Downloads로 고정
          - 전체 ZIP 파일 목록 로깅 (디버깅)
          - v5.0: 바탕화면 탐지를 OneDrive 우선으로 변경하여 폐쇄목록 즉시저장과
                  동일한 폴더(YYYYMMDD)에 결과물이 모이도록 통일.
        """
        today_str = datetime.now().strftime("%Y%m%d")

        # v5.4: 다운로드 폴더 결정을 헬퍼로 통일
        downloads_dir = PaymentQueueAutomation._resolve_downloads_dir()

        # v5.0: OneDrive 리다이렉트를 고려한 바탕화면 탐지
        desktop_dir = PaymentQueueAutomation._resolve_desktop_dir_static()

        logger.info(f"다운로드 폴더: {downloads_dir}")
        logger.info(f"바탕화면: {desktop_dir}")
        # ── 다운로드 폴더 내 전체 ZIP 파일 목록 로깅 (디버깅) ──
        all_zips = list(downloads_dir.glob("*.zip"))
        if all_zips:
            logger.info(f"다운로드 폴더 내 전체 ZIP 파일 {len(all_zips)}개:")
            for f in sorted(all_zips, key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
                try:
                    mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                    size = f.stat().st_size
                    logger.info(f"  {f.name} | {size:,}bytes | 수정: {mod_time}")
                except Exception:
                    logger.info(f"  {f.name} | (정보 읽기 실패)")
        else:
            logger.warning("다운로드 폴더에 ZIP 파일이 하나도 없습니다")

        # ── 부동산일괄저장 ZIP 파일 수집 ──
        all_related = list(downloads_dir.glob("부동산일괄저장*.zip"))
        logger.info(f"부동산일괄저장 ZIP 파일 {len(all_related)}개:")
        for f in all_related:
            try:
                mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                size = f.stat().st_size
                logger.info(f"  {f.name} | {size:,}bytes | 수정: {mod_time}")
            except Exception:
                logger.info(f"  {f.name} | (정보 읽기 실패)")

        # ── 오늘날짜 폴더 생성 ──
        target_dir = desktop_dir / today_str
        target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"대상 폴더: {target_dir}")

        # 오늘 날짜 파일만 필터 + 중복 제거
        today_date = datetime.now().date()
        today_zips = []
        seen = set()
        for zf in all_related:
            if zf.name in seen:
                continue
            seen.add(zf.name)
            try:
                mod_date = datetime.fromtimestamp(zf.stat().st_mtime).date()
                if mod_date == today_date:
                    today_zips.append(zf)
                else:
                    logger.info(f"  날짜 불일치로 제외: {zf.name} (수정일: {mod_date})")
            except Exception:
                today_zips.append(zf)  # 날짜 확인 실패 시 포함

        if not today_zips:
            logger.warning("오늘 다운로드한 부동산일괄저장*.zip 파일을 찾을 수 없습니다")
            # 날짜 무관하게 전체 ZIP 파일 확인
            if all_related:
                logger.info(f"날짜 무관 ZIP 파일 {len(all_related)}개 존재 → 전부 이동합니다")
                today_zips = list(all_related)
            else:
                return False

        logger.info(f"이동할 ZIP 파일 {len(today_zips)}개")

        # ── 이동 및 압축해제 ──
        for zf in sorted(today_zips, key=lambda x: x.name):
            dest = target_dir / zf.name
            try:
                shutil.move(str(zf), str(dest))
                logger.info(f"이동: {zf.name} → {target_dir}")
            except Exception as e:
                logger.error(f"이동 실패 ({zf.name}): {e}")
                continue
            try:
                with zipfile.ZipFile(str(dest), "r") as z:
                    z.extractall(str(target_dir))
                logger.info(f"압축해제 완료: {zf.name}")
            except Exception as e:
                logger.error(f"압축해제 실패 ({zf.name}): {e}")

        # ── PDF 파일명 정리: '_숫자_RIS' 패턴 제거 ──
        # 예: "등기부등본_12345_RIS.pdf" → "등기부등본.pdf"
        rename_pattern = re.compile(r'_\d+_RIS')
        renamed_count = 0
        for pdf_file in target_dir.glob("*.pdf"):
            old_name = pdf_file.name
            new_name = rename_pattern.sub('', old_name)
            if old_name != new_name:
                new_path = target_dir / new_name
                # 동일 이름 파일이 이미 있으면 번호 붙이기
                if new_path.exists():
                    stem = Path(new_name).stem
                    suffix = Path(new_name).suffix
                    counter = 1
                    while new_path.exists():
                        new_path = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                try:
                    pdf_file.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    logger.error(f"파일명 변경 실패 ({old_name}): {e}")

        if renamed_count > 0:
            logger.info(f"PDF 파일명 정리 완료: {renamed_count}개 파일 이름 변경")

        logger.info(f"★ 전체 ZIP 이동/압축해제/파일명 정리 완료 → {target_dir}")
        return True

    def save_failed_items(self):
        if not self.failed_items:
            logger.info("실패 항목 없음 - 모든 작업 성공!")
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"failed_{ts}.txt"
        with open(fn, "w", encoding="utf-8") as f:
            for pid, _ in self.failed_items:
                f.write(f"{pid}\n")
        logger.info(f"실패 목록: {fn} ({len(self.failed_items)}건)")
        return fn

    # ── v5.0: 폐쇄 고유번호 즉시 저장 ──────────────────────
    def _resolve_desktop_dir(self):
        """v5.0: 인스턴스용 래퍼. Phase 4 와 동일한 바탕화면을 가리키도록
        staticmethod 버전을 그대로 재사용 (경로 불일치 방지)."""
        try:
            return str(PaymentQueueAutomation._resolve_desktop_dir_static())
        except Exception as e:
            logger.warning(f"바탕화면 경로 탐지 실패: {e}")
            return None

    def _ensure_closed_items_file(self):
        """v5.0: 첫 폐쇄 감지 시 바탕화면에 날짜 폴더와 파일을 생성.

        - 폴더명: YYYYMMDD  (오늘 날짜만, 단순 형식)
                  → Phase 4 의 일괄열람/저장 결과물(move_and_extract_zip_files
                    가 만드는 바탕화면/YYYYMMDD)과 같은 폴더로 통일하여,
                    작업 완료 후 폐쇄목록.txt 와 등기부등본.pdf 가 한 곳에
                    모이도록 함. 폴더가 이미 있으면 그대로 재사용.
        - 파일명: 폐쇄고유번호_YYYYMMDD_HHMMSS.txt
        - 헤더에 생성 시각/안내 문구를 한 줄 적어둠.
        - 바탕화면 접근 실패 시 현재 작업 폴더로 폴백.
        - 한 번 생성되면 self._closed_items_file 에 캐시되어 재사용.
        """
        if self._closed_items_file:
            return self._closed_items_file

        today = datetime.now().strftime("%Y%m%d")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = today  # v5.0: YYYYMMDD 단순 형식 (Phase 4 와 통일)
        file_name = f"폐쇄고유번호_{ts}.txt"

        target_dir = None
        # 우선순위 1: 바탕화면
        desktop = self._resolve_desktop_dir()
        if desktop:
            try:
                target_dir = os.path.join(desktop, folder_name)
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"바탕화면에 폐쇄목록 폴더 생성 실패: {e} → 작업 폴더로 폴백")
                target_dir = None

        # 폴백: 작업 폴더(cwd)
        if not target_dir:
            try:
                target_dir = os.path.join(os.getcwd(), folder_name)
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"폐쇄목록 폴더 생성 완전 실패: {e}")
                # 최후의 보루: cwd 자체에 파일만 생성
                target_dir = os.getcwd()

        file_path = os.path.join(target_dir, file_name)

        # 헤더 1회 기록 (덮어쓰기 모드)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# 인터넷등기소 폐쇄 고유번호 목록\n")
                f.write(f"# 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 작업 중 폐쇄가 감지될 때마다 이 파일에 즉시 추가됩니다.\n")
                f.write(f"# (작업이 중단되어도 직전까지의 폐쇄 고유번호는 보존됩니다)\n")
                f.write("\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"폐쇄목록 파일 헤더 기록 실패: {e}")

        self._closed_items_dir = target_dir
        self._closed_items_file = file_path
        logger.info(f"[폐쇄] 즉시 저장 파일 생성 → {file_path}")
        return file_path

    def _append_closed_item_immediate(self, display_id):
        """v5.0: 폐쇄 고유번호 1건을 즉시 디스크에 append 한다.

        - 첫 호출 시 파일이 없으면 _ensure_closed_items_file() 로 생성.
        - 매 호출마다 open → write → flush → fsync → close 하여,
          프로세스가 강제 종료되어도 직전 기록까지는 디스크에 남도록 보장.
        - 이 함수는 self.closed_items 리스트와는 독립적으로 호출되며,
          호출측에서 중복 추가 방지를 책임진다 (기존 로직 유지).
        """
        try:
            path = self._ensure_closed_items_file()
            if not path:
                return
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{display_id}\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"폐쇄 고유번호 즉시 저장 실패({display_id}): {e}")

    def save_closed_items(self):
        """v3.13: 폐쇄 등기 고유번호 목록을 파일로 저장.

        v5.0: 즉시 저장 방식으로 바뀌면서 이 함수는 사실상 '이미 저장된 파일의
        경로를 알려주는' 역할로 축소됨. 호환성을 위해 인터페이스는 유지.
        - 즉시 저장 파일이 이미 있다면 그 경로를 그대로 반환 (중복 저장 X).
        - 즉시 저장 파일이 없는데 closed_items 만 있는 비정상 상황(예: 과거 호출
          순서 어긋남) 에서는 종전 방식대로 작업 폴더에 한 번에 저장.
        """
        if not self.closed_items:
            logger.info("폐쇄 등기 항목 없음")
            return None

        # 정상 경로: 이미 즉시 저장된 파일이 있으면 그것을 그대로 사용
        if self._closed_items_file and os.path.exists(self._closed_items_file):
            logger.info(
                f"폐쇄 등기 목록(즉시 저장됨): {self._closed_items_file} "
                f"({len(self.closed_items)}건)"
            )
            return self._closed_items_file

        # 폴백: 즉시 저장이 어떤 이유로 안 됐을 때 종전 방식
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"closed_{ts}.txt"
        with open(fn, "w", encoding="utf-8") as f:
            for pid in self.closed_items:
                f.write(f"{pid}\n")
        logger.info(f"폐쇄 등기 목록: {fn} ({len(self.closed_items)}건)")
        return fn

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None


# ─── 메인 ──────────────────────────────────────────────────

def main():
    args = parse_args()

    # v4.5: 진행상황 오버레이 / v4.6: 일시정지 컨트롤러 시작 (실패해도 본 작업은 계속)
    global _overlay, _pause, _popup_watcher
    _pause = PauseController()
    try:
        _overlay = ProgressOverlay.start(controller=_pause)
        _overlay.attach_to_logger(logger)
        _overlay.set_status("초기화 중…")
        # 일시정지 상태 변경 시 오버레이 버튼 활성/비활성 연동
        _pause.set_state_callback(lambda paused: _overlay.set_pause_indicator(paused))
    except Exception as e:
        _overlay = None
        logger.debug(f"오버레이 초기화 실패 (무시): {e}")

    # v5.2: Windows 응용 프로그램 오류 팝업 자동 닫기 워치독 시작
    #       (Windows 가 아니면 자동 비활성, 본 작업에는 영향 없음)
    _popup_watcher = PopupWatcher(
        poll_interval=5.0, rest_seconds=10, rest_threshold=2
    )
    try:
        _popup_watcher.start()
    except Exception as e:
        logger.debug(f"팝업 워치독 시작 실패 (무시): {e}")

    logger.info("=" * 60)
    logger.info("인터넷등기소 결제대상 자동 추가 + 일괄결제·열람·저장 v5.7")
    logger.info("=" * 60)

    # v4.2: 작업 중 절전/화면보호기 방지
    prevent_sleep()

    if not os.path.exists(args.file):
        logger.error(f"파일 없음: {args.file}")
        sys.exit(1)

    items = load_property_ids(args.file)
    if not items:
        logger.error("처리할 고유번호 없음")
        sys.exit(1)

    total = len(items)
    # v5.3: --start-from 의미를 1-based "N번째 건부터" 로 변경.
    #       사용자 입력값을 그대로 1-based 로 해석하되, 0 / 미지정 / 1 은 모두
    #       "처음부터" 로 동일하게 처리. start_offset 변수는 이후 expected/
    #       resume_from 계산에 사용되므로 정규화된 1-based 값을 보관.
    start_offset = max(args.start_from, 1)
    logger.info(f"총 {total}건 로드 (시작: {start_offset}번째 건부터)")

    if start_offset > 1:
        items = items[start_offset - 1:]

    auto = PaymentQueueAutomation()
    success_count = 0

    try:
        auto.start()
        if not auto.login():
            logger.error("로그인 실패")
            sys.exit(1)
        time.sleep(2)

        # ════════════════════════════════════════════════════
        # Phase 1: 결제대상 추가
        #   ★ v3.2: 마지막 항목 후 go_to_main() 안 함
        #   ★ v4.1: 10회 재시도 라운드를 최대 MAX_ROUNDS_PER_ITEM 번 반복.
        #           라운드 사이에는 COOLDOWN_BETWEEN_ROUNDS_SEC 초 대기. 최종
        #           라운드까지 실패하면 전역 장애로 간주하고 작업 종료.
        # ════════════════════════════════════════════════════
        overlay_status("Phase 1: 결제대상 추가")
        overlay_progress(0, len(items))
        for idx, item in enumerate(items):
            # v4.6: 건 경계 체크포인트 — 일시정지/중단 반응 지점
            if _pause is not None:
                _pause.checkpoint()

            pid = item["property_id"]
            dpid = item["property_id_display"]
            # v5.3: start_offset 은 이미 1-based 로 정규화됨.
            #   첫 건(idx=0) 의 expected = start_offset.
            #   예) start_offset=112, idx=0 → expected=112 (결제대상 화면에 112건 있어야 함)
            expected = start_offset + idx
            is_last = (idx == len(items) - 1)

            logger.info(f"\n[{idx+1}/{len(items)}] {dpid}")
            overlay_status(f"Phase 1: [{idx+1}/{len(items)}] {dpid}")
            overlay_progress(idx, len(items))

            item_succeeded = False

            for round_no in range(1, MAX_ROUNDS_PER_ITEM + 1):
                if round_no > 1:
                    logger.warning("=" * 60)
                    logger.warning(
                        f"[{dpid}] 라운드 {round_no-1} 전체 실패 "
                        f"→ {COOLDOWN_BETWEEN_ROUNDS_SEC}초 대기 후 라운드 {round_no} 시작"
                    )
                    logger.warning("=" * 60)
                    # 쿨다운 대기 (중간에 세션 유지 시도)
                    # v4.6: 중단 가능한 sleep 로 교체 — 10초 청크마다 세션 유지 + stop 체크
                    sleep_start = time.time()
                    while time.time() - sleep_start < COOLDOWN_BETWEEN_ROUNDS_SEC:
                        chunk = min(10, COOLDOWN_BETWEEN_ROUNDS_SEC - (time.time() - sleep_start))
                        if _pause is not None:
                            _pause.sleep(chunk)   # StopRequested 시 밖으로 전파
                        else:
                            time.sleep(chunk)
                        try:
                            auto._dismiss_any_alert()
                            auto._kill_processbar_overlay()
                        except Exception:
                            pass
                    try:
                        auto.go_to_main()
                        time.sleep(1)
                        auto.ensure_logged_in()
                    except Exception as e:
                        logger.warning(f"라운드 {round_no} 진입 전 복구 중 오류(무시): {e}")

                for attempt in range(MAX_RETRY_PER_ITEM):
                    auto.ensure_logged_in()

                    if attempt > 0:
                        logger.info(f"  라운드 {round_no} 재시도 #{attempt}")
                        auto._dismiss_any_alert()

                        if auto.is_duplicate_payment_page():
                            success_count += 1
                            logger.info(f"  ✓ 중복결제 페이지 기준 성공 ({success_count}건)")
                            if not is_last:
                                auto.go_to_main()
                                time.sleep(1)
                            item_succeeded = True
                            break

                        auto.go_to_main()
                        time.sleep(0.5)
                        auto.ensure_logged_in()

                    result = auto.process_single(pid, dpid)

                    if result == "duplicate":
                        success_count += 1
                        logger.info(f"  ✓ 중복결제 확인 기준 성공 ({success_count}건)")
                        if not is_last:
                            auto.go_to_main()
                            time.sleep(1)
                        item_succeeded = True
                        break

                    if result == "success" and auto.verify_payment_count(expected):
                        success_count += 1
                        logger.info(f"  ✓ 성공 ({success_count}건)")
                        if not is_last:
                            auto.go_to_main()
                            time.sleep(1)
                        else:
                            logger.info("★ 마지막 항목 → 결제대상 화면 유지")
                        item_succeeded = True
                        break

                    logger.warning("  → 재시도")
                    auto._dismiss_any_alert()
                    time.sleep(1)

                # 라운드 내 10회 루프 종료. 성공했으면 라운드 루프도 탈출.
                if item_succeeded:
                    break

            if not item_succeeded:
                # v4.1: 모든 라운드 소진 → 전역 장애로 판단하고 작업 종료.
                # "발급 순번 = 결제대상 건수" 전제가 깨진 상태로 다음 건 진행 시
                # 이후 모든 건이 오판되므로 여기서 깔끔히 멈추는 것이 안전.
                auto.failed_items.append((dpid, f"{MAX_ROUNDS_PER_ITEM}라운드 모두 실패"))
                logger.error("=" * 60)
                logger.error(f"✗ 최종 실패: {dpid}")
                logger.error(
                    f"같은 건이 {MAX_ROUNDS_PER_ITEM}라운드(총 "
                    f"{MAX_ROUNDS_PER_ITEM * MAX_RETRY_PER_ITEM}회) 모두 실패 → "
                    f"전역 장애로 판단하여 작업 종료"
                )
                if idx > 0:
                    # v5.3: 재개 명령도 1-based 의미로 출력.
                    #   현재 건의 1-based 번호 = start_offset + idx.
                    #   사용자가 그대로 복사해 --start-from 으로 주면 같은 건부터 재개.
                    resume_from = start_offset + idx
                    logger.error(
                        f"재개 시: python {os.path.basename(__file__)} "
                        f"--start-from {resume_from}"
                    )
                logger.error("=" * 60)
                auto.save_failed_items()
                if auto.closed_items:
                    auto.save_closed_items()
                auto.close()
                sys.exit(2)

            time.sleep(1)

            # v5.2: 팝업이 누적 발생했다면 다음 건 시작 전에 휴식 1회분 소비.
            #       (없으면 즉시 반환, 추가 sleep 없음)
            try:
                if _popup_watcher is not None:
                    _popup_watcher.consume_rest_if_due()
            except StopRequested:
                raise
            except Exception as e:
                logger.debug(f"휴식 회분 소비 중 예외 (무시): {e}")

        auto.save_failed_items()
        logger.info(f"\n{'='*60}")
        logger.info(f"[Phase 1 완료] 전체: {total} | 성공: {success_count} | 실패: {len(auto.failed_items)}")
        logger.info(f"{'='*60}")
        overlay_progress(len(items), len(items))
        overlay_status(f"Phase 1 완료 | 성공 {success_count} / 실패 {len(auto.failed_items)}")

        # v3.13: 폐쇄 등기 목록 저장 및 안내
        if auto.closed_items:
            auto.save_closed_items()
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"★★★ 폐쇄 고유번호를 확인하세요 ({len(auto.closed_items)}건) ★★★")
            for pid in auto.closed_items:
                logger.info(f"  - {pid}")
            logger.info("=" * 60)
            print("\n" + "=" * 60)
            print(f"★★★ 폐쇄 고유번호를 확인하세요 ({len(auto.closed_items)}건) ★★★")
            for pid in auto.closed_items:
                print(f"  - {pid}")
            print("=" * 60 + "\n")

        # ════════════════════════════════════════════════════
        # Phase 2: 일괄결제 → 수기 결제 대기
        # ════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 2] 일괄결제 시작")
        logger.info("=" * 60)
        overlay_status("Phase 2: 일괄결제")
        overlay_progress(0, 0)  # 진행률바 리셋

        auto.ensure_logged_in()
        time.sleep(1)

        # 결제대상 건수 확인
        actual_count, matched_text = auto._extract_payment_count()
        if actual_count is not None:
            logger.info(f"결제대상 목록: {actual_count}건 (예상: {total}건)")
            if actual_count == total:
                logger.info("✓ 결제대상 건수 일치")
            else:
                logger.warning(f"✗ 건수 불일치: {actual_count}건 ≠ 예상 {total}건")
        else:
            logger.warning("결제대상 건수를 확인할 수 없음")

        # 일괄결제 클릭
        auto.click_batch_payment()
        time.sleep(1)
        auto._handle_alert(accept=True)

        # 수기 결제 대기
        overlay_status("Phase 2: 수기 결제 대기 중…")
        auto.wait_for_manual_payment()

        # ════════════════════════════════════════════════════
        # Phase 3: 일괄열람출력 + 일괄저장 반복
        # ════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 3] 일괄열람 출력 + 일괄저장 반복 시작")
        logger.info("=" * 60)
        overlay_status("Phase 3: 일괄열람/저장")

        auto.ensure_logged_in()
        time.sleep(1)

        if auto.run_batch_view_save_loop():
            logger.info("★ 일괄열람/저장 전체 프로세스 완료!")
        else:
            logger.error("일괄열람/저장 프로세스 중 오류 발생")

        # ════════════════════════════════════════════════════
        # Phase 4: ZIP 파일 이동 및 압축해제
        # ════════════════════════════════════════════════════
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 4] ZIP 파일 이동 및 압축해제")
        logger.info("=" * 60)
        overlay_status("Phase 4: ZIP 정리")

        if PaymentQueueAutomation.move_and_extract_zip_files():
            logger.info("★ ZIP 파일 이동/압축해제 완료!")
        else:
            logger.warning("ZIP 파일 이동/압축해제 실패 → 수동으로 확인하세요")

        logger.info("\n" + "=" * 60)
        logger.info("★★★ 전체 자동화 프로세스 완료 ★★★")
        logger.info("=" * 60)
        overlay_status("✓ 전체 완료")
        overlay_progress(1, 1)

    except StopRequested:
        logger.warning("\n" + "=" * 60)
        logger.warning("★ 사용자 요청으로 작업이 중단되었습니다 (오버레이 '중단' 버튼)")
        logger.warning("=" * 60)
        overlay_status("⏹ 중단됨")
        try:
            if _overlay is not None:
                _overlay.set_stopped()
        except Exception:
            pass
    except KeyboardInterrupt:
        logger.warning("\n중단됨")
    except Exception as e:
        logger.error(f"오류: {e}", exc_info=True)
    finally:
        logger.info(f"\n{'='*60}\n전체: {total} | 성공: {success_count} | 실패: {len(auto.failed_items)}\n{'='*60}")
        # v5.2: 팝업 워치독 통계 요약 + 정지
        try:
            if _popup_watcher is not None and _popup_watcher.dismiss_count > 0:
                logger.warning(
                    f"[팝업워치독] 이번 실행 요약: "
                    f"OS 팝업 자동 닫음 {_popup_watcher.dismiss_count}회, "
                    f"휴식 부여 {_popup_watcher.rest_granted_total}회 / "
                    f"소비 {_popup_watcher.rest_consumed_total}회"
                )
            if _popup_watcher is not None:
                _popup_watcher.stop()
        except Exception:
            pass
        auto.close()
        allow_sleep()   # v4.2: 절전 방지 해제 (멱등 - 재호출해도 안전)
        # v4.5: 오버레이 종료. Enter 대기 중에도 창이 남아있도록 즉시 닫지 않음.
        try:
            if _pause is not None and _pause.is_stopping:
                overlay_status("⏹ 중단됨 — 엔터로 닫기")
            else:
                overlay_status("작업 완료 — 엔터로 닫기")
        except Exception:
            pass


def parse_args():
    p = argparse.ArgumentParser(description="인터넷등기소 결제대상 자동 추가 + 일괄결제·열람·저장 v5.7")
    p.add_argument("--file", "-f", default=DEFAULT_FILE)
    p.add_argument(
        "--start-from", type=int, default=0,
        help=(
            "N번째 건부터 처리 (1-based, 로그 표시와 동일). "
            "예) --start-from 112 → property_list.txt 의 112번째 줄부터 처리. "
            "미지정 또는 0/1 은 처음부터 처리."
        ),
    )
    return p.parse_args()


if __name__ == "__main__":
    # v4.1: .py 파일 더블클릭 실행 지원 (bat 파일 없이)
    #   1) 작업 디렉토리를 스크립트 위치로 변경 → 기본 파일(property_list.txt) 탐색 보장
    #   2) 예외/정상 종료 시 콘솔창이 즉시 닫히지 않도록 Enter 대기
    # v4.6 hotfix: PyInstaller onefile (.exe) 로 빌드된 경우 __file__ 은 %TEMP% 의
    #              임시 해제 폴더를 가리키므로, 그쪽으로 chdir 하면 property_list.txt
    #              를 찾지 못함. sys.frozen 을 감지해 .exe 가 있는 실제 폴더로 이동.
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller 등으로 빌드된 실행파일
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # 일반 .py 실행
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        if exe_dir:
            os.chdir(exe_dir)
    except Exception:
        pass

    exit_code = 0
    try:
        main()
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
    except KeyboardInterrupt:
        logger.warning("\n사용자 중단")
        exit_code = 130
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}", exc_info=True)
        exit_code = 1
    finally:
        # v4.2: 최종 안전망 - sys.exit(2) 등 어떤 경로로든 여기 도달하므로
        # 절전 방지 해제를 한 번 더 호출 (멱등이라 중복 호출해도 무해)
        try:
            allow_sleep()
        except Exception:
            pass
        # v5.2: 팝업 워치독도 한 번 더 정지 (멱등)
        try:
            if _popup_watcher is not None:
                _popup_watcher.stop()
        except Exception:
            pass
        # 더블클릭으로 실행된 경우 창이 바로 닫히는 것 방지
        try:
            input("\n종료하려면 Enter 를 누르세요...")
        except Exception:
            pass
        # v4.5: Enter 입력 후 오버레이 창 정리
        try:
            if _overlay is not None:
                _overlay.stop()
        except Exception:
            pass
    sys.exit(exit_code)
