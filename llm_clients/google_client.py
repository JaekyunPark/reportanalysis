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
        
        # 시스템 지침 설정
        system_instruction = "당신은 보고서 데이터 추출 전문가입니다. 반드시 요청된 JSON 구조를 엄격히 준수하여 유효한 JSON 데이터만 응답해야 합니다. 특히 필드 사이의 쉼표(,)를 절대 누락하지 마세요."

        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
    
    @retry_on_error()
    async def extract_data(self, prompt: str, total_fields: int = 0, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Google API를 사용하여 데이터 추출 (JSON 출력 모드 적용)
        """
        try:
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 시작 (JSON 모드)...")
            
            # 안전 설정
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # 헬퍼 함수: 스트리밍 처리 로직
            async def process_stream():
                # JSON 모드 활성화 및 비동기 스트리밍 시작
                response_stream = await self.model.generate_content_async(
                    prompt,  # enhanced_prompt 대신 원본 prompt 사용 (시스템 지침에서 보완)
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 16384,
                        "response_mime_type": "application/json",
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
            
            result_data = await asyncio.to_thread(self.parse_json_response, full_text)
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
