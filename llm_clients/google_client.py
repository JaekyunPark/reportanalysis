"""
Google Gemini API 클라이언트
"""
import asyncio
from typing import Dict, Any
import logging

import google.generativeai as genai
from llm_clients.base_client import BaseLLMClient
from utils.error_handler import (
    retry_on_error, 
    APIKeyError, 
    RateLimitError, 
    TimeoutError as CustomTimeoutError
)
from config import API_TIMEOUT

logger = logging.getLogger(__name__)


class GoogleClient(BaseLLMClient):
    """Google Gemini API 클라이언트"""
    
    def __init__(self, api_key: str, model_name: str, agent_id: int):
        super().__init__(api_key, model_name, agent_id)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    @retry_on_error()
    async def extract_data(self, prompt: str) -> Dict[str, Any]:
        """
        Google Gemini API를 사용하여 데이터 추출
        
        Args:
            prompt: 추출 프롬프트
            
        Returns:
            추출된 데이터 딕셔너리
        """
        try:
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 시작...")
            
            # Gemini에게 JSON 형식 요청 추가
            enhanced_prompt = f"{prompt}\n\n반드시 순수한 JSON 형식으로만 응답하세요. 다른 설명이나 텍스트 없이 JSON만 출력하세요."
            
            # Gemini는 동기 API이므로 asyncio.to_thread로 비동기 처리
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    enhanced_prompt,
                    generation_config={
                        "temperature": 0.1,  # 일관성을 위해 낮은 temperature
                        "max_output_tokens": 4096,
                    }
                ),
                timeout=API_TIMEOUT
            )
            
            result_text = response.text
            result_data = self.parse_json_response(result_text)
            
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 완료")
            
            return result_data
            
        except asyncio.TimeoutError:
            raise CustomTimeoutError(f"Google API 요청 시간 초과 ({API_TIMEOUT}초)")
        except Exception as e:
            error_msg = str(e).lower()
            if 'api key' in error_msg or 'authentication' in error_msg:
                raise APIKeyError(f"Google API 키 오류: {str(e)}")
            elif 'rate limit' in error_msg or 'quota' in error_msg:
                raise RateLimitError(f"Google API 속도 제한: {str(e)}")
            else:
                raise
