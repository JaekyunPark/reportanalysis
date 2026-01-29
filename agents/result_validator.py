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
        
        Args:
            results: 동일 모델의 결과 리스트
            
        Returns:
            일관성 점수 (0.0 ~ 1.0)
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
                    values.append(result["data"][field])
            
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
        google_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        모델 간 결과 비교
        
        Args:
            openai_results: OpenAI 결과 리스트
            anthropic_results: Anthropic 결과 리스트
            google_results: Google 결과 리스트
            
        Returns:
            비교 결과
        """
        logger.info("모델 간 결과 비교 시작...")
        
        # 각 모델의 대표 결과 (다수결)
        openai_consensus = ResultValidator._get_consensus_result(openai_results)
        anthropic_consensus = ResultValidator._get_consensus_result(anthropic_results)
        google_consensus = ResultValidator._get_consensus_result(google_results)
        
        # 필드별 비교
        all_fields = set()
        if openai_consensus:
            all_fields.update(openai_consensus.keys())
        if anthropic_consensus:
            all_fields.update(anthropic_consensus.keys())
        if google_consensus:
            all_fields.update(google_consensus.keys())
        
        field_comparison = {}
        
        for field in all_fields:
            openai_value = openai_consensus.get(field) if openai_consensus else None
            anthropic_value = anthropic_consensus.get(field) if anthropic_consensus else None
            google_value = google_consensus.get(field) if google_consensus else None
            
            values = [v for v in [openai_value, anthropic_value, google_value] if v is not None]
            
            # 일치 여부
            all_match = len(set(str(v) for v in values)) == 1 if values else False
            
            field_comparison[field] = {
                "openai": openai_value,
                "anthropic": anthropic_value,
                "google": google_value,
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
    def aggregate_final_result(all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        최종 결과 집계 및 신뢰도 점수 계산
        
        Args:
            all_results: run_all_agents의 결과
            
        Returns:
            최종 집계 결과
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
            openai_results, anthropic_results, google_results
        )
        
        # 최종 값 결정 (다수결)
        final_data = {}
        field_confidence = {}
        
        for field, comparison in cross_model_comparison["field_comparison"].items():
            values = [
                comparison["openai"],
                comparison["anthropic"],
                comparison["google"]
            ]
            values = [v for v in values if v is not None]
            
            if not values:
                final_data[field] = None
                field_confidence[field] = 0.0
                continue
            
            # 다수결로 최종 값 결정
            value_counts = Counter(str(v) for v in values)
            most_common_value_str, most_common_count = value_counts.most_common(1)[0]
            
            # 원본 값 찾기
            final_value = next(v for v in values if str(v) == most_common_value_str)
            final_data[field] = final_value
            
            # 필드별 신뢰도 계산
            agreement_ratio = most_common_count / len(values)
            
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
        
        Args:
            results: 결과 리스트
            
        Returns:
            합의된 결과
        """
        if not results:
            return {}
        
        # 첫 번째 결과의 필드 목록
        if not results[0].get("data"):
            return {}
        
        fields = results[0]["data"].keys()
        consensus = {}
        
        for field in fields:
            values = []
            for result in results:
                if "data" in result and field in result["data"]:
                    values.append(result["data"][field])
            
            if not values:
                consensus[field] = None
                continue
            
            # 가장 많이 나온 값
            value_counts = Counter(str(v) for v in values)
            most_common_value_str = value_counts.most_common(1)[0][0]
            
            # 원본 값 찾기
            consensus[field] = next(v for v in values if str(v) == most_common_value_str)
        
        return consensus
