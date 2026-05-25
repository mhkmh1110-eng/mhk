"""
등기부등본 근저당권 정보 파싱 프로그램  (v3.2)

[변경 이력]
- v3.2: 기이전 판정 정밀화.
        부기등기 후보 수집 시 등기목적에 '근저당권이전' 키워드 포함 여부를
        추가로 검증한다. 이전(v3.1 이하)에는 같은 본 순위번호의 부기등기
        중 권리자 셀에 근저당권자가 파싱된 모든 행을 후보로 봤으나,
        다른 종류의 부기등기(예: 근저당권변경, 채무자변경 등)에서 우연히
        권리자 셀에 근저당권자 표기가 들어가는 케이스를 배제하기 위해
        등기목적 키워드 검증을 추가.
- v3.1: 결과 엑셀의 시각적 양식 일괄 적용. 처리 로직 자체는 v3.0과 동일.
        (1) 모든 열의 너비를 셀 내용 최대 길이에 맞춰 자동 조정.
        (2) 정렬: 채권최고액/최초설정액 값 셀(2행 이후)을 제외한 모든 셀을
            가운데 정렬. 헤더(첫 행)는 무조건 가운데 정렬.
        (3) 데이터 영역(헤더 행부터 마지막 데이터 행까지, NO~담보물주소 컬럼)의
            모든 셀에 기본 실선 테두리(border, thin) 적용.
        (4) 헤더(첫 행) 폰트: bold, 흰색, 채우기색 RGB(31, 78, 120).
        (5) 처리결과 '다수'에 속하는 부동산 행들(첫 행과 그 아래 삽입 행 전체)
            → 채우기색 RGB(255, 242, 204).
        (6) 처리결과 '개명/기말소/주소오류'에 속하는 부동산 행들
            → 채우기색 RGB(226, 239, 218).
        (7) 처리결과 '기말소/주소오류', '기이전', 'PDF없음' 중 하나가 있는
            부동산 행들 → 채우기색 RGB(252, 228, 214).
        색깔 우선순위 (한 부동산에 여러 라벨 공존 시):
            (7) > (6) > (5).  (예: '다수'와 '기이전'이 같은 부동산에 있으면
            전체가 (7)의 주황색.)
- v3.0: 5가지 기능 추가/개선.
        (1) 채무자 개명 추적: 부기등기 등기원인에 '개명'이 포함된 경우,
            그 부기등기 권리자 셀 첫 줄의 가장 오른쪽 어구를 같은 본 순위번호
            본 등기의 'effective' 채무자명으로 인식. 매치 시 본 등기의 원래
            채무자명 또는 effective 채무자명 중 하나라도 입력값과 일치하면
            매치로 본다.
            개명이 여러 번 일어난 경우(예: 14-1에서 가→나, 14-3에서 나→다)는
            가장 마지막 개명의 새 이름이 effective 채무자명이 된다.
            본 등기 채무자명 삭선 검사는 하지 않음 (부기등기에 '개명' 등기원인이
            있다는 것 자체가 채무자 변경의 확정 신호).
        (2) 공동담보 부동산의 주소에 유형 라벨 추가:
            공동담보 'O' 표시되는 부동산의 담보물주소 끝에 한 칸 띄고
            정확히 '[건물][토지]' 문자열을 추가. (정제된 주소든 원본
            보존된 비정상 주소든 동일 처리)
        (3) 유형 열 추가: 처리결과 좌측에 '유형' 컬럼을 둠.
            값은 첫 페이지 부제로부터 '집합건물' / '건물' / '토지' 중 하나.
        (4) 채권최고액/최초설정액 열을 숫자 형식으로 표시:
            셀 값을 텍스트('175,000,000원')가 아닌 정수(175000000)로 저장하고
            셀 표시형식 '#,##0'을 적용하여 천단위 구분기호로 표시.
        (5) ③ 케이스(매치 없음, 기말소/주소오류)에서도 등기소명을 채움.
            이전(v2.9 이하)에는 ③ 케이스에서 등기소명을 비웠으나, 매치 결과와
            무관하게 PDF에서 객관적으로 뽑히는 정보이므로 채우는 게 더 유용함.
- v2.9: 담보물주소에 '내제조표' 단어가 포함되어 있으면 정제 시도를
        건너뛰고 원본 주소를 그대로 반환하면서 비정상(빨간색)으로 표시.
        주소 정제 로직보다 먼저(외 n필지 제거보다도 앞) 검사한다.
        목적: 특정 비정상 패턴('내제조표'로 시작하거나 포함되는 등기부)을
        자동 정제하지 않고 사용자가 시각적으로 즉시 확인할 수 있도록 함.
- v2.8: 담보물주소 B 패턴 일반화 및 처리 규칙 정밀화.
        (1) B 단위가 임의 문자열을 포함하도록 정규식 일반화.
            동/층/호 각 단위는 '제' + 임의 비공백 문자열 + 단위(동|층|호).
            예) '제(아파트)1002호', '제가1동', '제에이동' 모두 인식.
        (2) B 조합을 5가지로 제한 (호가 반드시 포함되거나 B 자체가 없어야 함):
              · 동+층+호 / 동+호 / 층+호 / 호 단독 / 없음
            한국 부동산 등기에서 호수는 등기 단위이므로 (집합건물) 호가
            빠진 채 동이나 층만 표시되는 경우는 실무상 거의 없다. 따라서
            동 단독, 층 단독, 동+층(호없음) 같은 조합은 비정상으로 간주.
        (3) 단위 안에 괄호가 있으면 괄호와 안 내용 삭제.
            예) '제(아파트)1002호' → '1002호'
        (4) '제지하층'은 특수 처리: '제'만 제거하여 '지하층' 으로 보존.
            그 외 층 단위는 결과에서 제거.
        (5) B 매치 실패 케이스 구분:
            · A 뒤에 동/층/호 단위가 아예 없음 → 정상 (토지/일반 건물)
            · 동/층/호 단위는 있는데 6가지 조합 매치 안 됨 → 비정상으로
              간주하고 원본 주소를 유지 + 셀 글자색 빨간색.
              예) '... 제5층', '... 제101동 제5층' (호 없음) 등.
- v2.7: 담보물주소 정제 로직 세 가지 강화.
        (1) '외 n필지' 자동 제거 (전처리 단계).
        (2) B 동 이름 확장: 숫자 외에 한글 알파벳(에이/비/씨/디 등)도 허용.
        (3) B 처리 순서/규칙 변경: '제' 모두 제거 → 'n층' 제거.
- v2.6: 담보물주소 정제 실패 시 시각적 표시 추가.
        v2.4의 엄격한 매칭 기준(A1: 단어 단위 [리·동·가·읍·면·산] + 숫자,
        A2: '블럭'/'블록' 포함 단어)을 그대로 유지하되, 둘 다 매치 안 되는
        경우(즉 정제 불가능한 비정상 주소)에 대해 다음 처리 추가:
          · 정제된 주소 대신 원본 주소를 그대로 셀에 기록한다.
          · 해당 셀의 글자색을 빨간색(FF0000)으로 설정하여 사용자가
            한눈에 매치 실패 케이스를 확인할 수 있게 한다.
        구현:
          · _normalize_address 의 반환값을 (address, is_normalized: bool)
            튜플로 변경. 매치 성공 시 (정제된 주소, True), 실패 시
            (원본 주소, False).
          · _set_cell 호출 시 담보물주소 컬럼이고 is_normalized==False
            이면 openpyxl Font(color='FF0000') 적용.
- v2.5: [폐기] B 매칭 공백 유연화. v2.4 정규식이 이미 등기소 실수
        (아파트명에 제n동 붙음) 케이스를 처리하므로 불필요한 변경이었음.
- v2.4: 담보물주소 정제 로직 강화 - A1 (지번) / A2 (블럭) / B (제n동 등)
        구조의 단어 단위 매칭으로 교체.
        v2.3 의 단순한 "한글-숫자 패턴까지 잘라내기" 로직을 다음과 같이
        확장한다.
        - A1 (지번): 공백으로 분리한 단어 리스트에서, 단어1이
          [리·동·가·읍·면·산] 중 하나로 끝나고 단어2가 숫자 또는
          숫자-숫자인 첫 번째 쌍을 찾는다. 단어2 까지가 A1.
          A1 뒤에 '번지'를 붙인다. 예) '○○동 123-4', '○○면 산 10', '종로1가 5'.
        - A2 (블럭, A1 fallback): A1 이 매치 안 되면 단어 안에 '블럭' 또는
          '블록'이 포함된 첫 단어를 찾는다. 그 단어가 통째로 A2 (블럭은
          단어 안에서 앞/중간/뒤 어디든 가능). '번지'를 붙이지 않음.
          예) '에이블록1로트', '에이블럭41호', '블럭에이1-7', '식사2구역에이1블럭'.
        - B (꼬리): A 다음 텍스트의 끝부분에 붙어 있는 '제n동/제n층/제n호'
          (숫자-단위 사이 공백 없음) 조합을 추출. 일부 단위만 있어도 되고
          전체가 없어도 됨.
        - 최종: A + suffix(번지 or '') + ' ' + B에서 '제' 모두 제거
        - 둘 다 매치 안 되면 원본 주소 유지 (안전한 fallback).
        - 다중 공백은 단일 공백으로 정규화.
- v2.3: 담보물주소를 핵심 주소까지만 잘라내도록 정제.
        주소 문자열을 왼쪽부터 스캔하여 "한글 띄고 숫자" 또는
        "한글 띄고 숫자-숫자" 패턴을 처음 만나면 그 패턴 끝까지만 남기고
        뒤의 텍스트(건물명·동·호수 등)는 제거한다. (v2.4에서 더 정밀하게 교체됨)
- v2.2: 결과 컬럼에 '담보물주소' 추가 (처리결과 우측).
        등기부등본의 두 번째 페이지 최상단에 있는 부동산 표시(예:
        '[집합건물] 경기도 화성시 ...') 에서 대괄호 안의 건물 유형
        표시(`[집합건물]`, `[건물]`, `[토지]`)를 제외한 실제 주소
        부분을 추출하여 기록한다.
        - 첫 번째 페이지는 표제부 헤더 구간이라 주소가 '...' 으로
          생략될 수 있어 사용하지 않고, 항상 두 번째 페이지 상단을
          본다.
        - PDF가 1페이지뿐인 경우 또는 두 번째 페이지에 부동산 표시가
          없는 경우엔 공란.
        - 신규 함수: get_property_address(pdf_path)
        - RESULT_COLUMNS / OUTPUT_COLUMNS 에 '담보물주소' 추가 (처리결과
          뒤). v1.10 부터의 컬럼 자동-삽입 로직 덕분에 기존 입력 엑셀에
          이 컬럼이 없어도 처리결과 우측에 자동으로 삽입됨.
- v2.1: 워터마크 제거 방식을 폰트 크기 기반 페이지 필터링으로 전환.
        등기부등본 PDF의 '열 람 용' 워터마크는 본문(폰트 크기 ~10pt)보다
        훨씬 큰 폰트(약 52pt)로 그려진다는 점을 이용하여, 페이지에서 큰
        크기의 char 객체를 사전에 제거한 뒤 표 추출/텍스트 추출/삭선 검사를
        수행한다.
        - 신규: pdfplumber.Page.filter() 기반의 _filtered_page() 헬퍼
          (size >= WATERMARK_SIZE_THRESHOLD 인 char 객체 제외).
          기본 임계값은 30 (본문 최대 크기 ~17 vs 워터마크 52 사이의 안전한
          중간값).
        - 페이지를 사용하는 모든 코드 경로에 일관 적용:
            · extract_eulgu_rows (표 추출)
            · get_deungki_office (마지막 페이지 텍스트 추출)
            · is_text_struck_in_page (삭선 검사)
            · find_replacement_chae_max, check_geun_jeo_strikethrough,
              is_transferred_to_housing_finance 등 부속 함수
        - clean_watermark 함수의 워터마크 글자 제거 정규식을 제거. 페이지
          필터링 단계에서 이미 워터마크 글자가 없어졌으므로 텍스트 단계의
          후처리가 불필요. 공백 정규화 기능은 유지.
        - 이전 버전(v1.7~v1.10) 들이 다루지 못한 케이스가 자동 해결됨:
            · 본문 단어 사이에 끼어든 워터마크 (예: '채용권최고액' → '채권최고액')
            · 어느 한글이든 워터마크 글자(열/람/용)와 인접한 경우의 모호성
        - 사람 이름·지명·회사명 안의 '용' 등은 본문 크기이므로 페이지 필터링
          단계에서 영향 받지 않아 안전하게 보존된다.
- v1.10: (1) '기이전' 판정 단순화 및 다른 라벨에 우선.
             모든 매치 행에 대해 독립적으로 기이전 여부를 판정한다.
             판정 조건은 v1.9와 동일하지만(본 등기 근저당권자에 삭선이 있고
             같은 본 순위번호의 부기등기 중 최종(삭선 안 된) 근저당권자가
             '한국주택금융공사'), 적용 범위가 ① 케이스로만 제한되지 않고
             ②(근저당권자만 매치) 케이스에도 동일하게 적용된다.
             기이전으로 판정되면 그 행의 라벨은 다른 모든 라벨(일치/다수/
             개명/기말소/주소오류/공란)을 덮어쓰고 '기이전'이 된다.
             이로 인해 ① 다건 케이스에서 첫 행 외의 행(원래는 공란)이라도
             기이전이면 '기이전'이 표시되어 한 부동산에 두 줄 이상 라벨이
             표시될 수 있다.
         (2) '감액' 표시 방식 변경: 처리결과 라벨에서 '(감액)' prefix를 제거.
             대신 결과 컬럼에 '최초설정액'을 추가 (채권최고액 우측).
             - 채권최고액에 삭선이 있으면:
                 · '채권최고액' 열: 부기등기에서 가져온 변경된 최종 금액
                 · '최초설정액' 열: 본 등기에 적힌 (삭선된) 원래 금액
             - 삭선이 없으면:
                 · '채권최고액' 열: 본 등기의 금액
                 · '최초설정액' 열: 공란
         (3) 결과 컬럼 자동 추가 규칙 변경: 누락된 결과 컬럼은
             RESULT_COLUMNS 정의 순서대로 의도된 인접 위치에 삽입된다.
             예) '최초설정액' 누락 시 '채권최고액' 우측에 삽입(우측 데이터는
             자동 시프트). 이전(v1.9 이하)에는 누락된 컬럼이 모두 헤더 끝에
             추가되어 위치가 의도와 달라질 수 있었음.
- v1.9: (1) 매칭 단계를 3단계로 확장.
            ① 채무자 + 근저당권자가 모두 일치하는 본 등기가 있으면 그것만
              파싱한다. (기존 동작)
            ② ①이 하나도 없을 때, 근저당권자만 일치하는 본 등기가 있으면
              그것들을 파싱한다. 처리결과는 '개명/기말소/주소오류'.
            ③ 근저당권자조차 일치하는 본 등기가 하나도 없으면 결과 컬럼은
              모두 비우고 처리결과만 '기말소/주소오류'.
        (2) 처리결과 라벨 체계 변경.
            ① 1건 → '일치'
            ① 2건 이상 → 첫 행 '다수', 나머지 행 처리결과 공란
            ② N건 → 첫 행에만 '개명/기말소/주소오류', 나머지 공란
            ③ → '기말소/주소오류'
        (3) [v1.10에서 폐기됨] '감액' prefix 방식.
        (4) [v1.10에서 변경됨] '기이전' 판정 ① 케이스 제한.
- v1.8: 워터마크 제거 로직에서 "비공백 문자 사이에 끼어든 단일 워터마크
        글자 제거" 규칙을 삭제. 이 규칙이 사람 이름·지명·회사명에 합법적으로
        포함된 '용' 글자(예: 한용운, 김용수, 박용현, 용산구 등)를 워터마크로
        오인하여 제거함으로써 채무자/근저당권자 매칭이 실패하고 결과가
        '기말소'로 잘못 처리되는 문제를 해결.
        실제 PDF 텍스트 추출 시 본문에 워터마크가 끼어드는 사례가 발견되지
        않았고, 워터마크는 항상 양옆이 공백인 단독 글자 형태이므로
        '공백으로 둘러싸인 워터마크 제거' 규칙만으로 충분.
- v1.7: (1) 처리결과 표시 '성공' → '일치'로 변경.
        (2) 빈/잡 순위번호 행 병합 정책 강화: 순위번호가 'N' 또는 'N-N'
            형식이 아닌 모든 행은 직전 행의 연속으로 간주하여 병합.
            (이전엔 빈 문자열만 병합 대상이었음.)
        (3) 공동담보 판정 매치별 독립 판정: 매치가 2개 이상이어도 각
            매치(본 등기)에 대해 따로 판정해 각 결과 행에 표시.
            (이전엔 매치 2개 이상이면 공동담보 판정을 스킵했음.)
        (4) 공동담보 판정 검색 범위 확장: 매칭된 본 등기에 딸린 모든
            부기등기(다음 본 등기 직전까지의 같은 본 순위번호 'N-N' 행)
            를 끝까지 검사. 권리자 셀뿐 아니라 등기목적 셀에서도
            '공동담보' 텍스트를 검색.
- v1.5: 매치 2개 이상일 때도 각 행에 정상이면 '성공'을 명시적으로 표시
        (이전엔 공란이었음). 처리결과 표시 규칙이 매치 개수와 무관하게
        일관됨: 기말소 / 성공 / 감액 / 기이전 / 감액/기이전.
- v1.4: 매치가 여러 개일 때 각 매치 행마다 처리결과(감액/기이전)를 표시.
- v1.3: 채권최고액 표시에서 '원' 제거.
- v1.2: 페이지 경계에서 한 근저당권의 행이 두 페이지에 걸쳐 분리되어
        파싱이 실패하던(기말소로 잘못 처리되던) 문제 해결.
- v1.1: 접수번호 자리에 접수일자가 잘못 들어가던 문제 해결.
- v1.0: 초기 버전.

[개요]
입력 엑셀(NO/근저당권자/채무자/부동산고유번호 + 빈 결과 컬럼들)과 등기부등본
PDF 파일들로부터 근저당권 정보를 추출하여 입력 엑셀의 사본에 결과를 채워 저장한다.
기존 헤더/서식/입력 데이터는 그대로 보존되며, 결과 컬럼만 채워진다.

[사용법]
1) 자동 모드 (기본)
   - 스크립트와 같은 폴더에 입력 엑셀(.xlsx) 1개를 둔다.
   - 같은 폴더 안에 'PDF' 하위폴더를 만들고 PDF 파일들을 둔다.
     (또는 같은 폴더에 PDF를 두어도 됨)
   - 스크립트를 실행하면 자동으로 파일을 찾아 결과 엑셀을 같은 폴더에 저장.
     결과 파일명: <입력파일명>_결과.xlsx

   예시 폴더 구조:
     작업폴더/
     ├── 등기부파싱.py
     ├── 작업목록.xlsx        ← 자동 탐색됨
     ├── PDF/                 ← 자동 탐색됨
     │   ├── 1164-1996-338621.pdf
     │   └── ...
     └── (실행 후) 작업목록_결과.xlsx

2) GUI 모드 - 경로를 수동으로 선택
   python 등기부파싱.py --gui

3) CLI 모드 - 경로를 직접 지정
   python 등기부파싱.py 입력.xlsx PDF폴더 결과.xlsx

[입력 엑셀 형식]
- 컬럼명: NO / 근저당권자 / 채무자 / 부동산고유번호 (필수)
          + 유형 / 처리결과 / 공동담보 / 접수일자 / 접수번호 / 채권최고액 /
            최초설정액 / 등기소명 / 담보물주소
- 결과 컬럼은 없으면 자동으로 추가된다. 추가 위치는 RESULT_COLUMNS의
  정의 순서를 따른다. 예) 결과 컬럼이 하나도 없는 입력 엑셀이면
  '유형'이 '부동산고유번호' 우측에 들어가고, '처리결과', '공동담보' 가
  그 우측, 나머지 결과 컬럼들이 차례로 이어진다.
- 헤더는 임의 행에 있어도 됨(자동 탐색). 입력 컬럼 순서도 무관.
- 이미 결과 컬럼이 다른 위치에 있는 입력 엑셀에 대해서는 그 위치를
  그대로 유지하며 빠진 컬럼만 추가한다 (기존 데이터 안전성 우선).
- NO에 값이 있는 행만 처리 대상.

[PDF 파일명 자동 변경]
처리 완료 후 PDF 파일명이 다음 형식으로 변경된다 (원본은 사라짐):
  NNN_부동산고유번호_채무자명(유형).pdf
  예: 001_1164-1996-338621_김석균(건물).pdf
  - NNN: 작업번호 3자리 (001~999)
  - 유형: '집합건물' / '건물' / '토지' (PDF 부제에서 자동 추출)
  - 같은 부동산고유번호가 여러 NO에 있으면 가장 첫 NO 기준

[처리 규칙]
- 입력 엑셀의 부동산고유번호와 동일한 이름의 PDF 파일을 PDF 폴더에서 찾는다.
- 을구에서 '근저당권설정' 본 등기들을 다음 우선순위로 검색한다:
    ① 채무자 + 근저당권자가 모두 일치하는 본 등기
       (v3.0: 채무자 개명 추적 포함. 본 등기와 같은 본 순위번호의
        부기등기에 '개명' 등기원인이 있는 경우, 그 부기등기 권리자 셀 첫 줄의
        가장 오른쪽 어구를 'effective' 채무자명으로 간주하고 매칭에 사용.)
    ② ①이 하나도 없을 때: 근저당권자만 일치하는 본 등기 (채무자 무시)
    ③ ②도 하나도 없으면: 매치 없음
- 일치하는 본 등기가 여러 개이면 해당 NO 행 아래에 추가 행을 삽입하여 모두 기록.
  (이때 아래 NO들은 그만큼 밀린다)
- 유형: 첫 페이지 부제로부터 '집합건물' / '건물' / '토지' 중 하나.
  처리 결과(매치 유무)와 무관하게 항상 채워진다.
- 처리결과 (라벨, 기이전 판정 이전 1차 라벨):
    · ① 채무자+근저당권자 매치 1건 → '일치'
    · ① 채무자+근저당권자 매치 2건 이상 → 첫 행 '다수', 나머지 행 공란
    · ② 근저당권자만 매치 → 첫 행에만 '개명/기말소/주소오류', 나머지 행 공란
    · ③ 매치 없음 → 결과 컬럼 대부분 공란, 처리결과만 '기말소/주소오류'.
      단 등기소명/유형/담보물주소는 PDF에서 객관적으로 뽑힌 정보이므로
      채워진다 (v3.0).
- 기이전 판정 (1차 라벨을 덮어쓴다):
    · 모든 매치 행에 대해 독립적으로 다음 조건을 검사:
        본 등기의 근저당권자에 삭선이 있고, 같은 본 순위번호의 부기등기 중
        최종(가장 마지막의 삭선 안 된) 근저당권자가 '한국주택금융공사'.
    · 기이전이면 그 행의 처리결과 라벨은 (1차 라벨이 무엇이든) '기이전'.
    · 따라서 ① 다건의 경우 첫 행 외의 행(원래 공란)도 기이전이면 '기이전'이
      표시되어, 한 부동산에 두 줄 이상 처리결과 라벨이 보일 수 있다.
- 채권최고액 / 최초설정액 (감액 처리):
    · 본 등기의 채권최고액에 삭선이 없으면:
        - 채권최고액 = 본 등기 금액
        - 최초설정액 = 공란
    · 본 등기의 채권최고액에 삭선이 있으면:
        - 채권최고액 = 같은 본 순위번호의 'n-n번근저당권변경' 부기등기 중
          삭선되지 않은 최종 금액
        - 최초설정액 = 본 등기에 적힌(삭선된) 원래 금액
    · v3.0: 셀 값은 정수로 저장하고 셀 표시형식 '#,##0' (천단위 구분기호)
      적용. 텍스트가 아니라 진짜 숫자 셀이라 합계/필터 등 가능.
- 공동담보('O'): 매치된 각 본 등기별로 독립 판정 (기존과 동일).
    · v3.0: 공동담보 'O' 표시되는 부동산의 담보물주소 끝에 한 칸 띄고
      '[건물][토지]' 라벨 추가 (정제된 주소든 원본 보존된 비정상 주소든
      동일 처리).
- 등기소명: 마지막 페이지 '관할등기소' 다음 텍스트.
  v3.0: ③ 케이스에서도 채움.
- 접수일자: 'YYYY-MM-DD' 형식으로 정규화
- 담보물주소: 두 번째 페이지 최상단의 부동산 표시에서 추출.
    · 형식: '[집합건물] 경기도 ...' 또는 '[건물] 서울특별시 ...' 또는
      '[토지] 경기도 ...' 등.
    · 대괄호 안의 건물 유형 표시(`[집합건물]` 등)는 제외하고 뒤의 주소만
      기록한다.
    · 첫 번째 페이지는 표제부 헤더 구간이라 주소가 '...' 으로 생략될 수
      있어 사용하지 않고, 항상 두 번째 페이지 상단을 본다.
    · 추출한 주소는 다음 규칙으로 정제된다 (단어 단위 매칭):
        A1 (지번): 단어1이 [리·동·가·읍·면·산] 으로 끝나고 단어2가 숫자[-숫자]
          인 첫 번째 쌍 → 단어2 까지가 A, A 뒤에 '번지' 붙임.
          예) '경기도 화성시 ○○동 123-4 ○○아파트 제101동 제602호'
              → '경기도 화성시 ○○동 123-4번지 101동 602호'
        A2 (블럭, A1 fallback): A1 안 되면 단어 안에 '블럭' 또는 '블록'이
          포함된 첫 단어 → 그 단어까지가 A, '번지' 안 붙임.
          예) '... 진위3일반산업단지 블럭에이1-7' → 그대로 유지
              '식사동 식사2구역에이1블럭 일산자이센트리지 제101동...'
              → '식사동 식사2구역에이1블럭 101동...'
        B: A 다음 텍스트 끝에 붙은 '제n동/제n층/제n호' 조합을 찾아 '제'를
          제거하고 A 뒤에 공백으로 이어 붙인다. 일부 단위만 있거나 없을 수
          있음.
        둘 다 매치 안 되면 원본 주소를 그대로 유지.
    · PDF가 1페이지뿐이거나 부동산 표시를 못 찾으면 공란.
"""
import os
import re
import sys
import traceback
from pathlib import Path

