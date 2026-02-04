import threading
import asyncio
import time
from typing import Dict, List, Any, Callable, Optional
import logging

from agents.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class AnalysisManager:
    """분석 프로세스를 백그라운드에서 관리하여 Streamlit 리런 시에도 중단되지 않게 함"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.orchestrator = AgentOrchestrator(api_keys)
        
        # 상태 정보
        self.is_running = False
        self.progress_log = [] # [(agent_id, provider, status, message), ...]
        self.agent_statuses = {} # {(provider, agent_id): {"status": str, "message": str}}
        self.results = None
        self.error = None
        self.cancelled_agents = []
        self.report_char_count = 0
        
        # 쓰레드 관리
        self._thread = None
        self._loop = None

    def start_analysis(self, prompts: Dict[str, str], agent_counts: Dict[str, int], schema: Dict[str, Any]):
        """백그라운드 쓰레드에서 분석 시작"""
        if self.is_running:
            return
            
        self.is_running = True
        self.results = None
        self.error = None
        self.progress_log = []
        self.agent_statuses = {}
        
        # 쓰레드 생성 및 시작
        self._thread = threading.Thread(
            target=self._run_async_wrapper,
            args=(prompts, agent_counts, schema),
            daemon=True
        )
        self._thread.start()

    def _run_async_wrapper(self, prompts, agent_counts, schema):
        """asyncio 루프를 쓰레드에 생성하여 오케스트레이터 실행"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            total_fields = len(schema.get("fields", []))
            
            # run_all_agents 실행
            result = self._loop.run_until_complete(
                self.orchestrator.run_all_agents(
                    prompts,
                    agent_counts=agent_counts,
                    status_callback=self._status_callback,
                    total_fields=total_fields,
                    cancelled_agents=self.cancelled_agents
                )
            )
            self.results = result
        except Exception as e:
            logger.error(f"Background analysis error: {str(e)}")
            self.error = str(e)
        finally:
            self.is_running = False
            self._loop.close()

    def _status_callback(self, agent_id, provider, status, message):
        """오케스트레이터의 상태 업데이트를 저장"""
        key = (provider, agent_id)
        self.agent_statuses[key] = {"status": status, "message": message}
        self.progress_log.append((agent_id, provider, status, message))

    def update_cancelled_agents(self, cancelled_list: List[str]):
        """중단 요청 리스트 업데이트 (참조 유지를 위해 내용만 업데이트)"""
        self.cancelled_agents.clear()
        self.cancelled_agents.extend(cancelled_list)

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 요약 반환"""
        return {
            "is_running": self.is_running,
            "agent_statuses": self.agent_statuses,
            "results": self.results,
            "error": self.error
        }
