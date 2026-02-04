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
            
        # 1. 필드 시작 지점 ("필드명": {) - 가장 일반적인 지점
        c1 = len(re.findall(r'"[^"]+":\s*\{', partial_text))
        
        # 2. 필드 핵심 내용 ("value":) - 필드명 가공 시에도 변하지 않는 고정 키
        c2 = len(re.findall(r'"value"\s*:\s*', partial_text))
        
        # 둘 중 더 많이 진행된 지점을 기준으로 카운트 (스트리밍 시점에 따라 다를 수 있음)
        count = max(c1, c2)
        
        # 실제 JSON 구조상 마지막 닫는 괄호 등의 차이로 1개 정도 오차가 있을 수 있으므로 캡핑
        progress = int((count / total_fields) * 100)
        return min(progress, 100)
    
    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        LLM 응답에서 JSON 추출 및 파싱 (강화된 복구 로직 포함)
        """
        import re
        
        # 1. 기본적인 전처리
        text = response_text.strip()
        
        # 2. Markdown 코드 블록 제거 및 가장 바깥쪽 { ... } 추출
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            text = match.group(1)
        
        # 3. 여러 단계의 복구 시도
        attempts = [
            lambda t: t,  # 1단계: 원본 시도
            # 2단계: 문자열 내 줄바꿈(Newline) 처리 (가장 흔함)
            lambda t: re.sub(r'(?<=:)\s*"(.*?)"(?=\s*[,}])', 
                             lambda m: '"' + m.group(1).replace('\n', '\\n') + '"', t, flags=re.DOTALL),
            # 3단계: 마지막 쉼표 제거: "field": 12, } -> "field": 12 }
            lambda t: re.sub(r',\s*([}\]])', r'\1', t),
            # 4단계: 필드 사이 쉼표 누락: } "field" -> } , "field"  또는 "val" "field" -> "val", "field"
            lambda t: re.sub(r'\}\s*"', r'} , "', t),
            lambda t: re.sub(r'("[^"]*")\s*(")', r'\1, \2', t),
            # 5단계: 숫자/불린/null 뒤에 쉼표 누락: 123 "field" -> 123, "field"
            lambda t: re.sub(r'(true|false|null|\d+)\s*(")', r'\1, \2', t),
            # 6단계: 문자열 내 이스케이프되지 않은 따옴표 처리 (비탐욕적 매칭으로 개별 필드 처리)
            # "source": "문장 "인용" 문구" -> "source": "문장 \"인용\" 문구"
            lambda t: re.sub(r'(?<=:)\s*"(.*?)"(?=\s*[,}])', 
                             lambda m: '"' + m.group(1).replace('"', '\\"') + '"', t, flags=re.DOTALL)
        ]


        
        last_exception = None
        for i, repair_func in enumerate(attempts):
            try:
                repaired = repair_func(text)
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                last_exception = e
                text = repaired  # 다음 단계는 이전 복구 결과를 기반으로 진행
                continue
                
        # 4. 모든 시도 실패 시 로그 기록 및 에러 발생
        logger.error(f"[{self.provider}] JSON 파싱 최종 실패: {str(last_exception)}\n응답 일부: {response_text[:500]}...")
        raise InvalidResponseError(f"응답을 JSON으로 파싱할 수 없습니다 (자동 복구 {len(attempts)}단계 시도 실패): {str(last_exception)}")

    
    def get_agent_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "agent_id": self.agent_id,
            "full_name": f"{self.provider}-{self.agent_id}"
        }