import pdfplumber
from openpyxl import load_workbook


# ===========================================================================
# 1. PDF 파싱 헬퍼
# ===========================================================================

# 워터마크 필터링 임계값 (이 크기 이상의 char 객체는 워터마크로 간주)
# 등기부 PDF의 본문은 일반적으로 9~17pt, '열 람 용' 워터마크는 약 52pt이다.
# 30은 그 사이의 안전한 중간값.
WATERMARK_SIZE_THRESHOLD = 30


def _is_watermark_char(obj):
    """page.filter 에서 사용할 워터마크 판정 함수.

    obj가 char 타입이고 size가 임계값 이상이면 워터마크로 간주.
    char가 아닌 객체(line, rect, curve 등)는 모두 유지해야 표 추출이
    정상 작동하므로 항상 비-워터마크로 본다.
    """
    if obj.get('object_type') != 'char':
        return False
    return obj.get('size', 0) >= WATERMARK_SIZE_THRESHOLD


def _filtered_page(page):
    """워터마크(큰 폰트 char)를 제외한 페이지를 반환한다.

    pdfplumber.Page.filter(test_function) 은 test_function 이 True 를 반환한
    객체만 유지한다. 우리는 _is_watermark_char 가 True 인 객체(워터마크)를
    제외하고 싶으므로 not _is_watermark_char 로 감싼다.
    """
    return page.filter(lambda obj: not _is_watermark_char(obj))


def clean_watermark(text):
    """공백 정규화 함수 (v2.1: 워터마크 글자 제거 정규식은 제거됨).

    v1.x 에서는 페이지에서 텍스트를 추출한 후 한글 워터마크 글자('열/람/용')
    를 정규식으로 제거했지만, v2.1 부터는 페이지 단계에서 폰트 크기 기반으로
    워터마크 char 객체 자체를 걸러내므로 텍스트에는 애초에 워터마크 글자가
    들어오지 않는다. 이 함수는 이름 호환을 위해 유지하되 공백 정규화 역할만
    수행한다.
    """
    if not text:
        return ''
    s = text
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n[ \t]+', '\n', s)
    return s.strip()


def normalize_korean_date(text):
    """'2016년2월18일' 같은 한국어 날짜를 'YYYY-MM-DD' 텍스트로 변환

    매치 안 되면 원본 텍스트를 그대로 반환한다.
    """
    if not text:
        return ''
    s = text.strip()
    m = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', s)
    if m:
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        return f"{y}-{mo:02d}-{d:02d}"
    return s


