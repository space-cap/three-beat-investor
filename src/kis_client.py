import requests
import json
import os
from datetime import datetime, timedelta, UTC
import time


class KisClient:
    """
    한국투자증권(KIS) API와 직접 통신(HTTP)하는 클라이언트.
    requests 라이브러리만을 사용하여 구현됨.
    """
    
    def __init__(self, app_key: str, app_secret: str, account_number: str, hts_user_id: str, is_prod: bool = False):
        """
        KisClient를 초기화합니다.

        Args:
            app_key (str): KIS API 앱 키.
            app_secret (str): KIS API 앱 시크릿.
            account_number (str): 계좌번호 (앞 8자리).
            hts_user_id (str): HTS 사용자 ID (조건 검색 시 필요).
            is_prod (bool, optional): 실서버(True) / 모의투자(False) 여부. 기본값은 False.
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_number = account_number
        self.hts_user_id = hts_user_id
        self.is_prod = is_prod
        self.token_file_path = ".token"
        
        # 실서버/모의투자 환경에 따른 URL 설정
        if is_prod:
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            
        self.access_token = None
        self.token_expiry = None
        
        print(f"[{'실서버' if is_prod else '모의투자'}] 환경으로 클라이언트를 초기화합니다. Base URL: {self.base_url}")
        self._load_token_from_file()

    def _load_token_from_file(self):
        """
        파일에 저장된 액세스 토큰을 불러옵니다.
        토큰이 유효하면 self.access_token과 self.token_expiry를 설정합니다.
        """
        if not os.path.exists(self.token_file_path):
            print("저장된 토큰 파일이 없습니다.")
            return

        try:
            with open(self.token_file_path, 'r') as f:
                token_data = json.load(f)
            
            expiry_str = token_data.get('token_expiry')
            if not expiry_str:
                print("토큰 파일에 만료 정보가 없습니다.")
                return

            token_expiry = datetime.fromisoformat(expiry_str)

            if datetime.now(UTC) < token_expiry:
                self.access_token = token_data.get('access_token')
                self.token_expiry = token_expiry
                print(f"파일에서 유효한 토큰을 불러왔습니다. 만료 시각(UTC): {self.token_expiry}")
            else:
                print("파일의 토큰이 만료되었습니다.")

        except (json.JSONDecodeError, IOError) as e:
            print(f"오류: 토큰 파일을 읽는 중 문제가 발생했습니다 - {e}")

    def _save_token_to_file(self):
        """
        현재 액세스 토큰과 만료 시간을 파일에 저장합니다.
        """
        if self.access_token and self.token_expiry:
            try:
                with open(self.token_file_path, 'w') as f:
                    token_data = {
                        'access_token': self.access_token,
                        'token_expiry': self.token_expiry.isoformat()
                    }
                    json.dump(token_data, f)
                print(f"토큰을 '{self.token_file_path}' 파일에 저장했습니다.")
            except IOError as e:
                print(f"오류: 토큰 파일 저장 실패 - {e}")

    def _get_token(self):
        """
        KIS API 인증 서버로부터 액세스 토큰을 발급받고 파일에 저장합니다. (Private 메서드)
        """
        print("액세스 토큰 발급을 시도합니다...")
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
            
            data = response.json()
            
            self.access_token = data['access_token']
            # 토큰 만료 시간 계산 (API 응답의 expires_in은 초 단위)
            # 여유 시간(60초)을 두어 만료 직전 갱신 방지
            expires_in = int(data['expires_in']) - 60 
            self.token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
            
            print(f"액세스 토큰 발급 성공. 만료 시각(UTC): {self.token_expiry}")
            self._save_token_to_file()

        except requests.exceptions.RequestException as e:
            print(f"오류: 토큰 발급 실패 - {e}")
            self.access_token = None
            self.token_expiry = None
            raise

    def _check_token(self):
        """
        현재 토큰이 유효한지 확인하고, 만료되었거나 없는 경우 갱신합니다. (Private 메서드)
        """
        if self.access_token is None or self.token_expiry is None or datetime.now(UTC) >= self.token_expiry:
            print("토큰이 없거나 만료되었습니다. 토큰을 갱신합니다.")
            self._get_token()
        else:
            print("기존 토큰이 유효합니다.")

    def _get_headers(self, tr_id: str) -> dict:
        """
        API 요청에 필요한 공통 헤더를 생성합니다. (Private 메서드)

        Args:
            tr_id (str): API 거래 ID (e.g., "FHPST01710000")

        Returns:
            dict: HTTP 요청 헤더
        """
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P", # 개인 고객
        }
        return headers

    def fetch_conditional_search(self, seq: str) -> list:
        """
        [핵심 기능] KIS '종목조건검색' API를 호출하여 HTS/MTS에 저장된
        조건식에 해당하는 종목 리스트를 반환합니다.

        (기술 참고: HTS의 실시간 조건검색(ctsc001)은 WebSocket API이므로,
         requests 라이브러리만으로는 구현이 불가합니다.
         본 API(FHPST01710000)는 저장된 조건식을 HTTP GET으로 호출하는 방식입니다.)

        Args:
            seq (str): 종목조건검색 목록조회 API의 output인 'seq'을 이용 (0 부터 시작)

        Returns:
            list: 필터링된 종목 코드(str) 리스트. (e.g., ["005930", "000660"])
        """
        try:
            # 1. 토큰 유효성 검사 및 갱신
            self._check_token()
            
            # 2. API 거래 ID 및 URL 설정
            tr_id = "HHKST03900400" if self.is_prod else "HHKST03900400"
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/psearch-result"
            
            # 3. 헤더 및 파라미터(Query String) 설정
            headers = self._get_headers(tr_id=tr_id)
            params = {
                "user_id": self.hts_user_id,  # HTS ID
                "seq": seq                    # 사용자조건 키값 # 조회 순서 (0부터 시작)
            }
            
            print(f"조건 검색 API 호출... (seq: {seq})")
            
            # 4. API 호출
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status() # HTTP 오류 체크
            
            data = response.json()
            # print(f"data: {data}")
            
            # 5. API 응답 코드(rt_cd) 확인
            if data['rt_cd'] != '0':
                raise Exception(f"API 오류: {data['msg1']} (응답 코드: {data['rt_cd']})")

            # 6. 결과 파싱 (종목 코드 리스트 반환)
            stock_list = [item['code'] for item in data.get('output2', [])]
            
            print(f"조건 검색 성공. 총 {len(stock_list)}개 종목 발견.")
            return stock_list

        except requests.exceptions.RequestException as e:
            print(f"오류: API 호출 실패 - {e}")
            return []
        except Exception as e:
            print(f"오류: {e}")
            return []
        