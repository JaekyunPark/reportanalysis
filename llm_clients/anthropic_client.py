"""
Anthropic API 클라이언트
"""
import asyncio
from typing import Dict, Any, Callable
import logging

from anthropic import AsyncAnthropic
from llm_clients.base_client import BaseLLMClient
from utils.error_handler import (
    retry_on_error, 
    APIKeyError, 
    RateLimitError, 
    TimeoutError as CustomTimeoutError
)
from config import API_TIMEOUT

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic API 클라이언트"""
    
    def __init__(self, api_key: str, model_name: str, agent_id: int):
        super().__init__(api_key, model_name, agent_id)
        self.client = AsyncAnthropic(api_key=api_key)
    
    @retry_on_error()
    async def extract_data(self, prompt: str, total_fields: int = 0, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Anthropic API를 사용하여 데이터 추출 (스트리밍 적용)
        
        Args:
            prompt: 추출 프롬프트
            total_fields: 전체 추출 항목 수
            progress_callback: 진행 상태보고 콜백
            
        Returns:
            추출된 데이터 딕셔너리
        """
        try:
            # 스트리밍 요청 및 처리 전체를 타임아웃으로 감싸기
            async def process_anthropic_stream():
                # Anthropic 전용 시스템 프롬프트 및 메시지 구성
                system_prompt = "당신은 보고서에서 정확하게 데이터를 추출하여 순수 JSON 형식으로만 응답하는 전문가입니다. 다른 설명은 배제하세요."
                
                full_text_local = "{"  # Prefill을 위해 '{'로 시작
                last_progress_local = 0
                
                async with self.client.messages.stream(
                    model=self.model_name,
                    max_tokens=8192,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        },
                        {
                            "role": "assistant",
                            "content": "{"
                        }
                    ]
                ) as stream:
                    async for text in stream.text_stream:
                        full_text_local += text

                        # 진행률 계산 및 콜백 호출
                        if total_fields > 0 and progress_callback:
                            current_progress = self.calculate_progress(full_text_local, total_fields)
                            if current_progress > last_progress_local:
                                progress_callback(current_progress)
                                last_progress_local = current_progress
                return full_text_local

            full_text = await asyncio.wait_for(process_anthropic_stream(), timeout=API_TIMEOUT)
            result_data = await asyncio.to_thread(self.parse_json_response, full_text)
            
            logger.info(f"[{self.get_agent_info()['full_name']}] 데이터 추출 완료")
            
            return result_data
            
        except asyncio.TimeoutError:
            raise CustomTimeoutError(f"Anthropic API 요청 시간 초과 ({API_TIMEOUT}초)")
        except Exception as e:
            error_msg = str(e).lower()
            if 'api key' in error_msg or 'authentication' in error_msg:
                raise APIKeyError(f"Anthropic API 키 오류: {str(e)}")
            elif 'rate limit' in error_msg or 'quota' in error_msg:
                raise RateLimitError(f"Anthropic API 속도 제한: {str(e)}")
            else:
                raise