def is_word_struck(word, lines, page_height, x_overlap_ratio=0.5):
    """단어 영역에 수평선(삭선)이 있는지 검사

    word: pdfplumber word dict (top, bottom, x0, x1; top-left origin)
    lines: page.lines (PDF 좌표; bottom-left origin)
    """
    pdf_y_top = page_height - word['bottom']  # PDF 좌표상 윗변
    pdf_y_bot = page_height - word['top']     # PDF 좌표상 아랫변
    word_height = pdf_y_bot - pdf_y_top
    if word_height <= 0:
        return False
    # 단어의 위/아래 20%를 제외한 중간 영역에 수평선이 있어야 삭선
    upper = pdf_y_top + word_height * 0.2
    lower = pdf_y_bot - word_height * 0.2
    word_width = word['x1'] - word['x0']
    if word_width <= 0:
        return False

    for ln in lines:
        if ln['y0'] != ln['y1']:
            continue
        ly = ln['y0']
        if upper - 1.5 <= ly <= lower + 1.5:
            overlap = max(0, min(ln['x1'], word['x1']) - max(ln['x0'], word['x0']))
            if overlap / word_width >= x_overlap_ratio:
                return True
    return False


def is_text_struck_in_page(target_name, page, search_y_top=None, search_y_bottom=None):
    """페이지에서 target_name과 매치되는 단어 묶음에 삭선이 있는지 검사

    search_y_top/bottom: top-left 좌표계, 검색 범위 제한 (을구 행 영역 등)
    target_name 안의 토큰 중 충분히 긴 것이 모두 삭선되어 있으면 True.
    """
    if not target_name:
        return False
    words = page.extract_words()
    lines = page.lines
    ph = page.height

    # target에서 의미 있는 토큰 추출 (2자 이상)
    tokens = [t for t in re.split(r'\s+', target_name) if len(t) >= 2]
    if not tokens:
        return False

    # 페이지 안의 단어를 줄 단위로 묶어 텍스트 매칭
    # 같은 y(top)에 있는 단어들을 한 줄로 묶음
    line_groups = {}
    for w in words:
        if search_y_top is not None and w['top'] < search_y_top - 2:
            continue
        if search_y_bottom is not None and w['bottom'] > search_y_bottom + 2:
            continue
        key = round(w['top'])
        line_groups.setdefault(key, []).append(w)

    for key, group in line_groups.items():
        group_sorted = sorted(group, key=lambda w: w['x0'])
        joined = ''.join(w['text'] for w in group_sorted)
        # target의 첫 토큰이 이 줄에 등장하는지 확인
        first_tok = tokens[0]
        if first_tok in joined:
            # 이 줄의 단어 중 target_name 토큰을 포함하는 단어들의 삭선 여부
            relevant = [w for w in group_sorted if any(t in w['text'] for t in tokens)]
            if not relevant:
                continue
            # 모든 관련 단어가 삭선이면 True
            all_struck = all(
                is_word_struck(w, lines, ph) for w in relevant
            )
            if all_struck:
                return True
    return False


# ===========================================================================
# 2. 을구 표 추출 (페이지 가로지름 통합)
# ===========================================================================

def _is_eulgu_header(cell):
    if not cell:
        return False
    return ('을' in cell and '구' in cell and '소유권 이외' in cell)


def _is_other_section_header(cell):
    if not cell:
        return False
    return ('갑 구' in cell and '소유권에 관한' in cell) or \
           ('표 제 부' in cell)


def _is_column_header_row(row):
    if not row:
        return False
    first = (row[0] or '').strip() if row[0] else ''
    return first == '순위번호'


def _is_valid_sun_wi(text):
    """순위번호 셀이 유효한 순위번호 패턴인지 검사.

    유효 패턴: 'N' (본 등기) 또는 'N-N' (부기등기), N은 숫자.
    그 외(빈 문자열, 잡 텍스트 등)는 무효 → 직전 행의 연속으로 본다.

    워터마크 글자가 끼어 있을 수 있으므로 clean_watermark 후 검사.
    """
    if text is None:
        return False
    s = clean_watermark(str(text)).strip()
    if not s:
        return False
    # 'N' 또는 'N-N' 형태만 유효
    return bool(re.fullmatch(r'\d+(-\d+)?', s))


def _merge_continuation_into_last(rows, new_row, pidx, y_top, y_bot):
    """순위번호가 유효한 순위번호 패턴이 아닌 행을 직전 행과 병합한다.

    [원칙]
    을구 표의 데이터 행은 반드시 순위번호 셀에 'N' 또는 'N-N' 형식의
    값이 있다(본 등기 'N' 또는 부기등기 'N-N'). 따라서 표 추출 결과에
    순위번호가 비어있거나 잡 텍스트인 행이 있다면 그건 데이터적으로
    독립된 행이 아니라 직전 행의 연속이다.
    대표적 발생 케이스:
      - 한 행이 두 페이지에 걸쳐 잘림(페이지 경계 분단)
      - 한 본 등기 안에서 집합건물의 부동산표시 변경 같은 추가 정보가
        같은 셀이 아닌 별도 행처럼 추출되는 경우
    어느 쪽이든 처리 방식은 동일: 직전 행에 셀별로 이어 붙인다.

    조건: 새 행의 순위번호 셀이 유효 패턴이 아니고, 직전 행이 존재.
    동작: 직전 행 셀들에 새 행의 셀 텍스트를 줄바꿈으로 이어 붙이고,
          y_bot은 새 행의 y_bot으로 확장(행이 여러 영역에 걸쳐 있다는 정보).
    반환값: 병합 처리되었으면 True, 아니면 False (False면 호출자가 새 행으로 추가).
    """
    if not rows:
        return False
    first = (new_row[0] or '') if new_row else ''
    if _is_valid_sun_wi(first):
        return False  # 정상 순위번호가 있으면 새 행이지 연속이 아님
    # 직전 행이 같은 PDF의 마지막 행 - 셀별로 텍스트 이어붙임
    last_row, last_pidx, last_y_top, last_y_bot = rows[-1]
    merged = []
    n = max(len(last_row), len(new_row))
    for k in range(n):
        a = (last_row[k] or '') if k < len(last_row) else ''
        b = (new_row[k] or '') if k < len(new_row) else ''
        a = a.rstrip('\n')
        b = b.lstrip('\n')
        if a and b:
            merged.append(a + '\n' + b)
        else:
            merged.append(a or b)
    # bbox는 직전 행 영역만 (삭선 검색은 본 등기 헤더가 있는 첫 페이지에서만 의미)
    rows[-1] = (merged, last_pidx, last_y_top, last_y_bot)
    return True


def extract_eulgu_rows(pdf_path):
    """모든 페이지의 표를 훑어 을구의 데이터 행만 순서대로 반환

    또한 각 행이 등장한 페이지 번호와 그 페이지에서의 y 범위를 함께 반환.
    페이지 경계에서 한 행이 두 페이지에 걸쳐 잘린 경우 자동으로 병합한다.
    """
    rows = []  # [(row_data_list, page_index, y_top, y_bottom)]
    with pdfplumber.open(pdf_path) as pdf:
        in_eulgu = False
        for pidx, raw_page in enumerate(pdf.pages):
            page = _filtered_page(raw_page)  # 워터마크 제거된 페이지로 표 추출
            tables = page.find_tables()
            for tbl in tables:
                table_data = tbl.extract()
                if not table_data:
                    continue
                first_cell = table_data[0][0] if table_data[0] else ''
                # 새 섹션의 시작 헤더 셀이 있는 경우
                if _is_eulgu_header(first_cell):
                    in_eulgu = True
                    rows_to_process = table_data[1:]
                elif _is_other_section_header(first_cell):
                    in_eulgu = False
                    continue
                else:
                    # 섹션 헤더가 없는 표 = 이전 페이지의 연속일 가능성
                    if not in_eulgu:
                        continue
                    rows_to_process = table_data

                # 표의 행별 bbox를 가져와서 y 범위 매핑
                # tbl.rows[i].bbox = (x0, top, x1, bottom)
                offset = len(table_data) - len(rows_to_process)
                for i, r in enumerate(rows_to_process):
                    if not any(cell for cell in r):
                        continue
                    if _is_column_header_row(r):
                        continue
                    # bbox 가져오기
                    actual_idx = i + offset
                    try:
                        bbox = tbl.rows[actual_idx].bbox
                        y_top = bbox[1]
                        y_bot = bbox[3]
                    except (IndexError, AttributeError):
                        y_top = None
                        y_bot = None

                    # 페이지 경계 연속 처리: 표의 첫 데이터 행이고 순위번호가 비어있으면
                    # 직전 행에 셀별로 이어붙임
                    if _merge_continuation_into_last(rows, r, pidx, y_top, y_bot):
                        continue
                    rows.append((r, pidx, y_top, y_bot))
    return rows


# ===========================================================================
# 3. 행 데이터 파싱
# ===========================================================================

def parse_eulgu_row(raw_row):
    """을구 한 행 데이터를 파싱해 dict 반환"""
    if len(raw_row) < 5:
        # 컬럼 수가 부족한 경우 빈 셀로 채움
        raw_row = list(raw_row) + [''] * (5 - len(raw_row))

    sun_wi = clean_watermark(raw_row[0] or '').strip()
    deungki_mokjeok = clean_watermark(raw_row[1] or '').strip()
    jeobsu_raw = raw_row[2] or ''
    deungki_inwon = clean_watermark(raw_row[3] or '').strip()
    gwon_lija_raw = clean_watermark(raw_row[4] or '').strip()

    # 접수일자 / 접수번호
    # 줄바꿈 형식이 PDF마다 일정하지 않으므로(워터마크 끼어듦, 줄 합쳐짐 등),
    # 셀 전체 텍스트에서 날짜 패턴과 '제XXXX호' 패턴을 독립적으로 찾는다.
    jeobsu_clean = clean_watermark(jeobsu_raw)
    # 1) 날짜: '2020년3월20일' 패턴
    jeobsu_date = ''
    m = re.search(r'\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일', jeobsu_clean)
    if m:
        jeobsu_date = normalize_korean_date(m.group(0))
    # 2) 접수번호: '제XXXX호' 패턴 (숫자만 추출)
    jeobsu_no = ''
    m = re.search(r'제\s*(\d+)\s*호', jeobsu_clean)
    if m:
        jeobsu_no = m.group(1)

    # 채권최고액
    chae_max_num = ''
    chae_max_disp = ''
    m = re.search(r'채권최고액\s*금?\s*([\d,]+)\s*원', gwon_lija_raw)
    if m:
        chae_max_num = m.group(1).replace(',', '')
        chae_max_disp = m.group(1)

    # 채무자
    chae_mu_ja = ''
    m = re.search(r'채무자\s+([^\s\n,]+)', gwon_lija_raw)
    if m:
        chae_mu_ja = m.group(1).strip()

    # 근저당권자
    geun_jeo = ''
    m = re.search(r'근저당권자\s+(\S+)', gwon_lija_raw)
    if m:
        geun_jeo = m.group(1).strip()

    # 공동담보 키워드 (본 등기 텍스트에 포함)
    has_gongdong = '공동담보' in gwon_lija_raw

    # 본 등기 vs 부기등기 구분
    is_buggi = '-' in sun_wi  # 8-2 같은 형식
    is_geun_jeo_setup = '근저당권설정' in deungki_mokjeok

    return {
        'sun_wi': sun_wi,
        'is_buggi': is_buggi,
        'deungki_mokjeok': deungki_mokjeok,
        'is_geun_jeo_setup': is_geun_jeo_setup,
        'jeobsu_date': jeobsu_date,
        'jeobsu_no': jeobsu_no,
        'deungki_inwon': deungki_inwon,
        'gwon_lija_raw': gwon_lija_raw,
        'chae_max_num': chae_max_num,
        'chae_max_disp': chae_max_disp,
        'chae_mu_ja': chae_mu_ja,
        'geun_jeo': geun_jeo,
        'has_gongdong_keyword': has_gongdong,
    }


# ===========================================================================
# 4. 등기소명 추출
# ===========================================================================

def get_deungki_office(pdf_path):
    """관할등기소 이름 추출"""
    with pdfplumber.open(pdf_path) as pdf:
        for raw_page in reversed(pdf.pages):
            page = _filtered_page(raw_page)
            text = clean_watermark(page.extract_text() or '')
            for line in text.split('\n'):
                m = re.search(r'관할등기소\s+(.+)', line)
                if m:
                    return m.group(1).strip()
    return ''


def get_property_type(pdf_path):
    """부동산 유형 추출 (v3.0: '집합건물' / '건물' / '토지' 3가지로 구분)

    PDF 첫 페이지 상단의 부제 영역(예: '- 집합건물 -', '- 건물 -', '- 토지 -')을
    검사한다. 부제 그대로 반환. 못 찾으면 ''.
    """
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return ''
        # 첫 페이지의 상단(상위 1/3) 텍스트만 검사
        page = _filtered_page(pdf.pages[0])
        text = page.extract_text() or ''
        head = text[:500]  # 보통 부제가 첫 몇 줄 안에 있음
        # 부제 패턴 우선 - 그대로 반환
        m = re.search(r'-\s*(집합건물|건물|토지)\s*-', head)
        if m:
            return m.group(1)
        # 부제가 안 잡히면 본문에서 추측 (드문 케이스)
        if '집합건물' in head:
            return '집합건물'
        if '건물의 표시' in head:
            return '건물'
        if '토지의 표시' in head and '대지권의 목적인 토지' not in head:
            return '토지'
    return ''


# 담보물주소 추출에 사용하는 대괄호 라벨 패턴
# '[집합건물]', '[건물]', '[토지]' 등을 인식한다.
_PROPERTY_BRACKET_RE = re.compile(r'\[\s*(?:집합건물|건물|토지|구분건물)\s*\]\s*(.+)')


