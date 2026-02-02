"""
LLM 클라이언트 기본 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
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
    async def extract_data(self, prompt: str, total_fields: int = 0, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        프롬프트를 사용하여 데이터 추출
        
        Args:
            prompt: 추출 프롬프트
            total_fields: 전체 추출 항목 수
            progress_callback: 진행 상태보고 콜백 (percentage)
            
        Returns:
            추출된 데이터 딕셔너리
        """
        pass
    
    def calculate_progress(self, partial_text: str, total_fields: int) -> int:
        """
        현재까지의 텍스트를 분석하여 추출된 필드 수 기반의 진행률(%) 계산
        """
        import re
        if total_fields <= 0:
            return 0
            
        # "필드명": { 구조가 몇 번 나타나는지 카운트
        # 스키마 구조에 따라 "field_name": { 형식이 반복되므로 이를 기준으로 판단
        matches = re.findall(r'"[^"]+":\s*\{', partial_text)
        count = len(matches)
        
        # 실제 JSON 구조상 마지막 닫는 괄호 등의 차이로 1개 정도 오차가 있을 수 있으므로 캡핑
        progress = min(int((count / total_fields) * 100), 99)
        return progress
    
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
        import re
        try:
            # 1. 기본적인 공백 제거
            text = response_text.strip()
            
            # 2. 정규표현식을 사용하여 가장 바깥쪽의 { ... } 추출
            # 이는 Markdown 코드 블록(```json)이나 앞뒤 설명 문구가 섞여 있을 때 유용함
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                text = match.group(1)
            
            # 3. JSON 파싱 시도
            try:
                data = json.loads(text)
                return data
            except json.JSONDecodeError:
                # 4. 베스트 에포트: 간단한 문법 오류 수정 시도 (예: 마지막 쉼표 제거)
                # "field": 12, } -> "field": 12 }
                repaired_text = re.sub(r',\s*([}\]])', r'\1', text)
                # 큰 따옴표 중복 등도 있을 수 있으나 일단 마지막 쉼표가 가장 흔함
                data = json.loads(repaired_text)
                logger.info(f"[{self.provider}] JSON 형식을 자동 복구하여 파싱 성공")
                return data
            
        except json.JSONDecodeError as e:
            # 5. 모든 시도 실패 시 원본 텍스트 로그 기록 및 에러 발생
            logger.error(f"JSON 파싱 최종 실패: {str(e)}\n응답 일부: {response_text[:500]}...")
            raise InvalidResponseError(f"응답을 JSON으로 파싱할 수 없습니다 (자동 복구 실패): {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "agent_id": self.agent_id,
            "full_name": f"{self.provider}-{self.agent_id}"
        }
