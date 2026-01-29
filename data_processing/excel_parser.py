"""
엑셀 설정 파일 파서
"""
import pandas as pd
from typing import Dict, List, Any
import logging

from config import EXCEL_COLUMNS, SUPPORTED_DATA_TYPES

logger = logging.getLogger(__name__)


class ExcelParser:
    """엑셀 추출 스키마 파서"""
    
    @staticmethod
    def load_extraction_schema(file_path: str) -> Dict[str, Any]:
        """
        엑셀 파일에서 추출 스키마 로드
        
        Args:
            file_path: 엑셀 파일 경로
            
        Returns:
            추출 스키마 딕셔너리
            {
                "fields": [
                    {
                        "name": "필드명",
                        "description": "설명",
                        "data_type": "데이터타입",
                        "validation": "검증규칙"
                    },
                    ...
                ]
            }
        """
        try:
            logger.info(f"엑셀 스키마 로드 중: {file_path}")
            
            # 엑셀 파일 읽기
            df = pd.read_excel(file_path)
            
            # 컬럼명 확인
            required_columns = list(EXCEL_COLUMNS.values())
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
            
            # 스키마 구성
            fields = []
            for _, row in df.iterrows():
                # 빈 행 건너뛰기
                if pd.isna(row[EXCEL_COLUMNS["field_name"]]):
                    continue
                
                field = {
                    "name": str(row[EXCEL_COLUMNS["field_name"]]).strip(),
                    "description": str(row[EXCEL_COLUMNS["description"]]).strip() if pd.notna(row[EXCEL_COLUMNS["description"]]) else "",
                    "data_type": str(row[EXCEL_COLUMNS["data_type"]]).strip() if pd.notna(row[EXCEL_COLUMNS["data_type"]]) else "텍스트",
                    "validation": str(row[EXCEL_COLUMNS["validation"]]).strip() if pd.notna(row[EXCEL_COLUMNS["validation"]]) else ""
                }
                
                # 데이터 타입 검증
                if field["data_type"] not in SUPPORTED_DATA_TYPES:
                    logger.warning(f"지원하지 않는 데이터 타입 '{field['data_type']}', 기본값 '텍스트'로 설정")
                    field["data_type"] = "텍스트"
                
                fields.append(field)
            
            schema = {
                "fields": fields,
                "total_fields": len(fields)
            }
            
            logger.info(f"스키마 로드 완료: {len(fields)}개 필드")
            return schema
            
        except Exception as e:
            logger.error(f"엑셀 파일 로드 실패: {str(e)}")
            raise
