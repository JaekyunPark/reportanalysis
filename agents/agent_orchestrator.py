"""
에이전트 오케스트레이터 - 9개 에이전트 병렬 실행
"""
import asyncio
from typing import Dict, List, Any, Callable
import time
import logging

from llm_clients import OpenAIClient, AnthropicClient, GoogleClient
from config import OPENAI_MODEL, ANTHROPIC_MODEL, GOOGLE_MODEL

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
    
    async def run_all_agents(self, prompt: Any, agent_counts: Dict[str, int] = None, status_callback: Callable = None, total_fields: int = 0, cancelled_agents: List[str] = None) -> Dict[str, Any]:
        """
        에이전트들을 병렬로 실행
        
        Args:
            prompt: 추출 프롬프트 (문자열 또는 {"default": "...", "google": "..."} 딕셔너리)
            agent_counts: 각 모델별 에이전트 수 딕셔너리 (예: {"openai": 3, "anthropic": 3, "google": 3})
            status_callback: 상태 업데이트 콜백 함수 (agent_id, provider, status, message)
            total_fields: 전체 추출 항목 수
            cancelled_agents: 중단 요청된 개별 에이전트 리스트 (예: ["OpenAI-1", "Anthropic-2"])
            
        Returns:
            ...
        """
        if not agent_counts:
            # 기본값 설정
            agent_counts = {"openai": 3, "anthropic": 3, "google": 3}
            
        if not cancelled_agents:
            cancelled_agents = []
            
        total_requested_agents = sum(agent_counts.values())
        logger.info("=" * 60)
        logger.info(f"{total_requested_agents}개 에이전트 병렬 실행 시작 (항목 수: {total_fields})")
        logger.info("=" * 60)

        
        start_time = time.time()
        
        # 호출 인자 정의
        if isinstance(prompt, dict):
            default_prompt = prompt.get("default", "")
            google_prompt = prompt.get("google", default_prompt)
        else:
            default_prompt = prompt
            google_prompt = prompt

        # 각 모델별 에이전트 생성
        tasks = []
        agent_info = []
        
        # OpenAI 에이전트
        if self.api_keys.get("openai") and agent_counts.get("openai", 0) > 0:
            for i in range(1, agent_counts["openai"] + 1):
                client = OpenAIClient(self.api_keys["openai"], OPENAI_MODEL, i)
                tasks.append(self._run_single_agent(client, default_prompt, status_callback, total_fields, cancelled_agents))
                agent_info.append({"provider": "OpenAI", "agent_id": i})
        
        # Anthropic 에이전트
        if self.api_keys.get("anthropic") and agent_counts.get("anthropic", 0) > 0:
            for i in range(1, agent_counts["anthropic"] + 1):
                client = AnthropicClient(self.api_keys["anthropic"], ANTHROPIC_MODEL, i)
                tasks.append(self._run_single_agent(client, default_prompt, status_callback, total_fields, cancelled_agents))
                agent_info.append({"provider": "Anthropic", "agent_id": i})
        
        # Google 에이전트
        if self.api_keys.get("google") and agent_counts.get("google", 0) > 0:
            for i in range(1, agent_counts["google"] + 1):
                client = GoogleClient(self.api_keys["google"], GOOGLE_MODEL, i)
                tasks.append(self._run_single_agent(client, google_prompt, status_callback, total_fields, cancelled_agents))
                agent_info.append({"provider": "Google", "agent_id": i})

        
        # 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        openai_results = []
        anthropic_results = []
        google_results = []
        errors = []
        cancelled_count = 0
        
        for i, (res, info) in enumerate(zip(results, agent_info)):
            if isinstance(res, Exception):
                # ... (error handling remains same)
                error_info = {
                    "provider": info["provider"],
                    "agent_id": info["agent_id"],
                    "error": str(res),
                    "error_message": get_user_friendly_error_message(res)
                }
                errors.append(error_info)
                if status_callback:
                    status_callback(info['agent_id'], info['provider'], "error", error_info["error_message"])
            elif isinstance(res, dict) and res.get("status") == "cancelled":
                cancelled_count += 1
                # 중단된 경우 결과에 추가하지 않음
            elif isinstance(res, dict) and res.get("status") == "failed":
                # 에이전트 내부에서 에러가 처리되어 반환된 경우
                error_info = {
                    "provider": info["provider"],
                    "agent_id": info["agent_id"],
                    "error": str(res.get("error", "알 수 없는 오류")),
                    "error_message": str(res.get("error", "알 수 없는 오류"))
                }
                errors.append(error_info)
                if status_callback:
                    status_callback(info['agent_id'], info['provider'], "error", error_info["error_message"])
            else:
                # 성공 시 데이터 추가
                if info["provider"] == "OpenAI":
                    openai_results.append(res)
                elif info["provider"] == "Anthropic":
                    anthropic_results.append(res)
                elif info["provider"] == "Google":
                    google_results.append(res)
                
                # 성공 콜백
                if status_callback:
                    status_callback(info['agent_id'], info['provider'], "success", "완료 (100%)")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 실행 정보
        execution_info = {
            "total_agents": len(tasks),
            "successful_agents": len(openai_results) + len(anthropic_results) + len(google_results),
            "failed_agents": len(errors),
            "cancelled_agents": cancelled_count,
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
    
    async def _run_single_agent(self, client, prompt: str, status_callback: Callable = None, total_fields: int = 0, cancelled_agents: List[str] = None) -> Dict[str, Any]:
        """
        단일 에이전트 실행 (순차적 시작 적용 및 스트리밍 진행률 보고)
        
        Args:
            client: LLM 클라이언트
            prompt: 추출 프롬프트
            status_callback: 상태 업데이트 콜백
            total_fields: 전체 추출 항목 수
            cancelled_agents: 중단 요청된 개별 에이전트 리스트
            
        Returns:
            ...
        """
        if not cancelled_agents:
            cancelled_agents = []
            
        agent_key = f"{client.provider}-{client.agent_id}"
        
        # 시작 전 중단 확인
        if agent_key in cancelled_agents:
            if status_callback:
                status_callback(client.agent_id, client.provider, "error", "사용자에 의해 취소됨")
            return {
                "agent_info": client.get_agent_info(),
                "data": {},
                "execution_time": 0,
                "status": "cancelled"
            }
        # 에이전트 간 시작 간격을 두어 속도 제한 예방 (Staggered Start)
        if client.provider == "Anthropic":
            # Anthropic은 TPM(분당 토큰) 제한이 엄격하므로 15초 단위로 띄움 (총 30~45초 분산)
            offset = 5 + (client.agent_id - 1) * 15
        else:
            # OpenAI, Google은 상대적으로 넉넉하므로 1.5초 간격 유지
            provider_offsets = {"OpenAI": 0, "Google": 3}
            offset = provider_offsets.get(client.provider, 0) + (client.agent_id * 1.5)
        
        if offset > 0:
            if status_callback:
                status_callback(client.agent_id, client.provider, "waiting", f"대기 중 ({int(offset)}초)")
            
            # 대기 중에도 주기적으로 중단 확인
            for _ in range(int(offset)):
                await asyncio.sleep(1)
                if agent_key in cancelled_agents:
                    if status_callback:
                        status_callback(client.agent_id, client.provider, "error", "사용자에 의해 취소됨")
                    return {
                        "agent_info": client.get_agent_info(),
                        "data": {},
                        "execution_time": 0,
                        "status": "cancelled"
                    }

        if status_callback:
            status_callback(client.agent_id, client.provider, "running", "분석 시작 (0%)")
            
        start_time = time.time()
        last_progress_time = time.time()
        last_percentage = 0
        
        from config import GOOGLE_STUCK_TIMEOUT
        
        try:
            # 스트리밍 및 진행률 보고 지원하는 extract_data 호출
            # 내부 진행률 보고용 콜백 정의
            def handle_client_progress(percentage):
                nonlocal last_percentage, last_progress_time
                if percentage > last_percentage:
                    last_percentage = percentage
                    last_progress_time = time.time() # 진행률이 오르면 타이머 리셋
                
                if status_callback:
                    status_callback(client.agent_id, client.provider, "running", f"분석 중 ({percentage}%)")

            # 액티브 취소를 위해 태스크로 분리하여 실행 및 감시
            extract_task = asyncio.create_task(
                client.extract_data(prompt, total_fields=total_fields, progress_callback=handle_client_progress)
            )
            
            # 태스크가 완료될 때까지 주기적으로 중단 리스트 및 워치독 확인
            while not extract_task.done():
                try:
                    # 1초 동안 대기하면서 태스크 완료 여부 확인
                    await asyncio.wait_for(asyncio.shield(extract_task), timeout=1.0)
                except asyncio.TimeoutError:
                    # 1. 수동 중단 확인 (기능은 유지하되 UI에서 버튼만 제거)
                    if agent_key in cancelled_agents:
                        extract_task.cancel()
                        return {
                            "agent_info": client.get_agent_info(),
                            "data": {},
                            "execution_time": time.time() - start_time,
                            "status": "cancelled",
                            "error": "사용자에 의해 중단됨"
                        }
                    
                    # 2. 구글 에이전트 워치독 확인
                    if client.provider == "Google":
                        stuck_duration = time.time() - last_progress_time
                        if stuck_duration > GOOGLE_STUCK_TIMEOUT:
                            logger.warning(f"[{agent_key}] {int(stuck_duration)}초 동안 진행률 변화 없음({last_percentage}%). 자동 중단 처리.")
                            extract_task.cancel()
                            if status_callback:
                                status_callback(client.agent_id, client.provider, "error", f"시간 초과로 인한 자동 중단 ({int(GOOGLE_STUCK_TIMEOUT)}초)")
                            return {
                                "agent_info": client.get_agent_info(),
                                "data": {},
                                "execution_time": time.time() - start_time,
                                "status": "failed",
                                "error": f"진행률 고정으로 인한 자동 중단 ({int(GOOGLE_STUCK_TIMEOUT)}초)"
                            }
                    continue
            
            # 태스크 완료됨 (정상 또는 에러)
            data = await extract_task
            execution_time = time.time() - start_time
            
            return {
                "agent_info": client.get_agent_info(),
                "data": data,
                "execution_time": round(execution_time, 2),
                "status": "success"
            }
        except asyncio.CancelledError:
            return {
                "agent_info": client.get_agent_info(),
                "data": {},
                "execution_time": time.time() - start_time,
                "status": "cancelled",
                "error": "작업이 취소되었습니다."
            }
        except Exception as e:
            # 상세 에러 로그 생성을 위해 에러 정보 반환
            error_msg = str(e)
            logger.error(f"[{agent_key}] 분석 실행 오류: {error_msg}")
            return {
                "agent_info": client.get_agent_info(),
                "data": {},
                "execution_time": time.time() - start_time,
                "status": "failed",
                "error": error_msg
            }
