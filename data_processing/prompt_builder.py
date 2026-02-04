"""
프롬프트 빌더
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptBuilder:
    """추출 프롬프트 생성기"""
    
    @staticmethod
    def build_extraction_prompt(schema: Dict[str, Any], report_text: str, model_type: str = "default") -> str:
        """
        스키마와 보고서 텍스트로부터 추출 프롬프트 생성
        
        Args:
            schema: 추출 스키마
            report_text: 보고서 텍스트
            model_type: 모델 유형 ("default", "google")
            
        Returns:
            생성된 프롬프트
        """
        is_google = model_type == "google"
        logger.info(f"추출 프롬프트 생성 중 (모델 타입: {model_type})...")
        
        # 필드 그룹화 (카테고리별)
        grouped_fields = {}
        for field in schema["fields"]:
            category = field.get("category")
            if category not in grouped_fields:
                grouped_fields[category] = []
            grouped_fields[category].append(field)
        
        # 필드 정의 생성
        field_definitions = []
        
        for category, fields in grouped_fields.items():
            if category:
                # 구글인 경우 더 부드러운 표현 사용 및 이모지 제거
                if is_google:
                    section_def = f"\n### 문맥: {category}\n"
                    section_def += f"지침: 아래 항목들은 문서의 '{category}' 섹션 내용을 바탕으로 추출해 주세요.\n"
                else:
                    section_def = f"\n### 📌 문맥: {category}\n"
                    section_def += f"⚠️ **지침**: 문서에서 **'{category}'**와 관련된 섹션 또는 파트를 먼저 찾으세요.\n"
                    section_def += f"다음 항목들은 반드시 **'{category}'** 문맥 내에서 찾아야 합니다:\n"
                field_definitions.append(section_def)
            else:
                if len(grouped_fields) > 1:
                    header = "### 일반 항목" if is_google else "\n### 🌍 일반 항목 (문서 전체 검색)\n"
                    field_definitions.append(header)
            
            for field in fields:
                field_def = f"""
- **{field['name']}**
  - 설명: {field['description']}
  - 데이터 타입: {field['data_type']}"""
            
                if field['validation']:
                    field_def += f"\n  - 검증 규칙: {field['validation']}"
                
                field_definitions.append(field_def)
        
        fields_text = "\n".join(field_definitions)
        
        # JSON 예시 생성
        json_example = "{\n"
        for i, field in enumerate(schema["fields"]):
            comma = "," if i < len(schema["fields"]) - 1 else ""
            
            if field['data_type'] == "숫자":
                example_value = "0"
            elif field['data_type'] == "불린":
                example_value = "true"
            elif field['data_type'] == "리스트":
                example_value = '["항목1", "항목2"]'
            else:
                example_value = '"추출된 값"'
            
            json_example += f'  "{field["name"]}": {{\n'
            json_example += f'    "value": {example_value},\n'
            json_example += f'    "source": "발견된 위치 또는 근거 문장"\n'
            json_example += f'  }}{comma}\n'
        
        json_example += "}"
        
        # 지침 텍스트 구성
        if is_google:
            extraction_instructions = """## 데이터 추출 지침
1. **정확성**: 보고서 내용에서 각 필드에 적합한 정보를 정확하게 추출하세요.
2. **구조 강제**: 모든 필드는 반드시 `{"value": ..., "source": ...}` 객체 구조를 유지해야 합니다.
3. **쉼표 준수**: 각 필드 사이에는 반드시 쉼표(,)가 있어야 합니다. 절대 누락하지 마세요.
4. **근거 부분 인용 (가독성+속도)**: `source`에는 **페이지 번호와 해당 문장의 앞부분(약 20~30자)**만 인용하세요.
5. **특수 문자**: 문자열 내부에 큰따옴표(")가 포함될 경우 반드시 백슬래시(\")로 이스케이프하세요.
6. **결약 처리**: 정보가 없으면 `value`는 `null`, `source`는 "정보 없음"으로 표기하세요.
"""
            
            output_format_instruction = f"""## 출력 형식
반드시 다음 JSON 구조를 따라야 합니다:
{json_example}"""
        else:
            extraction_instructions = """## 데이터 추출 지침
1. **정확성**: 보고서에 명시된 내용만 추출하세요.
2. **구조 강제**: 모든 필드는 반드시 `value`와 `source` 키를 가진 객체여야 합니다.
3. **근거 부분 인용 (속도 개선 핵심)**: `source`에는 해당 정보를 찾은 **페이지 번호와 문장 앞부분 일부**만 짤막하게 기입하세요. 긴 문장 전체를 복사하지 마세요.
4. **데이터 타임**: 정의된 데이터 타입(숫자, 날짜, 리스트 등)을 엄격히 준수하세요."""
            
            output_format_instruction = f"""## 출력 형식
설명 없이 **순수한 JSON 데이터**만 출력하세요. 모든 필드는 아래 예시 구조를 따라야 합니다:

{json_example}"""


        # 전체 프롬프트 구성
        prompt = f"""# 보고서 데이터 추출 작업

다음 보고서 내용에서 요청한 데이터를 추출해 주세요.

## 추출할 필드 정의

{fields_text}

## 보고서 내용 (전체 문맥)

{report_text[:60000]}  # 15,000 -> 60,000자로 확대

{extraction_instructions}

{output_format_instruction}
"""

        
        logger.info(f"프롬프트 생성 완료 (모델 타입: {model_type}, 길이: {len(prompt)} 문자)")
        return prompt
