import pytest
from unittest.mock import patch, MagicMock, ANY
from kis_client import KisClient
from datetime import datetime, timedelta, UTC
import requests

# 테스트용 기본 설정값
TEST_APP_KEY = "test_key"
TEST_APP_SECRET = "test_secret"
TEST_ACCOUNT = "12345678"
TEST_USER_ID = "test_user"
TEST_COND_KEY = "P000000123"

@pytest.fixture
def mock_client():
    """ 모의투자 환경의 KisClient 픽스처 """
    return KisClient(
        app_key=TEST_APP_KEY,
        app_secret=TEST_APP_SECRET,
        account_number=TEST_ACCOUNT,
        hts_user_id=TEST_USER_ID,
        is_prod=False
    )

@pytest.fixture
def prod_client():
    """ 실서버 환경의 KisClient 픽스처 """
    return KisClient(
        app_key=TEST_APP_KEY,
        app_secret=TEST_APP_SECRET,
        account_number=TEST_ACCOUNT,
        hts_user_id=TEST_USER_ID,
        is_prod=True
    )

def test_client_initialization(mock_client, prod_client):
    """ 클라이언트가 올바른 환경(URL)으로 초기화되는지 테스트 """
    assert "openapivts.koreainvestment.com" in mock_client.base_url
    assert mock_client.is_prod == False
    
    assert "openapi.koreainvestment.com" in prod_client.base_url
    assert prod_client.is_prod == True

@patch('requests.post')
def test_get_token_mocked(mock_post, mock_client):
    """ 토큰 발급 로직이 모킹된 응답을 올바르게 처리하는지 테스트 """
    # 모킹된 응답 설정
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "fake_token_string",
        "token_type": "Bearer",
        "expires_in": 86400 # 24시간
    }
    mock_post.return_value = mock_response
    
    # _get_token 호출
    mock_client._get_token()
    
    # 검증
    assert mock_client.access_token == "fake_token_string"
    assert mock_client.token_expiry is not None
    # 토큰 만료 시간이 현재 시간 + (86400 - 60초) 근방인지 확인
    assert mock_client.token_expiry > datetime.now(UTC) + timedelta(seconds=86300)

@patch('requests.post')
def test_get_token_failure(mock_post, mock_client):
    """ 토큰 발급 API 호출이 실패(e.g., 500 오류)했을 때 예외가 발생하는지 테스트 """
    mock_post.side_effect = requests.exceptions.HTTPError("Server Error")
    
    with pytest.raises(requests.exceptions.HTTPError):
        mock_client._get_token()
    
    assert mock_client.access_token is None
    assert mock_client.token_expiry is None

@patch('requests.get')
@patch.object(KisClient, '_get_token', return_value=None) # _get_token은 호출 안 되도록 모킹
def test_fetch_conditional_search_mocked(mock_get_token, mock_get, mock_client):
    """ 조건 검색 API 호출이 모킹된 응답을 올바르게 파싱하는지 테스트 """
    # _check_token이 _get_token을 호출하지 않도록, 유효한 토큰이 이미 있는 것처럼 설정
    mock_client.access_token = "valid_fake_token"
    mock_client.token_expiry = datetime.now(UTC) + timedelta(hours=1)
    
    # API 모킹 응답 설정 (성공)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rt_cd": "0",
        "msg1": "성공",
        "output": [
            {"code": "005930"}, # 삼성전자
            {"code": "000660"}, # SK하이닉스
        ]
    }
    mock_get.return_value = mock_response
    
    # API 호출
    stocks = mock_client.fetch_conditional_search(condition_key=TEST_COND_KEY)
    
    # 검증
    assert stocks == ["005930", "000660"]
    
    # requests.get이 올바른 파라미터로 호출되었는지 확인
    expected_params = {
        "CUST_ID": TEST_USER_ID,
        "COND_KEY": TEST_COND_KEY,
        "SEQ": "0"
    }
    mock_get.assert_called_once_with(
        f"{mock_client.base_url}/uapi/domestic-stock/v1/quotations/psearch-result",
        headers=ANY, # 헤더 내용은 _get_headers 테스트에서 별도 검증
        params=expected_params,
        timeout=10
    )
    # tr_id가 모의투자용(V)인지 확인
    assert mock_get.call_args[1]['headers']['tr_id'] == "VHPST01710000"


@patch('requests.get')
@patch.object(KisClient, '_get_token')
def test_token_refresh_logic(mock_get_token, mock_get, mock_client):
    """ 토큰이 만료되었을 때 _get_token이 자동으로 호출되는지 테스트 """
    # 1. 만료된 토큰 설정
    mock_client.access_token = "expired_token"
    mock_client.token_expiry = datetime.now(UTC) - timedelta(minutes=1)
    
    # 2. API 호출 모킹 (검색 결과는 무시)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rt_cd": "0", "output": []}
    mock_get.return_value = mock_response
    
    # 3. API 호출
    mock_client.fetch_conditional_search(condition_key=TEST_COND_KEY)
    
    # 4. 검증: _get_token (토큰 갱신)이 호출되었는지 확인
    mock_get_token.assert_called_once()
    