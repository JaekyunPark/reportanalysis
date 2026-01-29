"""
에러 처리 유틸리티
"""
import time
import logging
from typing import Callable, Any
from functools import wraps

from config import MAX_RETRIES, RETRY_DELAY

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMAPIError(Exception):
    """LLM API 관련 기본 예외"""
    pass


class APIKeyError(LLMAPIError):
    """API 키 관련 예외"""
    pass


class RateLimitError(LLMAPIError):
    """API 속도 제한 예외"""
    pass


class TimeoutError(LLMAPIError):
    """타임아웃 예외"""
    pass


class InvalidResponseError(LLMAPIError):
    """잘못된 응답 형식 예외"""
    pass


def retry_on_error(max_retries: int = MAX_RETRIES, delay: int = RETRY_DELAY):
    """
    에러 발생 시 재시도하는 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 재시도 간 대기 시간 (초)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except APIKeyError as e:
                    # API 키 에러는 재시도 불가
                    logger.error(f"API 키 에러: {str(e)}")
                    raise
                except RateLimitError as e:
                    # 속도 제한은 더 긴 대기 시간 적용
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"속도 제한 도달. {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries + 1})")
                    if attempt < max_retries:
                        time.sleep(wait_time)
                    last_exception = e
                except (TimeoutError, InvalidResponseError) as e:
                    logger.warning(f"에러 발생: {str(e)}. 재시도 중... (시도 {attempt + 1}/{max_retries + 1})")
                    if attempt < max_retries:
                        time.sleep(delay)
                    last_exception = e
                except Exception as e:
                    logger.error(f"예상치 못한 에러: {str(e)}")
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay)
            
            # 모든 재시도 실패
            logger.error(f"최대 재시도 횟수 초과. 마지막 에러: {str(last_exception)}")
            raise last_exception
        
        return wrapper
    return decorator


def get_user_friendly_error_message(error: Exception) -> str:
    """
    사용자 친화적인 에러 메시지 반환
    
    Args:
        error: 예외 객체
        
    Returns:
        사용자에게 표시할 메시지
    """
    if isinstance(error, APIKeyError):
        return "❌ API 키가 유효하지 않습니다. API 키를 확인해주세요."
    elif isinstance(error, RateLimitError):
        return "⚠️ API 호출 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
    elif isinstance(error, TimeoutError):
        return "⏱️ 요청 시간이 초과되었습니다. 네트워크 연결을 확인해주세요."
    elif isinstance(error, InvalidResponseError):
        return "⚠️ 응답 형식이 올바르지 않습니다. 다시 시도해주세요."
    else:
        return f"❌ 오류가 발생했습니다: {str(error)}"