def get_property_address(pdf_path):
    """담보물주소 추출 - 두 번째 페이지 최상단의 부동산 표시에서

    반환: (address, is_normalized: bool)
      address      : 추출/정제된 주소 (빈 문자열일 수 있음)
      is_normalized: A1/A2 매치 성공으로 정제 완료되었는지 여부.
                     False 이면 호출자가 셀 글자색을 빨간색으로 표시.
                     빈 주소(부동산 표시 못 찾음, PDF 페이지 1개뿐 등)는 True
                     로 본다 (셀이 비어있으므로 색칠 의미 없음).

    형식 예:
      [집합건물] 경기도 화성시 ○○구 ○○동 123-4 ...
      [건물] 서울특별시 강남구 ○○로 12
      [토지] 경기도 ...

    대괄호 안의 유형 라벨은 제외하고 뒤의 주소 부분만 정제하여 반환한다.
    첫 번째 페이지는 표제부 영역이라 주소가 '...' 으로 생략될 수 있어
    사용하지 않는다. 두 번째 페이지에서 못 찾으면 빈 문자열.

    탐색 전략:
      - 두 번째 페이지의 상위 25% 영역 텍스트를 우선 검사.
      - 그래도 못 찾으면 두 번째 페이지 전체 텍스트에서 검사 (보수적 fallback).
      - 라인 단위로 검사하므로 같은 페이지에 라벨이 여러 번 나오는 경우
        가장 앞쪽(상단) 것을 채택.
    """
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 2:
            return ('', True)
        raw_page = pdf.pages[1]  # 두 번째 페이지 (0-indexed)
        page = _filtered_page(raw_page)

        # 1) 페이지 상단 영역(상위 25%) 우선
        ph = raw_page.height
        try:
            top_crop = page.crop((0, 0, raw_page.width, ph * 0.25))
            top_text = top_crop.extract_text() or ''
        except Exception:
            top_text = ''

        for line in top_text.split('\n'):
            line = clean_watermark(line)
            m = _PROPERTY_BRACKET_RE.search(line)
            if m:
                return _normalize_address(m.group(1))

        # 2) 페이지 전체 텍스트에서 fallback 검사
        full_text = page.extract_text() or ''
        for line in full_text.split('\n'):
            line = clean_watermark(line)
            m = _PROPERTY_BRACKET_RE.search(line)
            if m:
                return _normalize_address(m.group(1))

    return ('', True)


# 담보물주소 정제용 패턴 (v2.7)
# 단어 단위 매칭으로 핵심 주소를 추출하고 끝부분의 동/층/호를 정리한다.

# A1 (지번): 단어1의 끝글자가 이 중 하나
_ADDR_A1_SUFFIX = ('리', '동', '가', '읍', '면', '산')
# A1: 단어2가 숫자 또는 숫자-숫자 단독
_ADDR_NUMBER_WORD_RE = re.compile(r'^\d+(?:-\d+)?$')

# B 단위 (v2.8):
# 각 단위는 '제' + 임의 비공백 문자열 + 단위 (동/층/호).
# 예: 제101동, 제에이동, 제가1동, 제(아파트)1동, 제(아파트)1002호, 제지하층
_ADDR_B_DONG = r'제\S*?동'
_ADDR_B_CHEUNG = r'제\S*?층'
_ADDR_B_HO = r'제\S*?호'

# B 조합 5가지 (긴 패턴부터 alternative 우선순위 배치):
#   동+층+호 / 동+호 / 층+호 / 호 단독
# (동 단독, 층 단독, 동+층(호없음)은 실무상 거의 없으므로 비정상 처리.)
# 매치는 항상 주소 끝($)에서 끝나야 한다.
_ADDR_B_ALTS = [
    rf'{_ADDR_B_DONG}\s+{_ADDR_B_CHEUNG}\s+{_ADDR_B_HO}',  # 동+층+호
    rf'{_ADDR_B_DONG}\s+{_ADDR_B_HO}',                       # 동+호
    rf'{_ADDR_B_CHEUNG}\s+{_ADDR_B_HO}',                     # 층+호
    rf'{_ADDR_B_HO}',                                         # 호 단독
]
_ADDR_B_RE = re.compile(rf'(?:{"|".join(_ADDR_B_ALTS)})\s*$')

# B 단위 존재 검사 (v2.8): A 뒤의 텍스트에 동/층/호 단위가 하나라도
# 등장하는데 6가지 조합 매치(_ADDR_B_RE)는 실패한 경우 = 비정상 케이스.
# 이런 경우 호출자가 원본 주소를 유지하고 빨간색으로 표시한다.
_ADDR_B_UNIT_PRESENT_RE = re.compile(r'제\S*?[동층호]')


def _clean_b_unit(unit_text):
    """B의 한 어구를 처리한다 (v2.8):
       1) '제지하층' → '지하층' (특수 처리)
       2) 괄호와 그 안 내용 제거: '제(아파트)1002호' → '제1002호'
       3) 맨 앞의 '제' 제거: '제1002호' → '1002호'
    """
    if unit_text == '제지하층':
        return '지하층'
    s = re.sub(r'\([^)]*\)', '', unit_text)
    s = re.sub(r'^제', '', s)
    return s

# v2.7: 전처리용 - '외 N필지' 제거 정규식
# - 외/숫자/필지 사이 공백 모두 허용 (0개 이상)
# - 매치된 부분을 단일 공백으로 치환하여 앞뒤 단어가 붙지 않게 한다.
# - '외' 뒤가 숫자여야 매치되므로 '외부산업' 같은 단어는 영향 없음.
_ADDR_OEI_PILJI_RE = re.compile(r'\s*외\s*\d+\s*필지\s*')


def _find_a1_end_index(words):
    """A1 매치 탐색.
    단어1이 [리·동·가·읍·면·산] 으로 끝나고 단어2가 숫자[-숫자] 인 첫 쌍의
    단어2 인덱스를 반환. 못 찾으면 None.
    """
    for i in range(len(words) - 1):
        if (words[i].endswith(_ADDR_A1_SUFFIX)
                and _ADDR_NUMBER_WORD_RE.match(words[i + 1])):
            return i + 1
    return None


def _find_a2_end_index(words):
    """A2 (블럭/블록) 탐색.
    단어 안에 '블럭' 또는 '블록' 이 포함된 첫 단어의 인덱스를 반환.
    못 찾으면 None.
    블럭/블록은 단어 앞/중간/뒤 어디에 있어도 매치된다.
    예) '에이블록1로트', '에이블럭41호', '블럭에이1-7', '식사2구역에이1블럭'
    """
    for i, w in enumerate(words):
        if '블럭' in w or '블록' in w:
            return i
    return None


def _normalize_address(addr):
    """담보물주소 정규화 (v2.9):
       반환: (정제된 주소, is_normalized: bool)
         is_normalized=True  : A1 또는 A2 매치 성공, 정제 완료
         is_normalized=False : 매치 실패 또는 비정상. 공백만 정규화한 원본을
                               함께 반환. 호출자는 셀 글자색을 빨간색으로 표시.

       처리 순서:
       (-1) (v2.9) '내제조표' 단어 검사: 포함되어 있으면 정제 건너뛰고
            원본 + 빨강 반환
       0) '외 n필지' 제거 (전처리)
       1) 공백 정규화
       2) 단어 분리 후 A1 우선, A2 (블럭) fallback 으로 핵심 주소 추출
       3) 끝부분의 B 추출. B는 다음 5가지 조합 중 하나:
            동+층+호 / 동+호 / 층+호 / 호 단독 / 없음
          (한국 등기 실무: 호가 등기 단위이므로 호 없는 동/층만은 비정상)
          각 단위는 '제' + 임의 비공백 + (동|층|호).
       4) B 단위 처리:
            · 괄호와 안 내용 삭제: '제(아파트)1002호' → '제1002호'
            · '제' 제거: '제1002호' → '1002호'
            · '제지하층' → '지하층' (보존)
            · 그 외 층 단위는 결과에서 제거
       5) A1 케이스는 '번지' suffix 추가, A2 케이스는 suffix 없음
       6) 매치 실패 처리:
            · A1/A2 둘 다 매치 실패 → 원본 주소 (is_normalized=False)
            · A 매치 성공, B 매치 실패의 두 케이스:
                - A 뒤에 동/층/호 단위가 아예 없음 → 정상 (토지/일반 건물)
                - 동/층/호 단위는 있지만 5가지 조합 매치 안 됨 (예: 동 단독,
                  층 단독, 동+층 호없음 등) → 비정상, 원본 주소 +
                  is_normalized=False

    예시:
      내제조표: '경기도 화성시 ○○동 내제조표 ○○아파트'
            → ('경기도 화성시 ○○동 내제조표 ○○아파트', False)  # 빨강
      외n필지: '경기도 평택시 ○○면 ○○리 100 외 3필지'
            → ('경기도 평택시 ○○면 ○○리 100번지', True)
      동+층+호: '경기도 화성시 ○○동 123-4 ○○아파트 제101동 제2층 제202호'
            → ('경기도 화성시 ○○동 123-4번지 101동 202호', True)
      한글동: '경기도 화성시 ○○동 123-4 제가1동 제202호'
            → ('경기도 화성시 ○○동 123-4번지 가1동 202호', True)
      괄호 호: '경기도 화성시 ○○동 123-4 제(아파트)1002호'
            → ('경기도 화성시 ○○동 123-4번지 1002호', True)
      지하층: '경기도 화성시 ○○동 123-4 ○○아파트 제101동 제지하층 제B01호'
            → ('경기도 화성시 ○○동 123-4번지 101동 지하층 B01호', True)
      A2: '식사동 식사2구역에이1블럭 일산자이센트리지 제101동 제2층 제202호'
            → ('식사동 식사2구역에이1블럭 101동 202호', True)
      매치 실패: '서울특별시 강남구 테헤란로 12 ○○빌딩'
            → ('서울특별시 강남구 테헤란로 12 ○○빌딩', False)
    """
    if not addr:
        return ('', True)  # 빈 입력은 정상 (셀 자체가 비어있을 것)

    # (v2.9) '내제조표' 단어가 포함되어 있으면 정제하지 않고 원본 + 빨간색.
    # 다른 모든 전처리/매칭보다 먼저 검사한다.
    if '내제조표' in addr:
        # 원본을 그대로 반환 (공백 정규화만 적용)
        normalized_only = re.sub(r'\s+', ' ', addr).strip()
        return (normalized_only, False)

    # 0) '외 n필지' 제거 - 다른 모든 처리 이전에 가장 먼저 적용
    s = _ADDR_OEI_PILJI_RE.sub(' ', addr)

    # 1) 공백 정규화
    s = re.sub(r'\s+', ' ', s).strip()
    if not s:
        return ('', True)

    # 2) 단어 분리 후 A1 우선 → A2 fallback
    words = s.split(' ')

    a1_end = _find_a1_end_index(words)
    if a1_end is not None:
        a_words = words[:a1_end + 1]
        rest_words = words[a1_end + 1:]
        suffix = '번지'
    else:
        a2_end = _find_a2_end_index(words)
        if a2_end is None:
            return (s, False)  # 매치 없음 - 원본 유지 + 빨간색 표시
        a_words = words[:a2_end + 1]
        rest_words = words[a2_end + 1:]
        suffix = ''

    a_text = ' '.join(a_words)
    rest = ' '.join(rest_words)

    # 3) B 추출 - 5가지 조합 중 하나로 끝나야 매치 (동+층+호, 동+호, 층+호,
    #    호 단독, 또는 없음). 동/층/호 단위는 '제' + 임의 비공백 + 단위.
    b_match = _ADDR_B_RE.search(rest)

    if b_match:
        # B 정상 매치
        b_text = b_match.group(0).strip()
        result = a_text + suffix
        cleaned_units = []
        for w in b_text.split():
            u = _clean_b_unit(w)
            # '층' 단위는 결과에서 제거 (단 '지하층'은 보존)
            if u.endswith('층') and u != '지하층':
                continue
            cleaned_units.append(u)
        if cleaned_units:
            result += ' ' + ' '.join(cleaned_units)
        return (result, True)
    else:
        # B 매치 실패 - 두 가지 경우 구분:
        # (a) A 뒤에 동/층/호 단위가 아예 없음 → 정상 (토지/일반 건물 등)
        # (b) 동/층/호 단위는 있지만 5가지 조합 매치 안 됨 → 비정상 (예:
        #     동 단독, 층 단독, 동+층 호없음 등) → 원본 주소 유지 + 빨간색 표시
        if _ADDR_B_UNIT_PRESENT_RE.search(rest):
            # (b) 비정상
            return (s, False)
        else:
            # (a) 정상 - B 없음
            return (a_text + suffix, True)


def sanitize_filename(name):
    """파일명에 쓸 수 없는 문자 제거 (Windows/Mac/Linux 공통)"""
    if not name:
        return ''
    # 금지 문자 제거: \ / : * ? " < > | 그리고 제어문자
    s = re.sub(r'[\\/:\*\?"<>\|\x00-\x1f]', '', str(name))
    s = s.strip().rstrip('.')  # Windows: trailing '.' 금지
    return s


