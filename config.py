"""
멀티-LLM 보고서 분석 시스템 설정
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()



# 모델 설정
OPENAI_MODEL = "gpt-5.2"
ANTHROPIC_MODEL = "claude-sonnet-4-5"
GOOGLE_MODEL = "gemini-3-pro-preview"

# 각 모델별 기본 에이전트 수
OPENAI_DEFAULT_AGENTS = int(os.getenv("OPENAI_AGENTS", 3))
ANTHROPIC_DEFAULT_AGENTS = int(os.getenv("ANTHROPIC_AGENTS", 3))
GOOGLE_DEFAULT_AGENTS = int(os.getenv("GOOGLE_AGENTS", 3))


# API 설정
API_TIMEOUT = 300  # 초 (긴 보고서 분석을 위해 연장)
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초

# 신뢰도 점수 임계값
CONFIDENCE_THRESHOLD_HIGH = 0.9  # 높은 신뢰도
CONFIDENCE_THRESHOLD_MEDIUM = 0.7  # 중간 신뢰도
CONFIDENCE_THRESHOLD_LOW = 0.5  # 낮은 신뢰도

# 일관성 점수 가중치
INTRA_MODEL_WEIGHT = 0.4  # 모델 내 일관성 가중치
CROSS_MODEL_WEIGHT = 0.6  # 모델 간 합의 가중치

# 엑셀 스키마 컬럼명
EXCEL_COLUMNS = {
    "category": "대분류",
    "field_name": "필드명",
    "description": "설명",
    "data_type": "데이터타입",
    "validation": "검증규칙"
}

# 지원하는 데이터 타입
SUPPORTED_DATA_TYPES = ["텍스트", "숫자", "날짜", "불린", "리스트"]

# UI 설정
MAX_FILE_SIZE_MB = 50  # 최대 파일 크기 (MB)

# 파일 경로 설정
DEFAULT_SCHEMA_FILE = "항목파일_0129.xlsx"

# 에이전트 워치독 설정 (초)
GOOGLE_STUCK_TIMEOUT = 300  # 5분 동안 0%면 포기
