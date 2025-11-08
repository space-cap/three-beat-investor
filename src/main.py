import os
from dotenv import load_dotenv
from kis_client import KisClient
import sys

def run_screener():
    """
    '삼박자 투자법' 1차 스크리너를 실행합니다.
    .env 파일에서 KIS API 설정을 로드하여 조건 검색을 수행합니다.
    """
    try:
        # 1. 환경 변수 로드
        load_dotenv()
        
        APP_KEY = os.environ.get("KIS_APP_KEY")
        APP_SECRET = os.environ.get("KIS_APP_SECRET")
        ACCOUNT_NUMBER = os.environ.get("KIS_ACCOUNT_NUMBER") # 계좌번호 8자리
        HTS_USER_ID = os.environ.get("KIS_HTS_USER_ID")       # HTS ID
        CONDITION_KEY = os.environ.get("KIS_CONDITION_KEY")    # HTS/MTS에서 발급받은 조건검색키
        IS_PROD_STR = os.environ.get("KIS_IS_PROD", "False") # 실서버 여부 (기본: 모의투자)
        
        IS_PROD = IS_PROD_STR.lower() in ('true', '1', 't')

        # 필수 환경 변수 체크
        if not all([APP_KEY, APP_SECRET, ACCOUNT_NUMBER, HTS_USER_ID, CONDITION_KEY]):
            print("오류: .env 파일에 필수 환경 변수가 설정되지 않았습니다.")
            print("필수 변수: KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NUMBER, KIS_HTS_USER_ID, KIS_CONDITION_KEY")
            sys.exit(1)

        print("--- '삼박자 투자법' 종목 발굴기 (가치/가격 필터) 시작 ---")

        # 2. KisClient 초기화
        client = KisClient(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            account_number=ACCOUNT_NUMBER,
            hts_user_id=HTS_USER_ID,
            is_prod=IS_PROD
        )
        
        # 3. 조건 검색 API 호출
        print(f"\nHTS/MTS 조건식 [{CONDITION_KEY}]을(를) 기준으로 스크리닝을 시작합니다...")
        stock_codes = client.fetch_conditional_search(condition_key=CONDITION_KEY)
        
        # 4. 결과 출력
        if stock_codes:
            print(f"\n[스크리닝 완료] 총 {len(stock_codes)}개의 종목이 발견되었습니다.")
            print("종목 코드 리스트:")
            print(stock_codes)
            print("\n-> 2단계: '정보(Info)' 분석(수동 또는 LLM)을 진행하세요.")
        else:
            print("\n[스크리닝 완료] 조건에 맞는 종목이 없습니다.")
            
        print("--- 프로그램 종료 ---")

    except Exception as e:
        print(f"프로그램 실행 중 치명적인 오류가 발생했습니다: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_screener()
    