def rename_pdf_after_processing(pdf_path, no_disp, gyu_no, chaemu, log_callback=None):
    """작업 완료 후 PDF 파일명을 'NNN_고유번호_채무자(유형).pdf' 로 변경

    - NNN: 작업번호 3자리 zero-pad (001, 002, ...)
    - 유형: '건물' 또는 '토지' (PDF에서 추출, 못 찾으면 빈 괄호 안 넣음)
    - 같은 이름의 파일이 이미 있거나 권한 문제로 실패하면 로그만 남기고 통과

    반환: 변경 후의 Path (실패 시 원본 Path)
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return pdf_path

    # 작업번호 3자리
    try:
        no_int = int(no_disp)
        no_part = f"{no_int:03d}"
    except (ValueError, TypeError):
        no_part = sanitize_filename(no_disp) or '000'

    chaemu_part = sanitize_filename(chaemu) or '미상'
    gyu_part = sanitize_filename(gyu_no) or '미상'

    # 부동산 유형 추출
    try:
        ptype = get_property_type(str(pdf_path))
    except Exception:
        ptype = ''

    type_part = f"({ptype})" if ptype else ''
    new_name = f"{no_part}_{gyu_part}_{chaemu_part}{type_part}.pdf"
    new_path = pdf_path.with_name(new_name)

    if new_path == pdf_path:
        return pdf_path  # 이미 올바른 이름

    if new_path.exists():
        # 동일 이름 충돌 → 변경하지 않고 로그만
        if log_callback:
            log_callback(f"  [PDF 이름변경 건너뜀] 이미 같은 이름 존재: {new_name}")
        return pdf_path

    try:
        pdf_path.rename(new_path)
        if log_callback:
            log_callback(f"  PDF 이름변경: {pdf_path.name} → {new_name}")
        return new_path
    except OSError as exc:
        if log_callback:
            log_callback(f"  [PDF 이름변경 실패] {pdf_path.name}: {exc}")
        return pdf_path


# ===========================================================================
# 5. 매칭 / 결과 생성 메인 로직
# ===========================================================================

def normalize_name(name):
    """이름 비교를 위한 정규화: 공백/괄호 등 제거"""
    if name is None:
        return ''
    s = str(name).strip()
    # 주식회사/(주) 표현 통일
    s = s.replace('(주)', '주식회사')
    s = re.sub(r'\s+', '', s)
    return s


def geunjeo_matches(input_name, parsed_name):
    """근저당권자 매칭 - 단방향 포함

    입력 엑셀의 이름(input_name)이 등기부의 이름(parsed_name) 안에 포함되면 일치.
    예) 입력 '우리은행' ⊂ 등기부 '주식회사우리은행'  → 일치
        입력 '주식회사우리은행' ⊂ 등기부 '우리은행' → 불일치 (등기부가 더 짧음)
    """
    a = normalize_name(input_name)
    b = normalize_name(parsed_name)
    if not a or not b:
        return False
    return a in b


def chaemu_matches(input_name, parsed_name):
    """채무자 매칭 - 양방향 포함 (이름이 짧을 수 있어 유연하게)"""
    a = normalize_name(input_name)
    b = normalize_name(parsed_name)
    if not a or not b:
        return False
    return a in b or b in a


def get_effective_chaemu(row_info, parsed_rows):
    """본 등기에 대한 'effective' 채무자명 반환 (v3.0).

    같은 본 순위번호의 부기등기 중 등기원인에 '개명'이 포함된 가장 마지막
    (부기등기 순위번호가 가장 큰) 행을 찾아, 그 권리자 셀 첫 줄의 마지막
    어구를 effective 채무자명으로 사용한다. 그런 부기등기가 없으면 본 등기의
    원래 chae_mu_ja 그대로 반환.

    이미지로 확인된 실제 패턴:
      14번 본 등기: 채무자 '라○' (삭선)
      14-2 부기등기: 등기원인 '...개명', 권리자 '라○의 성명(명칭) 나○'
      → 14번 본 등기의 effective 채무자명 = '나○'

    개명이 여러 번 일어난 경우(예: 14-1 가→나, 14-3 나→다)는 가장 마지막 개명의
    새 이름이 현재 effective 채무자명이다.
    """
    p = row_info['parsed']
    if p['is_buggi']:
        return p['chae_mu_ja']  # 부기등기 자체에 대해서는 의미 없음
    base_sun_wi = p['sun_wi']
    buggi_prefix = base_sun_wi + '-'

    # 같은 본 순위번호의 개명 부기등기들 수집
    rename_buggies = []
    for row in parsed_rows:
        bp = row['parsed']
        if not bp['is_buggi']:
            continue
        if not bp['sun_wi'].startswith(buggi_prefix):
            continue
        if '개명' not in bp.get('deungki_inwon', ''):
            continue
        rename_buggies.append(row)

    if not rename_buggies:
        return p['chae_mu_ja']

    # 부기등기 순위번호의 두 번째 부분(예: '14-2' → 2)으로 정렬해 가장 늦은 것 선택
    def _buggi_order(row):
        try:
            return int(row['parsed']['sun_wi'].split('-')[1])
        except (IndexError, ValueError):
            return 0
    rename_buggies.sort(key=_buggi_order)
    last_rename = rename_buggies[-1]

    # 권리자 셀 첫 줄의 가장 오른쪽 어구를 새 채무자명으로
    gwon_text = last_rename['parsed'].get('gwon_lija_raw', '')
    first_line = gwon_text.split('\n')[0].strip()
    words = first_line.split()
    if words:
        return words[-1]
    return p['chae_mu_ja']


def find_matching_geun_jeo_setups(parsed_rows, target_chaemu, target_geunjeo):
    """채무자 + 근저당권자가 일치하는 '근저당권설정' 본 등기들 반환 (v3.0).

    채무자 비교 시 본 등기의 원래 채무자명 또는 'effective' 채무자명
    (개명 부기등기가 있으면 새 이름) 중 어느 하나라도 입력값과 일치하면
    매치로 본다.

    parsed_rows: parse_eulgu_row 결과 dicts (raw_row, page index, y range 등 포함)
    """
    matches = []
    for idx, row_info in enumerate(parsed_rows):
        p = row_info['parsed']
        if p['is_buggi']:
            continue
        if not p['is_geun_jeo_setup']:
            continue
        if not geunjeo_matches(target_geunjeo, p['geun_jeo']):
            continue
        # 원래 채무자명으로 매치 시도
        if chaemu_matches(target_chaemu, p['chae_mu_ja']):
            matches.append((idx, row_info))
            continue
        # effective 채무자명(개명 후)으로 재시도
        effective = get_effective_chaemu(row_info, parsed_rows)
        if effective != p['chae_mu_ja'] and chaemu_matches(target_chaemu, effective):
            matches.append((idx, row_info))
    return matches


def find_geunjeo_only_matches(parsed_rows, target_geunjeo):
    """근저당권자만 일치하는 '근저당권설정' 본 등기들 반환 (채무자 무시)

    채무자+근저당권자 모두 매치되는 것이 없을 때 fallback 으로 사용한다.
    """
    matches = []
    for idx, row_info in enumerate(parsed_rows):
        p = row_info['parsed']
        if p['is_buggi']:
            continue
        if not p['is_geun_jeo_setup']:
            continue
        if not geunjeo_matches(target_geunjeo, p['geun_jeo']):
            continue
        matches.append((idx, row_info))
    return matches


def determine_gongdong(matched_idx, parsed_rows):
    """공동담보 'O' 여부 판정 - 일치 근저당권이 1개일 때만 호출

    판정 규칙:
      1) 본 등기 본문에 '공동담보' 텍스트가 있으면 True.
      2) 본 등기에 딸린 부기등기(같은 본 순위번호의 'n-n' 행) 중 어느
         하나라도 '공동담보' 텍스트를 포함하면 True.
         - 등기목적 셀(예: '1번근저당권담보추가')과 권리자 셀(본문) 모두 검사.
         - 중간에 빈 순위번호 행(집합건물의 부동산표시 변경 등)이 끼어
           있어도 무시하고 계속 진행한다.
         - 다른 본 순위번호의 본 등기(예: '2')를 만나면 검사 종료.
    """
    p = parsed_rows[matched_idx]['parsed']
    if p['has_gongdong_keyword']:
        return True

    sun_wi = p['sun_wi']
    buggi_prefix = sun_wi + '-'  # 예: '1-'

    for j in range(matched_idx + 1, len(parsed_rows)):
        next_p = parsed_rows[j]['parsed']
        next_sun_wi = next_p['sun_wi']

        # 빈 순위번호 행(부동산표시 변경 등)은 건너뛴다
        if not next_sun_wi:
            continue

        # 같은 본 순위번호의 부기등기 → '공동담보' 검사
        if next_p['is_buggi'] and next_sun_wi.startswith(buggi_prefix):
            # 등기목적 셀과 본문(권리자 셀) 모두에서 검색
            if ('공동담보' in next_p['gwon_lija_raw']
                    or '공동담보' in next_p['deungki_mokjeok']):
                return True
            continue

        # 같은 본 순위번호의 또 다른 본 등기는 있을 수 없지만 방어적으로:
        if next_sun_wi == sun_wi and not next_p['is_buggi']:
            continue

        # 다른 본 순위번호로 넘어가면 종료
        break

    return False


def check_geun_jeo_strikethrough(matched_row_info, pdf_path, target_geunjeo):
    """일치 근저당권 1개일 때, 그 본 등기 행 안에서 근저당권자 이름이 삭선되었는지 검사"""
    pidx = matched_row_info['page_idx']
    y_top = matched_row_info['y_top']
    y_bot = matched_row_info['y_bot']
    if pidx is None or y_top is None or y_bot is None:
        return False

    with pdfplumber.open(pdf_path) as pdf:
        page = _filtered_page(pdf.pages[pidx])
        return is_text_struck_in_page(target_geunjeo, page,
                                       search_y_top=y_top,
                                       search_y_bottom=y_bot)


HOUSING_FINANCE_CORP_NAMES = ('한국주택금융공사',)


def is_transferred_to_housing_finance(matched_idx, parsed_rows, pdf_path):
    """근저당권자가 한국주택금융공사로 이전되었는지 판정.

    조건:
      1) 본 등기의 근저당권자 이름에 삭선이 있어야 한다.
         (이미 호출 측에서 확인하고 호출하므로 여기서 다시 확인하지 않는다.)
      2) 같은 본 순위번호의 부기등기를 시간 순으로 훑었을 때,
         최종(가장 마지막의 삭선 안 된) 근저당권자가 '한국주택금융공사'.

    여기서는 (2)만 판정한다. 부기등기에서 근저당권자가 새로 등장하는 행은
    보통 등기목적이 '근저당권이전' 같은 형태이며, 권리자 셀에는
    "근저당권자 ○○○ ..." 가 적혀 있다.

    구현은 다음과 같다:
      - 같은 본 순위번호 (N-N) 부기등기들 중 다음 조건을 모두 만족하는 행을 모은다:
          · 등기목적에 '근저당권이전' 키워드 포함 (v3.2 추가)
          · 권리자 셀에 '근저당권자' 키워드가 있고 그 뒤 이름이 파싱되어 있음
      - 그 중 근저당권자 이름이 삭선되지 않은 마지막 행을 찾는다.
      - 그 행의 근저당권자가 '한국주택금융공사'면 True.
      - 후보가 없으면 False.
    """
    base_sun_wi = parsed_rows[matched_idx]['parsed']['sun_wi']

    # 같은 본 순위번호의 부기등기 후보 수집
    transfer_candidates = []
    for j in range(matched_idx + 1, len(parsed_rows)):
        rj = parsed_rows[j]
        pj = rj['parsed']
        next_sun_wi = pj['sun_wi']
        # 빈 순위번호는 건너뛴다
        if not next_sun_wi:
            continue
        # 다른 본 등기(다른 본 순위번호 또는 같은 순위번호의 본 등기)를 만나면 종료
        if not pj['is_buggi']:
            break
        # 같은 본 순위번호의 부기등기만 (예: '7-1', '7-2')
        if not next_sun_wi.startswith(base_sun_wi + '-'):
            continue
        # v3.2: 등기목적이 '근저당권이전'인 부기등기만 후보로 인정.
        # (이전엔 권리자 셀에 근저당권자가 파싱된 모든 부기등기를 후보로
        #  봤으나, 다른 종류의 부기등기에서 우연히 권리자 셀에 근저당권자가
        #  표기되는 케이스를 배제하기 위해 등기목적 키워드 검증을 추가)
        if '근저당권이전' not in pj.get('deungki_mokjeok', ''):
            continue
        # 권리자 셀에 '근저당권자' 키워드가 있고 이름이 파싱되었는지
        if not pj.get('geun_jeo'):
            continue
        transfer_candidates.append(rj)

    if not transfer_candidates:
        return False

    # 시간 순서(부기등기 등장 순)대로 훑되, 마지막의 삭선되지 않은 행을 찾는다.
    # 부기등기는 PDF 상 위에서 아래로 시간 순으로 나타난다.
    final_geun_jeo = None
    with pdfplumber.open(pdf_path) as pdf:
        for cand in transfer_candidates:
            cand_geun_jeo = cand['parsed']['geun_jeo']
            pidx = cand['page_idx']
            y_top = cand['y_top']
            y_bot = cand['y_bot']
            if pidx is None or y_top is None or y_bot is None:
                # 위치 정보가 없으면 삭선 검사 불가 - 보수적으로 일단 유효로 본다
                final_geun_jeo = cand_geun_jeo
                continue
            page = _filtered_page(pdf.pages[pidx])
            struck = is_text_struck_in_page(cand_geun_jeo, page,
                                            search_y_top=y_top,
                                            search_y_bottom=y_bot)
            if not struck:
                final_geun_jeo = cand_geun_jeo
            # 삭선이면 final_geun_jeo는 그대로(이전 값 유지) - 더 뒤의 행을 봄

    if not final_geun_jeo:
        return False

    # 정규화 후 한국주택금융공사 매칭
    final_norm = normalize_name(final_geun_jeo)
    for target_name in HOUSING_FINANCE_CORP_NAMES:
        if normalize_name(target_name) in final_norm:
            return True
    return False


def is_chae_max_struck(row_info, pdf_path):
    """행 내의 채권최고액 금액 텍스트가 삭선되었는지 검사

    채권최고액 숫자(예: '651,600,000')가 행 안에 있고, 그 위에 수평선이 그어져 있으면 True.
    """
    pidx = row_info['page_idx']
    y_top = row_info['y_top']
    y_bot = row_info['y_bot']
    chae_max_num = row_info['parsed'].get('chae_max_num', '')
    if not chae_max_num or pidx is None or y_top is None or y_bot is None:
        return False

    # PDF 페이지에서 해당 금액을 가진 단어를 찾아 삭선 검사
    with pdfplumber.open(pdf_path) as pdf:
        page = _filtered_page(pdf.pages[pidx])
        words = page.extract_words()
        lines = page.lines
        ph = page.height

        # chae_max_num 으로부터 등기부 표기 형식 ('651,600,000')을 만든다
        n = int(chae_max_num)
        formatted = f"{n:,}"  # '651,600,000'

        for w in words:
            # 행 y 범위 안에 있는 단어만
            if w['top'] < y_top - 2 or w['bottom'] > y_bot + 2:
                continue
            # 단어 텍스트에 형식화된 금액이 들어 있는지
            if formatted in w['text']:
                if is_word_struck(w, lines, ph):
                    return True
    return False


def find_replacement_chae_max(matched_idx, parsed_rows, pdf_path):
    """본 등기 채권최고액이 삭선된 경우, n-n번근저당권변경 부기등기에서
    삭선되지 않은 (즉 가장 마지막) 채권최고액을 찾아 반환

    반환: (chae_max_disp, chae_max_num) 또는 None (못 찾음)
    """
    base_sun_wi = parsed_rows[matched_idx]['parsed']['sun_wi']
    candidates = []
    for j in range(matched_idx + 1, len(parsed_rows)):
        rj = parsed_rows[j]
        pj = rj['parsed']
        # 본 부동산의 다른 본 등기로 넘어가면 종료
        if not pj['is_buggi']:
            break
        # 같은 본 순위번호 (n-n) 인 부기등기만
        if not pj['sun_wi'].startswith(base_sun_wi + '-'):
            continue
        # '근저당권변경' 부기등기이고 채권최고액이 들어있는 것만
        if '근저당권변경' not in pj['deungki_mokjeok']:
            continue
        if not pj['chae_max_num']:
            continue
        candidates.append(rj)

    # 후보 중 채권최고액이 삭선되지 않은 행을 찾음 (보통 마지막 1개)
    for rj in candidates:
        if not is_chae_max_struck(rj, pdf_path):
            return rj['parsed']['chae_max_disp'], rj['parsed']['chae_max_num']

    # 모두 삭선이거나 못 찾음 (이 케이스는 명세상 발생 안 함)
    if candidates:
        # 마지막 후보를 fallback
        last = candidates[-1]
        return last['parsed']['chae_max_disp'], last['parsed']['chae_max_num']
    return None


def process_single_pdf(pdf_path, input_geunjeo, input_chaemu):
    """한 개의 PDF에 대해 매칭 결과 dict 리스트와 메타정보를 반환 (v2.6)

    반환:
      {
        'office': str,           ← 등기소명
        'property_address': str, ← 담보물주소 (두 번째 페이지 상단의 부동산 표시).
                                   매치 종류와 무관하게 항상 채워진다.
        'property_address_is_normalized': bool,
                                  ← A1/A2 매치 성공으로 정제 완료되었는지.
                                    False 면 호출자가 셀 글자색을 빨간색으로
                                    표시. 빈 주소는 True.
        'matches': [match_info, ...],
        'match_kind': 'full' | 'geunjeo_only' | 'none',
            'full'          : 채무자+근저당권자 매치
            'geunjeo_only'  : 근저당권자만 매치
            'none'          : 아예 매치 없음
        'no_match_label': str  # match_kind == 'none' 일 때만 사용 ('기말소/주소오류')
      }
    각 match_info는 다음 키를 갖는다:
      jeobsu_date, jeobsu_no,
      chae_max_disp           ← 채권최고액(최종). 본 등기 금액 또는 변경
                                부기등기에서 가져온 변경 후 금액.
      chae_max_original_disp  ← 최초설정액. 본 등기 채권최고액이 삭선되었을
                                때 그 본 등기에 적힌 원래 금액. 삭선 없으면 ''.
      chae_max_changed, name_struck, transferred_to_kr_housing,
      gongdong, sun_wi, parsed_idx, row_info,
      row_label  ← 이 행에 표시할 처리결과 라벨. 빈 문자열이면 표시 안 함.
    """
    eulgu_rows_raw = extract_eulgu_rows(pdf_path)
    parsed_rows = []
    for raw_row, pidx, y_top, y_bot in eulgu_rows_raw:
        parsed_rows.append({
            'raw': raw_row,
            'parsed': parse_eulgu_row(raw_row),
            'page_idx': pidx,
            'y_top': y_top,
            'y_bot': y_bot,
        })

    office = get_deungki_office(pdf_path)
    property_address, property_address_is_normalized = get_property_address(pdf_path)
    property_type = get_property_type(pdf_path)  # v3.0: 유형 컬럼

    # 1) 채무자 + 근저당권자 매칭 시도
    # v3.0: find_matching_geun_jeo_setups 내부에서 채무자 개명 (effective_chaemu)을
    # 자동으로 고려한다. 사전 매핑 단계 불필요.
    full_matches = find_matching_geun_jeo_setups(
        parsed_rows, input_chaemu, input_geunjeo)

    if full_matches:
        match_kind = 'full'
        matches_to_use = full_matches
    else:
        # 2) 근저당권자만 매칭 시도 (fallback)
        geunjeo_only_matches = find_geunjeo_only_matches(parsed_rows, input_geunjeo)
        if geunjeo_only_matches:
            match_kind = 'geunjeo_only'
            matches_to_use = geunjeo_only_matches
        else:
            # 3) 아예 매치 없음
            # v3.0: ③ 케이스에서도 등기소명/유형/담보물주소 모두 채운다
            # (PDF에서 객관적으로 뽑힌 정보이므로)
            return {
                'office': office,
                'property_type': property_type,
                'property_address': property_address,
                'property_address_is_normalized': property_address_is_normalized,
                'matches': [],
                'match_kind': 'none',
                'no_match_label': '기말소/주소오류',
            }

    # 매치들에 대해 공통 정보 채우기 (감액/기이전/공동담보 판정)
    match_infos = []
    for idx, row_info in matches_to_use:
        p = row_info['parsed']

        # 본 등기 채권최고액이 삭선되었는지 검사
        chae_max_changed = is_chae_max_struck(row_info, pdf_path)
        if chae_max_changed:
            # 채권최고액(최종) = 변경 부기등기의 최종 금액
            # 최초설정액 = 본 등기에 적힌 (삭선된) 원래 금액
            chae_max_disp = p['chae_max_disp']  # 일단 기본값
            replacement = find_replacement_chae_max(idx, parsed_rows, pdf_path)
            if replacement is not None:
                chae_max_disp = replacement[0]
            chae_max_original_disp = p['chae_max_disp']
        else:
            # 삭선 없음: 채권최고액은 본 등기 금액, 최초설정액은 공란
            chae_max_disp = p['chae_max_disp']
            chae_max_original_disp = ''

        # 매치별 근저당권자 이름 삭선 여부
        name_struck = check_geun_jeo_strikethrough(row_info, pdf_path, input_geunjeo)

        # 한국주택금융공사 이전 여부
        # (v1.10: 모든 매치 행에 대해 - match_kind 제한 없음 - 근저당권자가
        #  삭선일 때만 검사 의미)
        transferred = False
        if name_struck:
            transferred = is_transferred_to_housing_finance(idx, parsed_rows, pdf_path)

        # 매치별 공동담보 판정
        match_gongdong = determine_gongdong(idx, parsed_rows)

        match_infos.append({
            'jeobsu_date': p['jeobsu_date'],
            'jeobsu_no': p['jeobsu_no'],
            'chae_max_disp': chae_max_disp,
            'chae_max_original_disp': chae_max_original_disp,
            'chae_max_changed': chae_max_changed,
            'name_struck': name_struck,
            'transferred_to_kr_housing': transferred,
            'gongdong': match_gongdong,
            'sun_wi': p['sun_wi'],
            'parsed_idx': idx,
            'row_info': row_info,
            'row_label': '',  # 아래에서 채움
        })

    # row_label 결정 (v1.10 라벨 규칙)
    # 1) 1차 라벨: 매치 종류와 개수에 따라
    n = len(match_infos)
    if match_kind == 'full':
        if n == 1:
            match_infos[0]['row_label'] = '일치'
        else:
            match_infos[0]['row_label'] = '다수'
            for mi in match_infos[1:]:
                mi['row_label'] = ''  # 공란
    else:
        # match_kind == 'geunjeo_only'
        match_infos[0]['row_label'] = '개명/기말소/주소오류'
        for mi in match_infos[1:]:
            mi['row_label'] = ''

    # 2) 기이전 판정으로 1차 라벨 덮어쓰기 (모든 행 독립 적용)
    for mi in match_infos:
        if mi['transferred_to_kr_housing']:
            mi['row_label'] = '기이전'

    return {
        'office': office,
        'property_type': property_type,
        'property_address': property_address,
        'property_address_is_normalized': property_address_is_normalized,
        'matches': match_infos,
        'match_kind': match_kind,
        'no_match_label': '',
    }


# ===========================================================================
# 6. 전체 실행 (입력 엑셀 → 결과 엑셀)
# ===========================================================================

OUTPUT_COLUMNS = [
    'NO', '근저당권자', '채무자', '부동산고유번호',
    '유형', '처리결과', '공동담보',
    '접수일자', '접수번호', '채권최고액', '최초설정액',
    '등기소명', '담보물주소'
]


INPUT_COLUMNS = ['NO', '근저당권자', '채무자', '부동산고유번호']
RESULT_COLUMNS = ['유형', '처리결과', '공동담보',
                  '접수일자', '접수번호', '채권최고액', '최초설정액',
                  '등기소명', '담보물주소']


def _find_header_row(ws, required_cols):
    """입력 엑셀에서 헤더 행이 어디에 있는지 찾는다.

    헤더 셀에 required_cols 의 모든 이름이 들어 있는 첫 행을 반환.
    또한 컬럼명 → 컬럼 인덱스(1-based) 매핑도 반환.
    """
    max_scan_rows = min(ws.max_row, 20)
    for row_idx in range(1, max_scan_rows + 1):
        values = {}
        for cell in ws[row_idx]:
            if cell.value is None:
                continue
            key = str(cell.value).strip()
            if key:
                values[key] = cell.column  # 1-based
        if all(c in values for c in required_cols):
            return row_idx, values
    raise ValueError(
        f"입력 엑셀에서 헤더 행을 찾지 못했습니다. 다음 컬럼이 모두 있어야 합니다: {required_cols}"
    )


def _ensure_result_columns(ws, header_row, col_map):
    """결과 컬럼이 없으면 RESULT_COLUMNS 정의 순서대로 삽입한다.

    삽입 규칙:
      - 이미 존재하는 컬럼은 그 위치 그대로 사용.
      - 누락된 컬럼은 RESULT_COLUMNS 순서대로 처리하되, 가능한 한
        의도된 인접 컬럼 옆에 들어가도록 한다:
          · 정의 순서상 바로 앞에 있는 컬럼이 시트에 존재하면 그 우측에 삽입.
          · 없으면, 바로 뒤에 있는 컬럼이 존재하면 그 좌측에 삽입.
          · 둘 다 없으면 헤더의 마지막 사용 컬럼 다음에 추가.
      - 삽입은 openpyxl의 insert_cols 로 처리되어 우측 데이터가 자동 시프트됨.
      - 인덱스가 시프트되므로 col_map 도 함께 갱신.

    예: RESULT_COLUMNS 가 [..., '채권최고액', '최초설정액', '등기소명', ...] 이고
        시트에 '채권최고액'은 있고 '최초설정액'은 없다면, '최초설정액'을
        '채권최고액'의 우측 칸에 삽입한다.
    """
    from copy import copy

    # 스타일 참조용 (마지막 입력 컬럼 헤더 셀)
    style_src_col = col_map.get('부동산고유번호',
                                max(col_map.values()) if col_map else 1)

    # RESULT_COLUMNS 의 정의 순서대로 누락된 것을 처리
    for i, col_name in enumerate(RESULT_COLUMNS):
        if col_name in col_map:
            continue

        # 삽입 위치 결정
        insert_at = None  # 1-based, 이 위치에 새 컬럼이 들어감 (기존 것은 우측으로 시프트)

        # 1) 정의 순서상 바로 앞 컬럼이 시트에 있으면 그 우측에 삽입
        for prev_name in reversed(RESULT_COLUMNS[:i]):
            if prev_name in col_map:
                insert_at = col_map[prev_name] + 1
                break
        # INPUT_COLUMNS 도 앞쪽 후보로 활용 (예: 첫 결과 컬럼이 누락된 경우
        # 마지막 입력 컬럼의 우측에 삽입)
        if insert_at is None and i == 0:
            # 첫 결과 컬럼이 통째로 없을 때
            last_input_col = max(
                (col_map[c] for c in INPUT_COLUMNS if c in col_map),
                default=None,
            )
            if last_input_col is not None:
                insert_at = last_input_col + 1

        # 2) 그래도 못 정했으면, 정의 순서상 바로 뒤 컬럼이 있는지 보고 그 좌측에 삽입
        if insert_at is None:
            for next_name in RESULT_COLUMNS[i + 1:]:
                if next_name in col_map:
                    insert_at = col_map[next_name]  # 그 자리에 삽입 → 기존 것은 우측 시프트
                    break

        # 3) 그래도 없으면 마지막에 추가
        if insert_at is None:
            insert_at = (max(col_map.values()) if col_map else 0) + 1

        # 시트에 열 삽입 (insert_at 위치에 빈 열이 생기고 기존 것은 우측으로 1칸 시프트)
        # insert_at 가 현재 마지막 사용 컬럼 다음 자리(=시프트 불필요)인 경우에도
        # insert_cols 가 안전하게 동작한다 (빈 열 1개가 생길 뿐).
        last_used_now = max(col_map.values()) if col_map else 0
        if insert_at <= last_used_now:
            ws.insert_cols(insert_at)
            # col_map 의 모든 컬럼 인덱스 시프트 (insert_at 이상은 +1)
            for k in list(col_map.keys()):
                if col_map[k] >= insert_at:
                    col_map[k] += 1

        # 헤더 셀에 컬럼명 기입 + 스타일 복사
        cell = ws.cell(row=header_row, column=insert_at)
        cell.value = col_name
        style_src_cell = ws.cell(row=header_row, column=style_src_col)
        if style_src_cell.has_style:
            cell.font = copy(style_src_cell.font)
            cell.fill = copy(style_src_cell.fill)
            cell.border = copy(style_src_cell.border)
            cell.alignment = copy(style_src_cell.alignment)
            cell.number_format = style_src_cell.number_format
            cell.protection = copy(style_src_cell.protection)
        col_map[col_name] = insert_at


def _copy_row_style(ws, src_row, dst_row, max_col):
    """행 스타일 복사 (insert_rows 후 새 행에 위 행의 스타일을 적용)"""
    from copy import copy
    for col in range(1, max_col + 1):
        src_cell = ws.cell(row=src_row, column=col)
        dst_cell = ws.cell(row=dst_row, column=col)
        if src_cell.has_style:
            dst_cell.font = copy(src_cell.font)
            dst_cell.fill = copy(src_cell.fill)
            dst_cell.border = copy(src_cell.border)
            dst_cell.alignment = copy(src_cell.alignment)
            dst_cell.number_format = src_cell.number_format
            dst_cell.protection = copy(src_cell.protection)


# ===========================================================================
# v3.1: 결과 엑셀 양식 일괄 적용
# ===========================================================================

# 색깔 정의 (RGB)
_V31_HEADER_FILL = 'FF1F4E78'    # 헤더 채우기색 RGB(31,78,120) → #1F4E78
_V31_HEADER_FONT = 'FFFFFFFF'    # 헤더 글자색 흰색
_V31_FILL_MULTI = 'FFFFF2CC'     # 다수: RGB(255,242,204) → #FFF2CC
_V31_FILL_RENAME = 'FFE2EFDA'    # 개명/기말소/주소오류: RGB(226,239,218) → #E2EFDA
_V31_FILL_ERROR = 'FFFCE4D6'     # 기말소·기이전·PDF없음: RGB(252,228,214) → #FCE4D6

# 라벨별 카테고리 분류
_V31_LABELS_ERROR = {'기말소/주소오류', '기이전', 'PDF없음'}
_V31_LABELS_RENAME = {'개명/기말소/주소오류'}
_V31_LABELS_MULTI = {'다수'}


def _apply_v31_formatting(ws, header_row, col_map):
    """결과 엑셀에 v3.1 양식 일괄 적용.

    1) 모든 열 너비를 셀 내용 최대 길이에 맞춰 조정
    2) 채권최고액/최초설정액 값 셀 제외한 모든 셀 가운데 정렬
       (헤더는 모두 가운데)
    3) 헤더 행부터 마지막 데이터 행까지 NO~담보물주소 컬럼에 기본 실선 테두리
    4) 헤더 폰트: bold, 흰색, 채우기색 RGB(31,78,120)
    5)/(6)/(7) 처리결과 라벨에 따라 부동산 행 묶음에 채우기색 적용
       우선순위: (7) > (6) > (5)
    """
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, Color
    )

    # 데이터 영역 결정
    last_row = ws.max_row
    if last_row <= header_row:
        return  # 데이터 없음

    # 사용할 컬럼 인덱스 범위
    col_indices = sorted(col_map.values())
    if not col_indices:
        return
    first_col = col_indices[0]
    last_col = col_indices[-1]

    # === (3) 데이터 영역 모든 셀에 기본 실선 테두리 ===
    thin_side = Side(style='thin', color='FF000000')
    border = Border(left=thin_side, right=thin_side,
                    top=thin_side, bottom=thin_side)
    for r in range(header_row, last_row + 1):
        for c in range(first_col, last_col + 1):
            ws.cell(row=r, column=c).border = border

    # === (2) 정렬 ===
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    # 헤더는 모두 가운데
    for c in range(first_col, last_col + 1):
        ws.cell(row=header_row, column=c).alignment = center_align
    # 데이터: 채권최고액/최초설정액 컬럼 제외하고 가운데
    amount_cols = {col_map.get('채권최고액'), col_map.get('최초설정액')}
    amount_cols.discard(None)
    for r in range(header_row + 1, last_row + 1):
        for c in range(first_col, last_col + 1):
            if c in amount_cols:
                continue  # 금액 셀은 원래 우측 정렬 유지
            ws.cell(row=r, column=c).alignment = center_align

    # === (4) 헤더 스타일 ===
    header_font = Font(bold=True, color=_V31_HEADER_FONT)
    header_fill = PatternFill(start_color=_V31_HEADER_FILL,
                              end_color=_V31_HEADER_FILL,
                              fill_type='solid')
    for c in range(first_col, last_col + 1):
        cell = ws.cell(row=header_row, column=c)
        cell.font = header_font
        cell.fill = header_fill

    # === (5)/(6)/(7) 부동산 단위 채우기색 ===
    # 각 부동산의 행 묶음(첫 행 + 그 아래 추가 행들)을 식별해야 한다.
    # NO 컬럼에 값이 있는 행이 부동산 시작 행. 다음 NO가 있는 행 직전까지가
    # 한 부동산의 행 묶음.
    no_col = col_map.get('NO')
    label_col = col_map.get('처리결과')
    if no_col is not None and label_col is not None:
        # 모든 부동산 시작 행 수집
        start_rows = []
        for r in range(header_row + 1, last_row + 1):
            v = ws.cell(row=r, column=no_col).value
            if v is not None and str(v).strip() != '':
                start_rows.append(r)

        # 각 부동산 행 묶음에 대해 라벨 검사 + 색칠
        for i, sr in enumerate(start_rows):
            er = start_rows[i + 1] - 1 if i + 1 < len(start_rows) else last_row
            # 이 묶음의 모든 처리결과 라벨 수집
            labels = set()
            for r in range(sr, er + 1):
                v = ws.cell(row=r, column=label_col).value
                if v is not None:
                    labels.add(str(v).strip())

            # 우선순위 적용: (7) > (6) > (5)
            fill_color = None
            if labels & _V31_LABELS_ERROR:
                fill_color = _V31_FILL_ERROR
            elif labels & _V31_LABELS_RENAME:
                fill_color = _V31_FILL_RENAME
            elif labels & _V31_LABELS_MULTI:
                fill_color = _V31_FILL_MULTI

            if fill_color:
                fill = PatternFill(start_color=fill_color,
                                   end_color=fill_color,
                                   fill_type='solid')
                for r in range(sr, er + 1):
                    for c in range(first_col, last_col + 1):
                        # 헤더는 건너뜀 (헤더 색이 덮이지 않도록)
                        if r == header_row:
                            continue
                        ws.cell(row=r, column=c).fill = fill

    # === (1) 열 너비 자동 조정 ===
    # 각 컬럼의 모든 셀에서 표시 길이의 최대값 계산 후 +2 여유.
    # 한글 한 글자의 폭이 영문보다 넓다는 점을 감안해 한글 가중치 1.8 적용.
    for c in range(first_col, last_col + 1):
        max_len = 0
        for r in range(header_row, last_row + 1):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            # 표시 형식 적용된 모습 추정
            if isinstance(v, (int, float)):
                num_fmt = ws.cell(row=r, column=c).number_format
                if num_fmt and ',' in num_fmt:
                    s = f"{int(v):,}"
                else:
                    s = str(v)
            else:
                s = str(v)
            # 줄바꿈 분리하여 가장 긴 줄만 고려
            for line in s.split('\n'):
                w = _approx_text_width(line)
                if w > max_len:
                    max_len = w
        col_letter = ws.cell(row=header_row, column=c).column_letter
        # 최소 너비 6, 여유 2 더하기
        ws.column_dimensions[col_letter].width = max(max_len + 2, 6)


def _approx_text_width(text):
    """텍스트의 엑셀 열 너비 추정값.
    한글 1글자는 약 1.8 너비, 그 외는 1.0.
    """
    width = 0.0
    for ch in text:
        if '\uac00' <= ch <= '\ud7af':  # 한글
            width += 1.8
        elif ch in '一二三四五六七八九十':  # 한자 (대표)
            width += 1.8
        else:
            width += 1.0
    return width


def run(input_excel_path, pdf_dir, output_excel_path, log_callback=None):
    """입력 엑셀을 사본으로 만들고 그 위에 결과를 채워넣는 방식으로 처리

    - 입력 엑셀의 헤더와 NO 행은 그대로 유지
    - 매치 1개 → 해당 NO 행의 결과 컬럼만 채움
    - 매치 N개(>1) → NO 행 아래에 (N-1)개 행을 삽입하여 모든 매치를 출력
      (NO/근저당권자/채무자/부동산고유번호는 첫 행에만)
    - 행 삽입은 아래 NO부터 거꾸로 처리하여 인덱스를 보존
    """
    import shutil
    from openpyxl.styles import Alignment

    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    pdf_dir = Path(pdf_dir)
    input_excel_path = str(input_excel_path)
    output_excel_path = str(output_excel_path)

    # 1) 입력 엑셀 → 출력 엑셀로 복사 (서식/양식 그대로 유지)
    if os.path.abspath(input_excel_path) != os.path.abspath(output_excel_path):
        shutil.copyfile(input_excel_path, output_excel_path)

    # 2) 워크북 열기
    wb = load_workbook(output_excel_path)
    ws = wb.active

    # 3) 헤더 행 찾기 - 입력 컬럼만 필수
    header_row, col_map = _find_header_row(ws, INPUT_COLUMNS)
    # 결과 컬럼이 없으면 자동 추가
    missing = [c for c in RESULT_COLUMNS if c not in col_map]
    if missing:
        log(f"결과 컬럼 자동 추가: {missing}")
        _ensure_result_columns(ws, header_row, col_map)
    log(f"헤더 행: {header_row}행, 컬럼: {sorted(col_map.items(), key=lambda x: x[1])}")

    # 4) 데이터 행을 모두 수집 (NO에 값이 있고, 실제 입력이 있는 행만)
    data_rows = []  # [(row_index, no_disp, in_geunjeo, in_chaemu, gyu_no), ...]
    for r in range(header_row + 1, ws.max_row + 1):
        no_cell = ws.cell(row=r, column=col_map['NO']).value
        if no_cell is None:
            continue
        no_str = str(no_cell).strip()
        if not no_str:
            continue
        try:
            no_disp = str(int(float(no_str)))
        except (ValueError, TypeError):
            no_disp = no_str

        def _get(name):
            v = ws.cell(row=r, column=col_map[name]).value
            return '' if v is None else str(v).strip()

        in_geunjeo = _get('근저당권자')
        in_chaemu = _get('채무자')
        gyu_no = _get('부동산고유번호')

        data_rows.append((r, no_disp, in_geunjeo, in_chaemu, gyu_no))

    log(f"처리 대상 행: {len(data_rows)}개")

    # 이름 변경 대상 PDF: NO별로 (no, gyu_no, chaemu, pdf_path)
    # - 부동산고유번호 비어있거나 PDF 없으면 대상 아님
    # - 같은 부동산고유번호가 여러 NO에서 참조되면 첫 NO 기준
    pdfs_to_rename = {}  # gyu_no → (no_disp, chaemu, pdf_path)

    # === v3.0 헬퍼 함수들 ===
    def _amount_to_int(amount_text):
        """채권최고액/최초설정액 문자열을 정수로 변환.
        '175,000,000' → 175000000, '' → None (빈 셀)
        """
        if not amount_text:
            return None
        # 숫자만 추출
        digits = re.sub(r'[^\d]', '', str(amount_text))
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def _append_property_label(address, has_gongdong, property_type):
        """공동담보 'O'인 경우 주소 끝에 '[건물][토지]' 추가 (v3.0).
        공동담보가 아니면 주소 그대로 반환.
        property_type 이 무엇이든 정확히 문자열 '[건물][토지]' 를 붙인다 (명세).
        """
        if not has_gongdong:
            return address
        if not address:
            return '[건물][토지]'
        return address + ' [건물][토지]'

    # 5) 각 행의 처리 결과를 미리 계산 (행 삽입은 나중에)
    results_by_row = {}  # row_index → result dict
    for r, no_disp, in_geunjeo, in_chaemu, gyu_no in data_rows:
        if not gyu_no or gyu_no.lower() == 'nan':
            log(f"[NO {no_disp}] 부동산고유번호 비어있음")
            results_by_row[r] = {'kind': 'simple', 'fills': {
                '유형': '',
                '접수일자': '', '접수번호': '', '채권최고액': None, '최초설정액': None,
                '등기소명': '', '공동담보': '', '처리결과': '입력누락',
                '담보물주소': '',
            }}
            continue

        pdf_path = pdf_dir / f"{gyu_no}.pdf"
        if not pdf_path.exists():
            log(f"[NO {no_disp}] PDF 없음: {pdf_path.name}")
            results_by_row[r] = {'kind': 'simple', 'fills': {
                '유형': '',
                '접수일자': '', '접수번호': '', '채권최고액': None, '최초설정액': None,
                '등기소명': '', '공동담보': '', '처리결과': 'PDF없음',
                '담보물주소': '',
            }}
            continue

        # PDF가 존재하면 이름 변경 대상으로 등록 (첫 NO 기준)
        if gyu_no not in pdfs_to_rename:
            pdfs_to_rename[gyu_no] = (no_disp, in_chaemu, pdf_path)

        try:
            result = process_single_pdf(str(pdf_path), in_geunjeo, in_chaemu)
        except Exception as exc:
            log(f"[NO {no_disp}] 파싱 오류: {exc}")
            traceback.print_exc()
            results_by_row[r] = {'kind': 'simple', 'fills': {
                '유형': '',
                '접수일자': '', '접수번호': '', '채권최고액': None, '최초설정액': None,
                '등기소명': '', '공동담보': '', '처리결과': f'오류: {exc}',
                '담보물주소': '',
            }}
            continue

        property_type = result.get('property_type', '')
        property_address = result.get('property_address', '')

        # match_kind == 'none': 매치 자체가 없음
        # v3.0: 등기소명, 유형, 담보물주소는 PDF에서 객관적으로 뽑힌 정보이므로 모두 채움
        if result['match_kind'] == 'none':
            results_by_row[r] = {
                'kind': 'simple',
                'fills': {
                    '유형': property_type,
                    '접수일자': '', '접수번호': '',
                    '채권최고액': None, '최초설정액': None,
                    '등기소명': result['office'],
                    '공동담보': '',
                    '처리결과': result['no_match_label'],
                    '담보물주소': property_address,  # 공동담보 'O' 아니므로 라벨 안 붙음
                },
                'address_red': not result.get('property_address_is_normalized', True),
            }
            log(f"[NO {no_disp}] {result['no_match_label']}")
            continue

        matches = result['matches']

        if len(matches) == 1:
            m = matches[0]
            has_gongdong = m['gongdong']
            address_with_label = _append_property_label(
                property_address, has_gongdong, property_type)
            results_by_row[r] = {
                'kind': 'simple',
                'fills': {
                    '유형': property_type,
                    '접수일자': m['jeobsu_date'],
                    '접수번호': m['jeobsu_no'],
                    '채권최고액': _amount_to_int(m['chae_max_disp']),
                    '최초설정액': _amount_to_int(m['chae_max_original_disp']),
                    '등기소명': result['office'],
                    '공동담보': 'O' if has_gongdong else '',
                    '처리결과': m['row_label'],
                    '담보물주소': address_with_label,
                },
                'address_red': not result.get('property_address_is_normalized', True),
            }
        else:
            # 여러 개 매치: 첫 행은 기존 행에 채우고, 추가 행들은 삽입 필요
            # 담보물주소/등기소명/유형은 첫 행에만 (부동산 단위 정보)
            first_has_gongdong = matches[0]['gongdong']
            first_address_with_label = _append_property_label(
                property_address, first_has_gongdong, property_type)
            first_fills = {
                '유형': property_type,
                '접수일자': matches[0]['jeobsu_date'],
                '접수번호': matches[0]['jeobsu_no'],
                '채권최고액': _amount_to_int(matches[0]['chae_max_disp']),
                '최초설정액': _amount_to_int(matches[0]['chae_max_original_disp']),
                '등기소명': result['office'],
                '공동담보': 'O' if first_has_gongdong else '',
                '처리결과': matches[0]['row_label'],
                '담보물주소': first_address_with_label,
            }
            extra_rows = []
            for m in matches[1:]:
                extra_rows.append({
                    '접수일자': m['jeobsu_date'],
                    '접수번호': m['jeobsu_no'],
                    '채권최고액': _amount_to_int(m['chae_max_disp']),
                    '최초설정액': _amount_to_int(m['chae_max_original_disp']),
                    '공동담보': 'O' if m['gongdong'] else '',
                    '처리결과': m['row_label'],
                    '담보물주소': '',  # 부동산 단위 정보이므로 첫 행에만
                })
            results_by_row[r] = {
                'kind': 'multi',
                'first_fills': first_fills,
                'extra_rows': extra_rows,
                'address_red': not result.get('property_address_is_normalized', True),
            }

        # 로그 메시지
        first_label = matches[0]['row_label'] or '(공란)'
        any_gongdong = any(m['gongdong'] for m in matches)
        log(f"[NO {no_disp}] {result['match_kind']} {first_label} "
            f"(매치 {len(matches)}개{', 공동담보 O' if any_gongdong else ''})")

    # 6) 결과 셀 채우기 - 단순 케이스부터 (행 삽입 없음)
    # v3.0: 금액 컬럼(채권최고액/최초설정액)은 셀 값을 정수로, 표시형식은
    # 천단위 구분기호('#,##0')로 적용한다.
    AMOUNT_COLS = ('채권최고액', '최초설정액')

    def _set_cell(row, col_name, val):
        cell = ws.cell(row=row, column=col_map[col_name])
        cell.value = val
        if col_name in AMOUNT_COLS and val is not None and val != '':
            # 숫자 셀 표시형식 적용 (v3.0)
            cell.number_format = '#,##0'

    def _apply_red_font_to_address(row):
        """담보물주소 셀의 글자색을 빨간색(FF0000)으로 변경.
        기존 폰트 속성(폰트명, 크기, 굵기 등)은 유지하고 color만 바꾼다.
        """
        from openpyxl.styles import Font
        from copy import copy as _copy
        cell = ws.cell(row=row, column=col_map['담보물주소'])
        old_font = cell.font
        new_font = Font(
            name=old_font.name,
            size=old_font.size,
            bold=old_font.bold,
            italic=old_font.italic,
            vertAlign=old_font.vertAlign,
            underline=old_font.underline,
            strike=old_font.strike,
            color='FF0000',
        )
        cell.font = new_font

    for r, _, _, _, _ in data_rows:
        res = results_by_row[r]
        if res['kind'] == 'simple':
            for col_name, val in res['fills'].items():
                _set_cell(r, col_name, val)
            if res.get('address_red'):
                _apply_red_font_to_address(r)

    # 7) 멀티 매치 - 아래 NO부터 거꾸로 처리하여 인덱스 보존
    multi_targets = [(r, results_by_row[r]) for r, _, _, _, _ in data_rows
                     if results_by_row[r]['kind'] == 'multi']
    multi_targets.sort(key=lambda x: x[0], reverse=True)  # 큰 행부터

    max_col = max(col_map.values())

    for r, res in multi_targets:
        # 기존 행에 첫 매치 결과 채우기
        for col_name, val in res['first_fills'].items():
            _set_cell(r, col_name, val)

        # 담보물주소 빨간색 처리 (첫 행에만 - 다중 매치의 부동산은 1개이므로)
        if res.get('address_red'):
            _apply_red_font_to_address(r)

        n_extra = len(res['extra_rows'])
        if n_extra == 0:
            continue
        # 행 삽입: r 다음 위치에 n_extra개 행 삽입
        ws.insert_rows(r + 1, amount=n_extra)
        # 새 행에 스타일 복사 (위 행 기준)
        for off in range(n_extra):
            new_r = r + 1 + off
            _copy_row_style(ws, r, new_r, max_col)
        # 새 행에 추가 매치 데이터 채우기 (NO 등은 비움)
        for off, extra in enumerate(res['extra_rows']):
            new_r = r + 1 + off
            _set_cell(new_r, '접수일자', extra['접수일자'])
            _set_cell(new_r, '접수번호', extra['접수번호'])
            _set_cell(new_r, '채권최고액', extra['채권최고액'])
            _set_cell(new_r, '최초설정액', extra.get('최초설정액', None))
            _set_cell(new_r, '공동담보', extra.get('공동담보', ''))
            _set_cell(new_r, '처리결과', extra.get('처리결과', ''))
            _set_cell(new_r, '담보물주소', extra.get('담보물주소', ''))
            # NO/근저당권자/채무자/부동산고유번호/등기소명/유형은 비움
            # (부동산 단위 정보이므로 첫 행에만 표시)
            for col_name in ['NO', '근저당권자', '채무자', '부동산고유번호',
                             '등기소명', '유형']:
                ws.cell(row=new_r, column=col_map[col_name]).value = None

    # 8) v3.1: 결과 엑셀 양식 일괄 적용
    _apply_v31_formatting(ws, header_row, col_map)

    # 9) 저장
    wb.save(output_excel_path)
    log(f"저장 완료: {output_excel_path}")

    # 10) PDF 파일명 변경 (작업번호_고유번호_채무자(유형).pdf)
    if pdfs_to_rename:
        log(f"PDF 파일명 변경 시작 ({len(pdfs_to_rename)}개)")
        for gyu_no, (no_disp, chaemu, pdf_path) in pdfs_to_rename.items():
            rename_pdf_after_processing(pdf_path, no_disp, gyu_no, chaemu, log_callback=log)
        log("PDF 파일명 변경 완료")


# ===========================================================================
# 7. GUI (tkinter)
# ===========================================================================

def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    root = tk.Tk()
    root.title('등기부등본 근저당권 정보 파싱')
    root.geometry('760x520')

    # 입력 변수
    var_input_xlsx = tk.StringVar()
    var_pdf_dir = tk.StringVar()
    var_output_xlsx = tk.StringVar()

    frm = tk.Frame(root, padx=12, pady=12)
    frm.pack(fill='both', expand=True)

    def browse_input():
        path = filedialog.askopenfilename(
            title='입력 엑셀 파일 선택',
            filetypes=[('Excel', '*.xlsx *.xls')])
        if path:
            var_input_xlsx.set(path)
            # 출력 경로 자동 설정
            if not var_output_xlsx.get():
                p = Path(path)
                var_output_xlsx.set(str(p.parent / f"{p.stem}_결과.xlsx"))

    def browse_pdf():
        path = filedialog.askdirectory(title='PDF 폴더 선택')
        if path:
            var_pdf_dir.set(path)

    def browse_output():
        path = filedialog.asksaveasfilename(
            title='결과 엑셀 저장 위치',
            defaultextension='.xlsx',
            filetypes=[('Excel', '*.xlsx')])
        if path:
            var_output_xlsx.set(path)

    # 행 1: 입력 엑셀
    tk.Label(frm, text='입력 엑셀:', width=10, anchor='w').grid(row=0, column=0, sticky='w', pady=4)
    tk.Entry(frm, textvariable=var_input_xlsx, width=70).grid(row=0, column=1, padx=4)
    tk.Button(frm, text='찾아보기', command=browse_input, width=10).grid(row=0, column=2, padx=4)

    # 행 2: PDF 폴더
    tk.Label(frm, text='PDF 폴더:', width=10, anchor='w').grid(row=1, column=0, sticky='w', pady=4)
    tk.Entry(frm, textvariable=var_pdf_dir, width=70).grid(row=1, column=1, padx=4)
    tk.Button(frm, text='찾아보기', command=browse_pdf, width=10).grid(row=1, column=2, padx=4)

    # 행 3: 출력 엑셀
    tk.Label(frm, text='결과 엑셀:', width=10, anchor='w').grid(row=2, column=0, sticky='w', pady=4)
    tk.Entry(frm, textvariable=var_output_xlsx, width=70).grid(row=2, column=1, padx=4)
    tk.Button(frm, text='찾아보기', command=browse_output, width=10).grid(row=2, column=2, padx=4)

    # 로그
    tk.Label(frm, text='실행 로그:', anchor='w').grid(row=4, column=0, columnspan=3, sticky='w', pady=(12, 4))
    log_text = scrolledtext.ScrolledText(frm, height=18, width=92, font=('Consolas', 9))
    log_text.grid(row=5, column=0, columnspan=3, sticky='nsew', pady=4)
    frm.grid_rowconfigure(5, weight=1)
    frm.grid_columnconfigure(1, weight=1)

    def append_log(msg):
        log_text.insert('end', msg + '\n')
        log_text.see('end')
        log_text.update()

    def on_run():
        ix = var_input_xlsx.get().strip()
        pd_dir = var_pdf_dir.get().strip()
        ox = var_output_xlsx.get().strip()
        if not (ix and pd_dir and ox):
            messagebox.showwarning('경고', '입력 엑셀, PDF 폴더, 결과 엑셀 경로를 모두 지정하세요.')
            return
        if not Path(ix).exists():
            messagebox.showerror('오류', f'입력 엑셀이 존재하지 않습니다:\n{ix}')
            return
        if not Path(pd_dir).is_dir():
            messagebox.showerror('오류', f'PDF 폴더가 존재하지 않습니다:\n{pd_dir}')
            return

        log_text.delete('1.0', 'end')
        append_log('===== 처리 시작 =====')
        try:
            run(ix, pd_dir, ox, log_callback=append_log)
            append_log('===== 처리 완료 =====')
            messagebox.showinfo('완료', f'처리가 완료되었습니다.\n저장 위치: {ox}')
        except Exception as exc:
            append_log(f'오류 발생: {exc}')
            traceback.print_exc()
            messagebox.showerror('오류', str(exc))

    tk.Button(frm, text='실 행', command=on_run, width=14, height=2,
              bg='#2563eb', fg='white', font=('맑은 고딕', 11, 'bold')) \
        .grid(row=3, column=0, columnspan=3, pady=8)

    root.mainloop()


# ===========================================================================
# 8. 진입점
# ===========================================================================

def _script_dir():
    """스크립트(또는 frozen exe)가 있는 폴더"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # __file__ 이 정의되어 있을 때만 사용 가능
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def discover_paths(base_dir=None):
    """폴더 안에서 입력 엑셀과 PDF 폴더를 자동으로 찾는다.

    탐색 규칙:
      - 입력 엑셀: base_dir 안의 .xlsx 중 임시파일(~$로 시작) 및 결과파일
                   (*_결과.xlsx, *_result.xlsx 등) 제외. 1개여야 한다.
      - PDF 폴더: 'PDF' / 'pdfs' / 'pdf' / '등기부등본' 하위폴더 중 .pdf가
                   있는 것을 우선. 없으면 base_dir 자체에 .pdf가 있으면 그것.
      - 결과 엑셀: <입력파일 stem>_결과.xlsx (같은 폴더에 저장)

    반환: (input_xlsx_path, pdf_dir_path, output_xlsx_path)
    탐색 실패 시 ValueError 발생.
    """
    base = Path(base_dir) if base_dir else _script_dir()

    # 1) xlsx 후보 수집
    candidates = []
    for p in base.glob('*.xlsx'):
        name = p.name
        if name.startswith('~$'):
            continue  # 엑셀 임시파일
        stem = p.stem
        # 결과파일 패턴 제외
        if stem.endswith('_결과') or stem.endswith('_result') \
                or stem.endswith('_output') or stem.endswith('_out'):
            continue
        candidates.append(p)

    if len(candidates) == 0:
        raise ValueError(
            f"입력 엑셀(.xlsx)을 찾을 수 없습니다.\n"
            f"폴더: {base}\n"
            f"이 폴더에 입력 엑셀 파일을 두거나, GUI로 실행하세요(--gui)."
        )
    if len(candidates) > 1:
        names = ', '.join(c.name for c in candidates)
        raise ValueError(
            f"폴더에 xlsx 파일이 여러 개 있습니다: {names}\n"
            f"폴더: {base}\n"
            f"하나만 남기거나, GUI로 실행하세요(--gui)."
        )
    input_xlsx = candidates[0]

    # 2) PDF 폴더 탐색
    pdf_dir = None
    for sub_name in ('PDF', 'pdfs', 'pdf', '등기부등본', '등기부'):
        sub = base / sub_name
        if sub.is_dir() and any(sub.glob('*.pdf')):
            pdf_dir = sub
            break
    if pdf_dir is None:
        # 기본 폴더에 PDF가 있으면 그것 사용
        if any(base.glob('*.pdf')):
            pdf_dir = base
        else:
            raise ValueError(
                f"PDF 파일이 들어 있는 폴더를 찾을 수 없습니다.\n"
                f"기본 폴더: {base}\n"
                f"하위에 'PDF' 폴더를 만들고 PDF를 넣거나, GUI로 실행하세요(--gui)."
            )

    # 3) 결과 엑셀 경로
    output_xlsx = input_xlsx.with_name(f"{input_xlsx.stem}_결과.xlsx")

    return input_xlsx, pdf_dir, output_xlsx


