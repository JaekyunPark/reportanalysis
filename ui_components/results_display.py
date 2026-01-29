"""
UI 컴포넌트 - 결과 표시
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Any
import json


class ResultsDisplay:
    """결과 표시 UI 컴포넌트"""
    
    @staticmethod
    def display_agent_results_grid(all_results: Dict[str, Any]):
        """
        9개 에이전트 결과를 3x3 그리드로 표시
        
        Args:
            all_results: run_all_agents의 결과
        """
        st.header("📊 에이전트별 추출 결과")
        
        # 탭으로 모델별 구분
        tabs = st.tabs(["🤖 OpenAI (GPT)", "🧠 Anthropic (Claude)", "✨ Google (Gemini)"])
        
        # OpenAI 결과
        with tabs[0]:
            ResultsDisplay._display_model_results(
                all_results["openai_results"],
                "OpenAI",
                "🟢"
            )
        
        # Anthropic 결과
        with tabs[1]:
            ResultsDisplay._display_model_results(
                all_results["anthropic_results"],
                "Anthropic",
                "🔵"
            )
        
        # Google 결과
        with tabs[2]:
            ResultsDisplay._display_model_results(
                all_results["google_results"],
                "Google",
                "🟡"
            )
    
    @staticmethod
    def _display_model_results(results: List[Dict[str, Any]], model_name: str, icon: str):
        """모델별 결과 표시"""
        if not results:
            st.warning(f"{model_name} 모델의 결과가 없습니다.")
            return
        
        cols = st.columns(len(results))
        
        for i, (col, result) in enumerate(zip(cols, results)):
            with col:
                agent_info = result.get("agent_info", {})
                st.subheader(f"{icon} Agent {agent_info.get('agent_id', i+1)}")
                st.caption(f"⏱️ {result.get('execution_time', 0)}초")
                
                # 데이터 표시
                data = result.get("data", {})
                if data:
                    # JSON 형식으로 표시
                    with st.expander("📄 추출 데이터", expanded=True):
                        st.json(data)
                else:
                    st.error("데이터 없음")
    
    @staticmethod
    def display_comparison_table(comparison: Dict[str, Any]):
        """
        모델 간 비교 테이블 표시
        
        Args:
            comparison: compare_cross_model_results의 결과
        """
        st.header("🔍 모델 간 비교 분석")
        
        # 전체 일치율
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "전체 일치율",
                f"{comparison['overall_agreement']:.1%}",
                f"{comparison['matching_fields']}/{comparison['total_fields']} 필드"
            )
        with col2:
            st.metric(
                "일치 필드",
                comparison['matching_fields']
            )
        with col3:
            st.metric(
                "전체 필드",
                comparison['total_fields']
            )
        
        st.divider()
        
        # 필드별 비교 테이블
        st.subheader("필드별 상세 비교")
        
        comparison_data = []
        for field, comp in comparison["field_comparison"].items():
            all_match = "✅" if comp["all_match"] else "⚠️"
            
            comparison_data.append({
                "필드명": field,
                "일치": all_match,
                "OpenAI": str(comp["openai"]) if comp["openai"] is not None else "-",
                "Anthropic": str(comp["anthropic"]) if comp["anthropic"] is not None else "-",
                "Google": str(comp["google"]) if comp["google"] is not None else "-",
                "합의도": f"{comp['agreement_count']}/{comp['total_models']}"
            })
        
        df = pd.DataFrame(comparison_data)
        
        # 스타일 적용
        def highlight_mismatch(row):
            if row["일치"] == "⚠️":
                return ['background-color: #fff3cd'] * len(row)
            return [''] * len(row)
        
        styled_df = df.style.apply(highlight_mismatch, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    @staticmethod
    def display_final_results(final_result: Dict[str, Any]):
        """
        최종 검증된 결과 표시
        
        Args:
            final_result: aggregate_final_result의 결과
        """
        st.header("✅ 최종 검증 결과")
        
        # 신뢰도 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            confidence = final_result["overall_confidence"]
            grade = final_result["confidence_grade"]
            
            # 신뢰도에 따른 색상
            if grade == "높음":
                delta_color = "normal"
                emoji = "🟢"
            elif grade == "중간":
                delta_color = "off"
                emoji = "🟡"
            else:
                delta_color = "inverse"
                emoji = "🔴"
            
            st.metric(
                "전체 신뢰도",
                f"{confidence:.1%}",
                f"{emoji} {grade}"
            )
        
        with col2:
            st.metric(
                "OpenAI 일관성",
                f"{final_result['model_consistency']['openai']:.1%}"
            )
        
        with col3:
            st.metric(
                "Anthropic 일관성",
                f"{final_result['model_consistency']['anthropic']:.1%}"
            )
        
        with col4:
            st.metric(
                "Google 일관성",
                f"{final_result['model_consistency']['google']:.1%}"
            )
        
        st.divider()
        
        # 최종 데이터 테이블
        st.subheader("📋 최종 추출 데이터")
        
        final_data_list = []
        for field, value in final_result["final_data"].items():
            confidence = final_result["field_confidence"].get(field, 0)
            
            # 신뢰도 표시
            if confidence >= 0.9:
                conf_badge = "🟢 높음"
            elif confidence >= 0.7:
                conf_badge = "🟡 중간"
            else:
                conf_badge = "🔴 낮음"
            
            final_data_list.append({
                "필드명": field,
                "추출값": str(value) if value is not None else "-",
                "신뢰도": f"{confidence:.1%}",
                "등급": conf_badge
            })
        
        df_final = pd.DataFrame(final_data_list)
        st.dataframe(df_final, use_container_width=True, hide_index=True)
        
        # JSON 다운로드
        st.subheader("💾 결과 다운로드")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON 다운로드
            json_str = json.dumps(final_result["final_data"], ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSON 다운로드",
                data=json_str,
                file_name="extraction_result.json",
                mime="application/json"
            )
        
        with col2:
            # CSV 다운로드
            csv_data = df_final.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv_data,
                file_name="extraction_result.csv",
                mime="text/csv"
            )
    
    @staticmethod
    def display_error_status(errors: List[Dict[str, Any]]):
        """
        에러 상태 표시
        
        Args:
            errors: 에러 정보 리스트
        """
        if not errors:
            return
        
        st.error(f"⚠️ {len(errors)}개 에이전트 실행 실패")
        
        with st.expander("에러 상세 정보"):
            for error in errors:
                st.write(f"**{error['provider']} Agent {error['agent_id']}**")
                st.write(f"- {error['error_message']}")
                st.caption(f"상세: {error['error']}")
                st.divider()
