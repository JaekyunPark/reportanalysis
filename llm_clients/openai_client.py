"""
OpenAI API 클라이언트
"""
import asyncio
from typing import Dict, Any
import logging

from openai import AsyncOpenAI
from llm_clients.base_client import BaseLLMClient
from utils.error_handler import (
    retry_on_error, 
    APIKeyError, 
    RateLimitError, 
    TimeoutError as CustomTimeoutError
)
from config import API_TIMEOUT

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""
    
    def __init__(self, api_key: str, model_name: str, agent_id: int):
        super().__init__(api_key, model_name, agent_id)
        self.client = AsyncOpenAI(api_key=api_key)
    
    @retry_on_error()
    async def extract_data(self, prompt: str) -> Dict[str, Any]:
        """
        OpenAI API를 사용하여 데이터 추출
        
        Args:
            prompt: 추출 프롬프트
            
        Returns:
            추출된 데이터 딕셔너리
        """
        try:
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 시작...")
            
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 보고서에서 정확하게 데이터를 추출하는 전문가입니다. 항상 JSON 형식으로 응답하세요."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # 일관성을 위해 낮은 temperature
                    response_format={"type": "json_object"}  # JSON 모드 강제
                ),
                timeout=API_TIMEOUT
            )
            
            result_text = response.choices[0].message.content
            result_data = self.parse_json_response(result_text)
            
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 완료")
            
            return result_data
            
        except asyncio.TimeoutError:
            raise CustomTimeoutError(f"OpenAI API 요청 시간 초과 ({API_TIMEOUT}초)")
        except Exception as e:
            error_msg = str(e).lower()
            if 'api key' in error_msg or 'authentication' in error_msg:
                raise APIKeyError(f"OpenAI API 키 오류: {str(e)}")
            elif 'rate limit' in error_msg or 'quota' in error_msg:
                raise RateLimitError(f"OpenAI API 속도 제한: {str(e)}")
            else:
                raise
