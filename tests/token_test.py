import os
from dotenv import load_dotenv
from kis_client import KisClient


def run_token_test():
    """
    .env 파일의 정보를 사용하여 실제 KIS API 토큰 발급을 테스트합니다.
    """
    # .env 파일에서 환경 변수 로드
    load_dotenv()

    # 환경 변수에서 설정값 읽기
    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    IS_PROD = os.getenv("KIS_IS_PROD", "false").lower() == "true"
    
    # 필수 환경 변수 확인
    if not all([APP_KEY, APP_SECRET]):
        print("오류: .env 파일에 다음 필수 환경 변수를 모두 설정해주세요.")
        print("KIS_APP_KEY, KIS_APP_SECRET")
        return

    print("환경 변수를 성공적으로 로드했습니다.")
    print(f"실서버 모드: {IS_PROD}")

    try:
        # KisClient 초기화 (account_number와 hts_user_id는 토큰 발급에 필요 없으므로 임의의 값 전달)
        client = KisClient(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            account_number="12345678", 
            hts_user_id="testuser",
            is_prod=IS_PROD
        )

        print("\n토큰 발급 테스트를 시작합니다...")
        
        # 토큰 발급 함수 직접 호출
        client._get_token()

        # 결과 확인
        if client.access_token:
            print("\n[성공] 토큰이 성공적으로 발급되었습니다.")
            print(f"  - Access Token (first 10 chars): {client.access_token[:10]}...")
            print(f"  - Token Expiry (UTC): {client.token_expiry}")
        else:
            print("\n[실패] 토큰 발급에 실패했습니다.")

    except Exception as e:
        print(f"\n[오류] 테스트 실행 중 예외가 발생했습니다: {e}")


if __name__ == "__main__":
    run_token_test()
