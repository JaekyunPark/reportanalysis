"""
Google Gemini API 클라이언트
"""
import asyncio
from typing import Dict, Any, Callable
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
    async def extract_data(self, prompt: str, total_fields: int = 0, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Google API를 사용하여 데이터 추출 (완전 비동기 스트리밍 적용)
        
        Args:
            prompt: 추출 프롬프트
            total_fields: 전체 추출 항목 수
            progress_callback: 진행 상태보고 콜백
            
        Returns:
            추출된 데이터 딕셔너리
        """
        try:
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 시작 (비동기 스트리밍)...")
            
            # Gemini에게 JSON 형식 요청 (안전 필터를 위해 부드러운 표현 사용)
            enhanced_prompt = f"{prompt}\n\n응답은 가급적 다른 설명 없이 순수한 JSON 형식으로만 작성해 주세요."
            
            # 안전 설정
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # 헬퍼 함수: 스트리밍 처리 로직
            async def process_stream():
                # generate_content_async를 사용하여 비동기 스트리밍 시작
                response_stream = await self.model.generate_content_async(
                    enhanced_prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 4096,
                    },
                    safety_settings=safety_settings,
                    stream=True
                )
                
                full_text = ""
                last_progress = 0
                
                async for chunk in response_stream:
                    # 1. 프롬프트 피드백 확인
                    if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback:
                        if hasattr(chunk.prompt_feedback, 'block_reason') and chunk.prompt_feedback.block_reason:
                            raise Exception(f"입력 프롬프트 차단 (사유: {chunk.prompt_feedback.block_reason})")

                    # 2. 텍스트 추출 및 진행률 보고
                    try:
                        full_text += chunk.text
                        if total_fields > 0 and progress_callback:
                            current_progress = self.calculate_progress(full_text, total_fields)
                            if current_progress > last_progress:
                                progress_callback(current_progress)
                                last_progress = current_progress
                    except Exception as e:
                        if hasattr(chunk, 'candidates') and chunk.candidates:
                            candidate = chunk.candidates[0]
                            if candidate.finish_reason == 2:
                                safety_info = ", ".join([f"{str(getattr(r, 'category', 'UNKNOWN'))}: {str(getattr(r, 'probability', 'UNKNOWN'))}" for r in getattr(candidate, 'safety_ratings', [])])
                                raise Exception(f"Google API 출력 안전 필터 차단. 상세 등급: {safety_info}")
                        raise e
                return full_text

            # 스트리밍 과정 전체에 대한 타임아웃 적용
            full_text = await asyncio.wait_for(process_stream(), timeout=API_TIMEOUT)
            
            result_data = self.parse_json_response(full_text)
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 완료")
            
            return result_data
            
        except asyncio.TimeoutError:
            raise CustomTimeoutError(f"Google API 스트리밍 시간 초과 ({API_TIMEOUT}초)")
        except Exception as e:
            error_msg = str(e).lower()
            if 'api key' in error_msg or 'authentication' in error_msg:
                raise APIKeyError(f"Google API 키 오류: {str(e)}")
            elif 'rate limit' in error_msg or 'quota' in error_msg:
                raise RateLimitError(f"Google API 속도 제한: {str(e)}")
            else:
                raise
