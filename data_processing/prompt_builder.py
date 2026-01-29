"""
프롬프트 빌더
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptBuilder:
    """추출 프롬프트 생성기"""
    
    @staticmethod
    def build_extraction_prompt(schema: Dict[str, Any], report_text: str) -> str:
        """
        스키마와 보고서 텍스트로부터 추출 프롬프트 생성
        
        Args:
            schema: 추출 스키마
            report_text: 보고서 텍스트
            
        Returns:
            생성된 프롬프트
        """
        logger.info("추출 프롬프트 생성 중...")
        
        # 필드 정의 생성
        field_definitions = []
        for field in schema["fields"]:
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
            
            json_example += f'  "{field["name"]}": {example_value}{comma}\n'
        
        json_example += "}"
        
        # 전체 프롬프트 구성
        prompt = f"""# 보고서 데이터 추출 작업

다음 보고서에서 지정된 필드의 데이터를 정확하게 추출하세요.

## 추출할 필드 정의

{fields_text}

## 보고서 내용

{report_text[:15000]}  

## 추출 지침

1. 보고서에서 각 필드에 해당하는 정보를 정확하게 찾아 추출하세요.
2. 정보가 명시되어 있지 않은 경우 null을 사용하세요.
3. 데이터 타입에 맞게 값을 변환하세요:
   - 텍스트: 문자열
   - 숫자: 숫자형 (쉼표 제거)
   - 날짜: "YYYY-MM-DD" 형식
   - 불린: true/false
   - 리스트: 배열 형식
4. 검증 규칙이 있는 경우 반드시 준수하세요.
5. 추측하지 말고 보고서에 명시된 내용만 추출하세요.

## 출력 형식

반드시 다음과 같은 JSON 형식으로 응답하세요:

{json_example}

다른 설명이나 주석 없이 순수한 JSON만 출력하세요.
"""
        
        logger.info(f"프롬프트 생성 완료 (길이: {len(prompt)} 문자)")
        return prompt
