"""
결과 검증 및 비교
"""
from typing import Dict, List, Any
import logging
from collections import Counter

from config import (
    CONFIDENCE_THRESHOLD_HIGH,
    CONFIDENCE_THRESHOLD_MEDIUM,
    INTRA_MODEL_WEIGHT,
    CROSS_MODEL_WEIGHT
)

logger = logging.getLogger(__name__)


class ResultValidator:
    """결과 비교 및 검증"""
    
    @staticmethod
    def calculate_intra_model_consistency(results: List[Dict[str, Any]]) -> float:
        """
        동일 모델 그룹 내 일관성 계산
        """
        if len(results) < 2:
            return 1.0
        
        # 각 필드별 일치도 계산
        field_scores = []
        
        # 첫 번째 결과의 필드 목록 가져오기
        if not results or not results[0].get("data"):
            return 0.0
        
        fields = results[0]["data"].keys()
        
        for field in fields:
            values = []
            for result in results:
                if "data" in result and field in result["data"]:
                    # 데이터가 딕셔너리이고 'value' 키가 있는 경우 처리
                    val = result["data"][field]
                    if isinstance(val, dict) and "value" in val:
                        values.append(val["value"])
                    else:
                        values.append(val)
            
            if not values:
                continue
            
            # 가장 많이 나온 값의 비율
            value_counts = Counter(str(v) for v in values)
            most_common_count = value_counts.most_common(1)[0][1]
            consistency = most_common_count / len(values)
            field_scores.append(consistency)
        
        if not field_scores:
            return 0.0
        
        return sum(field_scores) / len(field_scores)
    
    @staticmethod
    def compare_cross_model_results(
        openai_results: List[Dict[str, Any]],
        anthropic_results: List[Dict[str, Any]],
        google_results: List[Dict[str, Any]],
        field_order: List[str] = None
    ) -> Dict[str, Any]:
        """
        모델 간 결과 비교
        """
        logger.info("모델 간 결과 비교 시작...")
        
        # 각 모델의 대표 결과 (다수결)
        openai_consensus = ResultValidator._get_consensus_result(openai_results)
        anthropic_consensus = ResultValidator._get_consensus_result(anthropic_results)
        google_consensus = ResultValidator._get_consensus_result(google_results)
        
        # 필드 목록 결정 (field_order가 있으면 우선 사용)
        if field_order:
            all_fields = field_order
        else:
            all_fields = set()
            if openai_consensus:
                all_fields.update(openai_consensus.keys())
            if anthropic_consensus:
                all_fields.update(anthropic_consensus.keys())
            if google_consensus:
                all_fields.update(google_consensus.keys())
            all_fields = sorted(list(all_fields)) # 기본적으로 정렬
        
        field_comparison = {}
        
        for field in all_fields:
            # 값만 추출하여 비교
            openai_val = openai_consensus.get(field)
            if isinstance(openai_val, dict) and "value" in openai_val:
                openai_val = openai_val["value"]
                
            anthropic_val = anthropic_consensus.get(field)
            if isinstance(anthropic_val, dict) and "value" in anthropic_val:
                anthropic_val = anthropic_val["value"]
                
            google_val = google_consensus.get(field)
            if isinstance(google_val, dict) and "value" in google_val:
                google_val = google_val["value"]
            
            values = [v for v in [openai_val, anthropic_val, google_val] if v is not None]
            
            # 일치 여부 (값이 없으면 False)
            if not values:
                field_comparison[field] = {
                    "openai": None, "anthropic": None, "google": None,
                    "all_match": False, "agreement_count": 0, "total_models": 0
                }
                continue

            all_match = len(set(str(v) for v in values)) == 1 if values else False
            
            field_comparison[field] = {
                "openai": openai_val,
                "anthropic": anthropic_val,
                "google": google_val,
                "all_match": all_match,
                "agreement_count": len([v for v in values if str(v) == str(values[0])]) if values else 0,
                "total_models": len(values)
            }
        
        # 전체 일치율
        matching_fields = sum(1 for comp in field_comparison.values() if comp["all_match"])
        total_fields = len(field_comparison)
        overall_agreement = matching_fields / total_fields if total_fields > 0 else 0.0
        
        logger.info(f"모델 간 일치율: {overall_agreement:.2%} ({matching_fields}/{total_fields} 필드)")
        
        return {
            "field_comparison": field_comparison,
            "overall_agreement": overall_agreement,
            "matching_fields": matching_fields,
            "total_fields": total_fields,
            "openai_consensus": openai_consensus,
            "anthropic_consensus": anthropic_consensus,
            "google_consensus": google_consensus
        }
    
    @staticmethod
    def aggregate_final_result(all_results: Dict[str, Any], field_order: List[str] = None) -> Dict[str, Any]:
        """
        최종 결과 집계 및 신뢰도 점수 계산
        """
        logger.info("최종 결과 집계 시작...")
        
        openai_results = all_results["openai_results"]
        anthropic_results = all_results["anthropic_results"]
        google_results = all_results["google_results"]
        
        # 모델 내 일관성 계산
        openai_consistency = ResultValidator.calculate_intra_model_consistency(openai_results)
        anthropic_consistency = ResultValidator.calculate_intra_model_consistency(anthropic_results)
        google_consistency = ResultValidator.calculate_intra_model_consistency(google_results)
        
        # 모델 간 비교
        cross_model_comparison = ResultValidator.compare_cross_model_results(
            openai_results, anthropic_results, google_results, field_order=field_order
        )
        
        # 최종 값 결정 (다수결)
        final_data = {}
        field_confidence = {}
        
        # 컨센서스 결과 (source 정보 포함)
        openai_consensus = cross_model_comparison["openai_consensus"]
        anthropic_consensus = cross_model_comparison["anthropic_consensus"]
        google_consensus = cross_model_comparison["google_consensus"]
        
        # 순서 보장을 위해 comparison에서 필드 목록 가져옴 (이미 정렬되어 있음)
        for field, comparison in cross_model_comparison["field_comparison"].items():
            # 값만 있는 리스트 (비교용)
            values = [
                comparison["openai"],
                comparison["anthropic"],
                comparison["google"]
            ]
            valid_values = [v for v in values if v is not None]
            
            if not valid_values:
                final_data[field] = None
                field_confidence[field] = 0.0
                continue
            
            # 다수결로 최종 값 결정
            value_counts = Counter(str(v) for v in valid_values)
            most_common_value_str, most_common_count = value_counts.most_common(1)[0]
            
            # 최종 값과 소스 찾기
            # 가장 많이 선택된 값(value)을 가진 전체 객체(value+source)를 찾음
            final_obj = None
            
            # 우선순위: 다수결에 해당하는 값 중 source가 있는 것 선호
            candidates = []
            
            # OpenAI 확인
            if openai_consensus.get(field):
                val = openai_consensus[field].get("value") if isinstance(openai_consensus[field], dict) else openai_consensus[field]
                if str(val) == most_common_value_str:
                    candidates.append(openai_consensus[field])
            
            # Anthropic 확인
            if anthropic_consensus.get(field):
                val = anthropic_consensus[field].get("value") if isinstance(anthropic_consensus[field], dict) else anthropic_consensus[field]
                if str(val) == most_common_value_str:
                    candidates.append(anthropic_consensus[field])
                    
            # Google 확인
            if google_consensus.get(field):
                val = google_consensus[field].get("value") if isinstance(google_consensus[field], dict) else google_consensus[field]
                if str(val) == most_common_value_str:
                    candidates.append(google_consensus[field])
            
            if candidates:
                final_obj = candidates[0] # 첫 번째 후보 선택
                
                # 구조 통일 (단순 값인 경우 객체로 변환)
                if not isinstance(final_obj, dict) or "value" not in final_obj:
                    final_obj = {"value": final_obj, "source": None}
            else:
                final_obj = {"value": None, "source": None}
            
            final_data[field] = final_obj
            
            # 필드별 신뢰도 계산
            agreement_ratio = most_common_count / len(valid_values)
            
            # 모델 내 일관성도 고려
            avg_intra_consistency = (openai_consistency + anthropic_consistency + google_consistency) / 3
            
            confidence = (
                agreement_ratio * CROSS_MODEL_WEIGHT +
                avg_intra_consistency * INTRA_MODEL_WEIGHT
            )
            field_confidence[field] = round(confidence, 3)
        
        # 전체 신뢰도
        overall_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0.0
        
        # 신뢰도 등급
        if overall_confidence >= CONFIDENCE_THRESHOLD_HIGH:
            confidence_grade = "높음"
        elif overall_confidence >= CONFIDENCE_THRESHOLD_MEDIUM:
            confidence_grade = "중간"
        else:
            confidence_grade = "낮음"
        
        logger.info(f"최종 신뢰도: {overall_confidence:.2%} ({confidence_grade})")
        
        return {
            "final_data": final_data,
            "field_confidence": field_confidence,
            "overall_confidence": round(overall_confidence, 3),
            "confidence_grade": confidence_grade,
            "model_consistency": {
                "openai": round(openai_consistency, 3),
                "anthropic": round(anthropic_consistency, 3),
                "google": round(google_consistency, 3)
            },
            "cross_model_agreement": round(cross_model_comparison["overall_agreement"], 3)
        }
    
    @staticmethod
    def _get_consensus_result(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        결과 리스트에서 다수결로 합의된 결과 추출
        (Nested 구조 지원: value 기준으로 다수결, source는 value가 일치하는 것 중 하나 선택)
        """
        if not results:
            return {}
        
        # 첫 번째 결과의 필드 목록
        if not results[0].get("data"):
            return {}
        
        fields = results[0]["data"].keys()
        consensus = {}
        
        for field in fields:
            values_to_compare = [] # 비교용 (문자열 변환된 값)
            full_objects = [] # 원본 객체 (value, source 포함)
            
            for result in results:
                if "data" in result and field in result["data"]:
                    obj = result["data"][field]
                    full_objects.append(obj)
                    
                    # 값 추출
                    if isinstance(obj, dict) and "value" in obj:
                        values_to_compare.append(str(obj["value"]))
                    else:
                        values_to_compare.append(str(obj))
            
            if not values_to_compare:
                consensus[field] = None
                continue
            
            # 가장 많이 나온 값
            value_counts = Counter(values_to_compare)
            most_common_value_str = value_counts.most_common(1)[0][0]
            
            # 해당 값을 가진 원본 객체 찾기
            # source가 있는 것을 선호
            best_obj = None
            found = False
            
            for obj in full_objects:
                val_str = ""
                if isinstance(obj, dict) and "value" in obj:
                    val_str = str(obj["value"])
                else:
                    val_str = str(obj)
                
                if val_str == most_common_value_str:
                    best_obj = obj
                    # 소스가 있고, 비어있지 않은 경우 우선 선택
                    if isinstance(obj, dict) and "source" in obj and obj["source"]:
                        found = True
                        break
            
            consensus[field] = best_obj
        
        return consensus