def run_auto(base_dir=None):
    """자동 폴더 모드 실행"""
    input_xlsx, pdf_dir, output_xlsx = discover_paths(base_dir)
    print("=" * 60)
    print("[자동 폴더 모드]")
    print(f"  입력 엑셀: {input_xlsx}")
    print(f"  PDF 폴더 : {pdf_dir}")
    print(f"  결과 엑셀: {output_xlsx}")
    print("=" * 60)
    run(str(input_xlsx), str(pdf_dir), str(output_xlsx))


def _print_usage():
    print(
        "사용법:\n"
        "  python 등기부파싱.py                 # 자동 폴더 모드 (기본)\n"
        "  python 등기부파싱.py --gui           # GUI 모드\n"
        "  python 등기부파싱.py 입력.xlsx PDF폴더 결과.xlsx   # CLI 모드\n"
    )


def main():
    args = sys.argv[1:]

    # 도움말
    if args and args[0] in ('-h', '--help', '/?'):
        _print_usage()
        return

    # GUI 모드 명시
    if args and args[0] in ('--gui', '-g'):
        launch_gui()
        return

    # CLI 모드 (3개 인자)
    if len(args) >= 3:
        run(args[0], args[1], args[2])
        return

    # 인자 없음 → 자동 폴더 모드
    if len(args) == 0:
        try:
            run_auto()
        except ValueError as exc:
            # 자동 모드 실패 시: 콘솔로 실행한 경우엔 메시지만 출력하고
            # 더블클릭 등으로 실행한 경우엔 GUI를 띄워준다.
            print(f"자동 모드 실패: {exc}\n")
            print("GUI로 전환합니다...\n")
            try:
                launch_gui()
            except Exception:
                _print_usage()
                raise
        except Exception as exc:
            print(f"오류: {exc}")
            traceback.print_exc()
        return

    # 알 수 없는 사용 패턴
    _print_usage()


if __name__ == '__main__':
    main()
