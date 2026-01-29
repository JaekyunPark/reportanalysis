"""
에이전트 오케스트레이터 - 9개 에이전트 병렬 실행
"""
import asyncio
from typing import Dict, List, Any
import time
import logging

from llm_clients import OpenAIClient, AnthropicClient, GoogleClient
from config import OPENAI_MODEL, ANTHROPIC_MODEL, GOOGLE_MODEL, AGENTS_PER_MODEL
from utils.error_handler import get_user_friendly_error_message

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """9개 에이전트 병렬 실행 조정자"""
    
    def __init__(self, api_keys: Dict[str, str]):
        """
        Args:
            api_keys: API 키 딕셔너리
                {
                    "openai": "sk-...",
                    "anthropic": "sk-ant-...",
                    "google": "..."
                }
        """
        self.api_keys = api_keys
    
    async def run_all_agents(self, prompt: str) -> Dict[str, Any]:
        """
        9개 에이전트를 병렬로 실행
        
        Args:
            prompt: 추출 프롬프트
            
        Returns:
            {
                "openai_results": [result1, result2, result3],
                "anthropic_results": [result1, result2, result3],
                "google_results": [result1, result2, result3],
                "execution_info": {...}
            }
        """
        logger.info("=" * 60)
        logger.info("9개 에이전트 병렬 실행 시작")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # 각 모델별 에이전트 생성
        tasks = []
        agent_info = []
        
        # OpenAI 에이전트 3개
        if self.api_keys.get("openai"):
            for i in range(1, AGENTS_PER_MODEL + 1):
                client = OpenAIClient(self.api_keys["openai"], OPENAI_MODEL, i)
                tasks.append(self._run_single_agent(client, prompt))
                agent_info.append({"provider": "OpenAI", "agent_id": i})
        
        # Anthropic 에이전트 3개
        if self.api_keys.get("anthropic"):
            for i in range(1, AGENTS_PER_MODEL + 1):
                client = AnthropicClient(self.api_keys["anthropic"], ANTHROPIC_MODEL, i)
                tasks.append(self._run_single_agent(client, prompt))
                agent_info.append({"provider": "Anthropic", "agent_id": i})
        
        # Google 에이전트 3개
        if self.api_keys.get("google"):
            for i in range(1, AGENTS_PER_MODEL + 1):
                client = GoogleClient(self.api_keys["google"], GOOGLE_MODEL, i)
                tasks.append(self._run_single_agent(client, prompt))
                agent_info.append({"provider": "Google", "agent_id": i})
        
        # 병렬 실행
        logger.info(f"총 {len(tasks)}개 에이전트 실행 중...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 분류
        openai_results = []
        anthropic_results = []
        google_results = []
        errors = []
        
        for i, (result, info) in enumerate(zip(results, agent_info)):
            if isinstance(result, Exception):
                error_info = {
                    "provider": info["provider"],
                    "agent_id": info["agent_id"],
                    "error": str(result),
                    "error_message": get_user_friendly_error_message(result)
                }
                errors.append(error_info)
                logger.error(f"[{info['provider']}-{info['agent_id']}] 실패: {str(result)}")
            else:
                if info["provider"] == "OpenAI":
                    openai_results.append(result)
                elif info["provider"] == "Anthropic":
                    anthropic_results.append(result)
                elif info["provider"] == "Google":
                    google_results.append(result)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 실행 정보
        execution_info = {
            "total_agents": len(tasks),
            "successful_agents": len(openai_results) + len(anthropic_results) + len(google_results),
            "failed_agents": len(errors),
            "execution_time_seconds": round(execution_time, 2),
            "openai_count": len(openai_results),
            "anthropic_count": len(anthropic_results),
            "google_count": len(google_results),
            "errors": errors
        }
        
        logger.info("=" * 60)
        logger.info(f"실행 완료: {execution_info['successful_agents']}/{execution_info['total_agents']} 성공")
        logger.info(f"실행 시간: {execution_time:.2f}초")
        logger.info("=" * 60)
        
        return {
            "openai_results": openai_results,
            "anthropic_results": anthropic_results,
            "google_results": google_results,
            "execution_info": execution_info
        }
    
    async def _run_single_agent(self, client, prompt: str) -> Dict[str, Any]:
        """
        단일 에이전트 실행
        
        Args:
            client: LLM 클라이언트
            prompt: 추출 프롬프트
            
        Returns:
            {
                "agent_info": {...},
                "data": {...},
                "execution_time": 1.23
            }
        """
        start_time = time.time()
        
        try:
            data = await client.extract_data(prompt)
            execution_time = time.time() - start_time
            
            return {
                "agent_info": client.get_agent_info(),
                "data": data,
                "execution_time": round(execution_time, 2),
                "status": "success"
            }
        except Exception as e:
            # 예외를 다시 발생시켜 gather에서 처리
            raise
