"""
LLM 클라이언트 기본 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import logging

from utils.error_handler import InvalidResponseError

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """모든 LLM 클라이언트의 기본 클래스"""
    
    def __init__(self, api_key: str, model_name: str, agent_id: int):
        """
        Args:
            api_key: API 키
            model_name: 모델명
            agent_id: 에이전트 ID (1-3)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.agent_id = agent_id
        self.provider = self.__class__.__name__.replace('Client', '')
    
    @abstractmethod
    async def extract_data(self, prompt: str) -> Dict[str, Any]:
        """
        프롬프트를 사용하여 데이터 추출
        
        Args:
            prompt: 추출 프롬프트
            
        Returns:
            추출된 데이터 딕셔너리
        """
        pass
    
    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        LLM 응답에서 JSON 추출 및 파싱
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            파싱된 JSON 딕셔너리
            
        Raises:
            InvalidResponseError: JSON 파싱 실패 시
        """
        try:
            # JSON 코드 블록 제거 (```json ... ``` 형식)
            text = response_text.strip()
            if text.startswith('```'):
                # 첫 번째와 마지막 줄 제거
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1])
            
            # JSON 파싱
            data = json.loads(text)
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}\n응답: {response_text[:200]}...")
            raise InvalidResponseError(f"응답을 JSON으로 파싱할 수 없습니다: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "agent_id": self.agent_id,
            "full_name": f"{self.provider}-{self.agent_id}"
        }
