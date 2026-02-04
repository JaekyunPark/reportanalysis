"""
엑셀 설정 파일 파서
"""
import pandas as pd
import os
from datetime import datetime
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
            required_columns = [
                EXCEL_COLUMNS["field_name"],
                EXCEL_COLUMNS["description"]
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
            
            # 대분류 컬럼 존재 여부 확인
            has_category = EXCEL_COLUMNS["category"] in df.columns
            
            # 스키마 구성
            fields = []
            for _, row in df.iterrows():
                # 빈 행 건너뛰기
                if pd.isna(row[EXCEL_COLUMNS["field_name"]]):
                    continue
                
                # 대분류 값 추출 (없으면 None)
                category = None
                if has_category and pd.notna(row[EXCEL_COLUMNS["category"]]):
                    category = str(row[EXCEL_COLUMNS["category"]]).strip()
                
                field = {
                    "category": category,
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

    @staticmethod
    def save_batch_results(batch_results: List[Dict[str, Any]], output_dir: str = "results") -> str:
        """
        여러 보고서의 분석 결과를 하나의 엑셀 파일로 저장
        
        Args:
            batch_results: 각 파일별 final_result 딕셔너리 리스트
            output_dir: 저장할 디렉토리 경로
            
        Returns:
            저장된 파일 경로
        """
        try:
            if not batch_results:
                logger.warning("저장할 결과가 없습니다.")
                return ""

            # 결과 디렉토리 생성
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 데이터 정규화 및 통합
            all_rows = []
            for result in batch_results:
                file_name = result.get("file_name", "unknown")
                final_data = result.get("final_data", {})
                field_confidence = result.get("field_confidence", {})
                
                row = {"파일명": file_name}
                
                # 각 필드의 값(value)만 추출하여 행에 추가
                for field, val_obj in final_data.items():
                    value = val_obj.get("value") if isinstance(val_obj, dict) else val_obj
                    confidence = field_confidence.get(field, 0)
                    
                    row[field] = value
                    row[f"{field}_신뢰도"] = f"{confidence:.1%}"
                
                all_rows.append(row)

            df = pd.DataFrame(all_rows)

            # 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(output_dir, f"batch_analysis_{timestamp}.xlsx")

            # 엑셀 저장
            df.to_excel(file_path, index=False)
            logger.info(f"배치 결과 저장 완료: {file_path}")
            
            return file_path

        except Exception as e:
            logger.error(f"배치 결과 저장 실패: {str(e)}")
            raise

    @staticmethod
    def save_individual_result(final_result: Dict[str, Any], output_dir: str = "results") -> str:
        """
        단일 보고서의 분석 결과를 엑셀 파일로 저장
        
        Args:
            final_result: 단일 파일의 final_result 딕셔너리
            output_dir: 저장할 디렉토리 경로
            
        Returns:
            저장된 파일 경로
        """
        try:
            file_name = final_result.get("file_name", "unknown")
            final_data = final_result.get("final_data", {})
            field_confidence = final_result.get("field_confidence", {})
            
            # 결과 디렉토리 생성
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 데이터 변환
            rows = []
            for field, val_obj in final_data.items():
                value = val_obj.get("value") if isinstance(val_obj, dict) else val_obj
                source = val_obj.get("source") if isinstance(val_obj, dict) else "-"
                confidence = field_confidence.get(field, 0)
                
                rows.append({
                    "필드명": field,
                    "추출값": value,
                    "근거/위치": source,
                    "신뢰도": f"{confidence:.1%}"
                })

            df = pd.DataFrame(rows)

            # 파일명 생성 (원본파일명 + 타임스탬프)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 파일명에서 확장자 제거
            base_name = os.path.splitext(file_name)[0]
            file_path = os.path.join(output_dir, f"result_{base_name}_{timestamp}.xlsx")

            # 엑셀 저장
            df.to_excel(file_path, index=False)
            logger.info(f"개별 결과 저장 완료: {file_path}")
            
            return file_path

        except Exception as e:
            logger.error(f"개별 결과 저장 실패: {str(e)}")
            raise
