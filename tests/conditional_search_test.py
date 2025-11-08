import os
from dotenv import load_dotenv
from kis_client import KisClient


def run_conditional_search_test():
    """
    .env 파일의 정보를 사용하여 실제 KIS API 조건 검색을 테스트합니다.
    """
    # .env 파일에서 환경 변수 로드
    load_dotenv()

    # 환경 변수에서 설정값 읽기
    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    ACCOUNT_NUMBER = os.getenv("KIS_ACCOUNT_NUMBER")
    HTS_USER_ID = os.getenv("KIS_HTS_USER_ID")
    IS_PROD = os.getenv("KIS_IS_PROD", "false").lower() == "true"
    
    # 필수 환경 변수 확인
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NUMBER, HTS_USER_ID]):
        print("오류: .env 파일에 다음 필수 환경 변수를 모두 설정해주세요.")
        print("KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NUMBER, KIS_HTS_USER_ID")
        return

    print("환경 변수를 성공적으로 로드했습니다.")
    print(f"실서버 모드: {IS_PROD}")

    try:
        # KisClient 초기화
        client = KisClient(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            account_number=ACCOUNT_NUMBER,
            hts_user_id=HTS_USER_ID,
            is_prod=IS_PROD
        )

        # seq 값
        seq = "0"
        
        print(f"\n조건 검색 테스트를 시작합니다 (seq: {seq})...")
        
        # 조건 검색 API 호출
        stocks = client.fetch_conditional_search(seq=seq)

        # 결과 출력
        if stocks:
            print("\n[성공] 조건 검색 결과:")
            for i, stock_code in enumerate(stocks):
                print(f"  {i+1}. {stock_code}")
        else:
            print("\n[정보] 조건에 해당하는 종목을 찾지 못했거나 API 응답이 비어있습니다.")

    except Exception as e:
        print(f"\n[오류] 테스트 실행 중 예외가 발생했습니다: {e}")

if __name__ == "__main__":
    run_conditional_search_test()
