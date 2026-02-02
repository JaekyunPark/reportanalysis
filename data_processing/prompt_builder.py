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
            extraction_instructions = """## 추출 지침

1. 보고서에서 각 항목에 해당하는 정보를 찾아 추출해 주세요.
2. 정보가 없는 경우 null을 사용하세요.
3. 각 항목에 대해 값(value)과 그 근거(source)를 객체 형식으로 추출하세요.
   - value: 데이터 값
   - source: 해당 값이 위치한 페이지 번호나 관련 문구
4. 데이터 타입(텍스트, 숫자, 날짜 등)을 준수해 주세요.
5. 보고서에 명시된 내용만 사용하여 추출해 주세요."""
            
            output_format_instruction = f"""## 출력 형식

아래와 같은 JSON 형식으로 응답해 주세요:

{json_example}

설명 없이 JSON 데이터만 출력해 주세요."""
        else:
            extraction_instructions = """## 추출 지침

1. 보고서에서 각 필드에 해당하는 정보를 정확하게 찾아 추출하세요.
2. 정보가 명시되어 있지 않은 경우 null을 사용하세요.
3. **각 필드에 대해 반드시 값(value)과 그 근거(source)를 함께 추출해야 합니다.**
   - `value`: 실제 데이터 값
   - `source`: 해당 값을 찾은 문장, 섹션 위치, 또는 페이지 번호 등 근거가 되는 텍스트 (텍스트에 포함된 `[PAGE n]` 표시를 참고하여 **반드시 페이지 번호를 포함**하세요)
4. 데이터 타입에 맞게 값을 변환하세요:
   - 텍스트: 문자열
   - 숫자: 숫자형 (쉼표 제거)
   - 날짜: "YYYY-MM-DD" 형식
   - 불린: true/false
   - 리스트: 배열 형식
5. 검증 규칙이 있는 경우 반드시 준수하세요.
6. 추측하지 말고 보고서에 명시된 내용만 추출하세요."""
            
            output_format_instruction = f"""## 출력 형식

반드시 다음과 같은 JSON 형식으로 응답하세요 (모든 필드는 value와 source를 가진 객체여야 하며, source에는 페이지 정보가 포함되어야 합니다):

{json_example}

다른 설명이나 주석 없이 순수한 JSON만 출력하세요."""

        # 전체 프롬프트 구성
        prompt = f"""# 보고서 데이터 추출 작업

다음 보고서 내용에서 요청한 데이터를 추출해 주세요.

## 추출할 필드 정의

{fields_text}

## 보고서 내용

{report_text[:15000]}  

{extraction_instructions}

{output_format_instruction}
"""
        
        logger.info(f"프롬프트 생성 완료 (모델 타입: {model_type}, 길이: {len(prompt)} 문자)")
        return prompt
