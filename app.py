"""
멀티-LLM 보고서 분석 시스템
메인 Streamlit 애플리케이션
"""
import streamlit as st
import asyncio
import os
import json
import pandas as pd
from pathlib import Path

from data_processing import ExcelParser, ReportLoader, PromptBuilder
from agents import AgentOrchestrator, ResultValidator
from ui_components import ResultsDisplay
from utils.analysis_manager import AnalysisManager
from config import (
    MAX_FILE_SIZE_MB, OPENAI_MODEL, ANTHROPIC_MODEL, GOOGLE_MODEL,
    OPENAI_DEFAULT_AGENTS, ANTHROPIC_DEFAULT_AGENTS, GOOGLE_DEFAULT_AGENTS,
    DEFAULT_SCHEMA_FILE
)


# 페이지 설정
st.set_page_config(
    page_title="멀티-LLM 보고서 분석",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("🤖 멀티-LLM 보고서 분석 시스템")
st.markdown("**9개 AI 에이전트를 활용한 교차 검증 데이터 추출**")
st.divider()

# 사이드바 - API 키 입력
with st.sidebar:
    st.header("⚙️ 설정")
    
    with st.expander("🔑 API 키 재설정 (선택 사항)"):
        openai_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help=f"GPT 모델 사용: {OPENAI_MODEL}"
        )
        
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            type="password",
            help=f"Claude 모델 사용: {ANTHROPIC_MODEL}"
        )
        
        google_key = st.text_input(
            "Google API Key",
            value=os.getenv("GOOGLE_API_KEY", ""),
            type="password",
            help=f"Gemini 모델 사용: {GOOGLE_MODEL}"
        )

    
    st.divider()
    
    st.subheader("👥 에이전트 수 설정")
    
    openai_agents = st.slider("OpenAI 에이전트", 0, 5, OPENAI_DEFAULT_AGENTS)
    anthropic_agents = st.slider("Anthropic 에이전트", 0, 5, ANTHROPIC_DEFAULT_AGENTS)
    google_agents = st.slider("Google 에이전트", 0, 5, GOOGLE_DEFAULT_AGENTS)
    
    total_agents = openai_agents + anthropic_agents + google_agents
    
    st.divider()
    
    st.subheader("📊 모델 정보")
    st.info(f"""
    **사용 모델:**
    - 🤖 OpenAI: {OPENAI_MODEL} ({openai_agents}개)
    - 🧠 Anthropic: {ANTHROPIC_MODEL} ({anthropic_agents}개)
    - ✨ Google: {GOOGLE_MODEL} ({google_agents}개)
    
    **총 에이전트:** {total_agents}개 병렬 실행
    """)


# 메인 영역
tab1, tab2 = st.tabs(["📤 파일 업로드 & 분석", "ℹ️ 사용 방법"])

with tab1:
    # 세션 상태 초기화
    if "final_result" not in st.session_state:
        st.session_state.final_result = None
    if "all_results" not in st.session_state:
        st.session_state.all_results = None
    if "comparison" not in st.session_state:
        st.session_state.comparison = None
    if "exec_info" not in st.session_state:
        st.session_state.exec_info = None
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = []
    if "batch_file_path" not in st.session_state:
        st.session_state.batch_file_path = None
    if "cancelled_agents" not in st.session_state:
        st.session_state.cancelled_agents = []
    if "analysis_active" not in st.session_state:
        st.session_state.analysis_active = False
    if "current_file_idx" not in st.session_state:
        st.session_state.current_file_idx = 0
    if "analysis_managers" not in st.session_state:
        st.session_state.analysis_managers = {} # {file_idx: AnalysisManager}
    if "schema" not in st.session_state:
        st.session_state.schema = None
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {}

    # 파일 업로드 (상태 초기화를 위해 콜백 대신 직접 확인)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 엑셀 스키마 파일")
        excel_file = st.file_uploader(
            "추출 항목 정의 엑셀 파일을 업로드하세요",
            type=['xlsx', 'xls'],
            help="필드명, 설명, 데이터타입, 검증규칙 컬럼이 포함되어야 합니다"
        )
        
        if excel_file:
            st.success(f"✅ {excel_file.name} 업로드 완료")
        elif os.path.exists(DEFAULT_SCHEMA_FILE):
            st.info(f"ℹ️ 기본 설정 파일 사용 가능: {DEFAULT_SCHEMA_FILE}")
    
    with col2:
        st.subheader("📄 보고서 파일")
        report_file = st.file_uploader(
            "분석할 보고서 파일을 업로드하세요",
            type=['pdf', 'txt'],
            accept_multiple_files=False,
            help=f"최대 {MAX_FILE_SIZE_MB}MB까지 업로드 가능"
        )
        
        if report_file:
            st.success(f"✅ {report_file.name} 업로드 완료")
    
    st.divider()
    
    # 분석 실행 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_analysis = st.button(
            "🚀 분석 실행",
            type="primary",
            use_container_width=True,
            disabled=not ((excel_file or os.path.exists(DEFAULT_SCHEMA_FILE)) and report_file)
        )
    
    # 분석 실행
    if run_analysis:
        # API 키 확인
        api_keys = {}
        if openai_key:
            api_keys["openai"] = openai_key
        if anthropic_key:
            api_keys["anthropic"] = anthropic_key
        if google_key:
            api_keys["google"] = google_key
        
        if not api_keys:
            st.error("❌ 최소 하나 이상의 API 키를 입력해주세요!")
        else:
            try:
                # API 키 세션 저장
                st.session_state.api_keys = api_keys
                
                # 새로운 분석 시작 시 기존 결과 초기화 및 상태 설정
                st.session_state.final_result = None
                st.session_state.all_results = None
                st.session_state.comparison = None
                st.session_state.exec_info = None
                st.session_state.batch_results = []
                st.session_state.batch_file_path = None
                st.session_state.cancelled_agents = []
                st.session_state.current_file_idx = 0
                
                # 1. 스키마 로드
                with st.spinner("📊 엑셀 스키마 로드 중..."):
                    if excel_file:
                        temp_excel_path = f"temp_{excel_file.name}"
                        with open(temp_excel_path, "wb") as f:
                            f.write(excel_file.getvalue())
                        st.session_state.schema = ExcelParser.load_extraction_schema(temp_excel_path)
                        os.remove(temp_excel_path)
                    else:
                        st.session_state.schema = ExcelParser.load_extraction_schema(DEFAULT_SCHEMA_FILE)
                    
                    st.success(f"✅ 스키마 로드 완료: {st.session_state.schema['total_fields']}개 필드")

                # 분석 활성화
                st.session_state.analysis_active = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ 분석 시작 오류: {str(e)}")

    # 2. 분석 실행 로직
    if st.session_state.analysis_active and report_file and st.session_state.schema:
        try:
            schema = st.session_state.schema
            file_idx = 0 # 단일 파일이므로 0 고정
            
            progress_container = st.container()
            with progress_container:
                # 매니저가 없으면 생성 및 시작
                if file_idx not in st.session_state.analysis_managers:
                    # 보고서 로드
                    with st.spinner(f"📄 [{report_file.name}] 로드 중..."):
                        temp_report_path = f"temp_{report_file.name}"
                        with open(temp_report_path, "wb") as f:
                            f.write(report_file.getvalue())
                        
                        if report_file.name.endswith('.pdf'):
                            report_text = ReportLoader.load_pdf(temp_report_path)
                        else:
                            report_text = ReportLoader.load_text(temp_report_path)
                        os.remove(temp_report_path)
                        
                        # 프롬프트 생성
                        with st.spinner(f"🔨 [{report_file.name}] 프롬프트 생성 중..."):
                            default_prompt = PromptBuilder.build_extraction_prompt(schema, report_text, model_type="default")
                            google_prompt = PromptBuilder.build_extraction_prompt(schema, report_text, model_type="google")
                            prompts = {"default": default_prompt, "google": google_prompt}
                        
                        manager = AnalysisManager(st.session_state.api_keys)
                        manager.report_char_count = len(report_text)
                        manager.start_analysis(prompts, {"openai": openai_agents, "anthropic": anthropic_agents, "google": google_agents}, schema)
                        st.session_state.analysis_managers[file_idx] = manager
                
                manager = st.session_state.analysis_managers[file_idx]
                
                # 보고서 정보 표시
                if manager.report_char_count > 0:
                    st.info(f"📄 보고서 읽기 완료: 약 {manager.report_char_count}자")

                # 상태 표시 및 폴링
                st.subheader("🤖 에이전트 분석 진행 상황")
                status_grid = st.empty()
                progress_bar = st.progress(0)

                # 상태 업데이트 루프 (폴링)
                import time
                while manager.is_running:
                    manager_info = manager.get_status()
                    status_data = []
                    completed_count = 0
                    
                    providers_config = [("OpenAI", openai_agents), ("Anthropic", anthropic_agents), ("Google", google_agents)]
                    for provider, count in providers_config:
                        for i in range(1, count + 1):
                            status_info = manager_info["agent_statuses"].get((provider, i), {"status": "waiting", "message": "대기 중"})
                            s = status_info["status"]
                            icon = "⏳" if s == "waiting" else "🔄" if s == "running" else "✅" if s == "success" else "❌"
                            if s in ["success", "error", "cancelled"]:
                                completed_count += 1
                            status_data.append({"내용": f"{provider}-{i}", "상태": f"{icon} {s.upper()}", "상세": status_info["message"]})
                    
                    df_status = pd.DataFrame(status_data)
                    status_grid.table(df_status)
                    total_requested = openai_agents + anthropic_agents + google_agents
                    if total_requested > 0:
                        progress_bar.progress(min(completed_count / total_requested, 1.0))
                        
                    # 결과가 이미 나왔으면 루프 종료
                    if manager_info["results"]:
                        break
                        
                    # 짧은 대기 후 새로고침 유도 (사용자 경험 개선)
                    time.sleep(1)
                    # st.rerun()을 호출하면 좋으나 루프를 빠져나가게 되므로 
                    # Streamlit의 empty 컨테이너 업데이트로 충분함.

                # 최종 결과 수집
                all_results = manager.results

                # 결과 검증
                with st.spinner(f"🔍 [{report_file.name}] 결과 검증 중..."):
                    field_order = [f["name"] for f in schema["fields"]]
                    final_result = ResultValidator.aggregate_final_result(all_results, field_order=field_order)
                    final_result["file_name"] = report_file.name # 파일명 추가
                    
                    comparison = ResultValidator.compare_cross_model_results(
                        all_results["openai_results"], all_results["anthropic_results"], all_results["google_results"],
                        field_order=field_order
                    )
                    
                    # 개별 파일 결과 자동 저장
                    individual_file_path = ExcelParser.save_individual_result(final_result)
                    
                    # 분석 결과 저장
                    st.session_state.final_result = final_result
                    st.session_state.all_results = all_results
                    st.session_state.comparison = comparison
                    st.session_state.exec_info = all_results["execution_info"]
                    st.session_state.batch_results = [{
                        "file_name": report_file.name,
                        "final_result": final_result,
                        "all_results": all_results,
                        "comparison": comparison,
                        "exec_info": all_results["execution_info"],
                        "file_path": individual_file_path
                    }]
                    
                    # 매니저 삭제 및 상태 해제
                    del st.session_state.analysis_managers[file_idx]
                    st.session_state.analysis_active = False
                    
                    # 풍선 효과
                    st.balloons()
                st.rerun()

        except Exception as e:
            st.error(f"❌ 분석 과정 오류: {str(e)}")
            st.session_state.analysis_active = False
            st.rerun()

    # 결과 표시 (세션 상태에 결과가 있는 경우 실행 여부와 관계없이 표시)
    if st.session_state.batch_results:
        st.header("📋 배치 분석 요약")
        
        # 통합 엑셀 다운로드 버튼
        if st.session_state.batch_file_path and os.path.exists(st.session_state.batch_file_path):
            col1, col2 = st.columns([1, 1])
            with col1:
                with open(st.session_state.batch_file_path, "rb") as f:
                    st.download_button(
                        label="📥 통합 결과 엑셀 다운로드",
                        data=f,
                        file_name=os.path.basename(st.session_state.batch_file_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
            with col2:
                st.info("💡 각 파일별 결과도 아래 목록에서 개별적으로 다운로드할 수 있습니다.")
        
        # 파일별 요약 테이블 및 개별 다운로드
        summary_data = []
        for res_entry in st.session_state.batch_results:
            res = res_entry["final_result"]
            summary_data.append({
                "파일명": res_entry.get("file_name", "unknown"),
                "평균 신뢰도": f"{res.get('overall_confidence', 0):.1%}",
                "신뢰도 등급": res.get("confidence_grade", "-"),
                "결과 파일": os.path.basename(res_entry.get("output_path", "-")) if res_entry.get("output_path") else "-"
            })
        
        st.subheader("📁 파일별 분석 요약 및 다운로드")
        
        # 테이블 대신 컬럼으로 다운로드 버튼 배치
        for res_entry in st.session_state.batch_results:
            res = res_entry["final_result"]
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                with col1:
                    st.write(f"📄 **{res_entry.get('file_name')}**")
                with col2:
                    st.write(f"{res.get('overall_confidence', 0):.1%}")
                with col3:
                    st.write(res.get('confidence_grade'))
                with col4:
                    output_path = res_entry.get("output_path")
                    if output_path and os.path.exists(output_path):
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="📥 다운로드",
                                data=f,
                                file_name=os.path.basename(output_path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{res_entry.get('file_name')}"
                            )
                st.divider()
        
        st.divider()
        
        # 개별 파일 상세 결과 선택
        st.subheader("🔍 개별 파일 상세 결과 확인")
        selected_file_name = st.selectbox(
            "상세 정보 확인을 위한 파일을 선택하세요",
            options=[res["file_name"] for res in st.session_state.batch_results]
        )
        
        # 선택된 파일의 결과 찾기
        selected_entry = next((res for res in st.session_state.batch_results if res["file_name"] == selected_file_name), None)
        
        if selected_entry:
            # 상세 정보 표시
            # 1. 실행 요약 (유저 요청 복구)
            st.subheader("📊 에이전트 실행 요약")
            exec_info = selected_entry.get("exec_info", {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 에이전트", f"{exec_info.get('total_agents', 0)}개")
            with col2:
                st.metric("성공", f"{exec_info.get('successful_agents', 0)}개", delta_color="normal")
            with col3:
                st.metric("실패", f"{exec_info.get('failed_agents', 0)}개", delta_color="inverse" if exec_info.get('failed_agents', 0) > 0 else "normal")
            with col4:
                st.metric("실행 시간", f"{exec_info.get('execution_time_seconds', 0)}초")
            
            # 모델별 성공 카운트
            st.write(f"✅ 모델별 성공: OpenAI ({exec_info.get('openai_count', 0)}) | Anthropic ({exec_info.get('anthropic_count', 0)}) | Google ({exec_info.get('google_count', 0)})")
            
            # 에러 발생 시 로그 표시
            if exec_info.get("errors"):
                ResultsDisplay.display_error_status(exec_info["errors"])
            
            st.divider()

            # 최종 결과
            ResultsDisplay.display_final_results(selected_entry["final_result"])
            
            st.divider()
            
            # 모델 간 비교
            ResultsDisplay.display_comparison_table(selected_entry["comparison"])
            
            st.divider()
            
            # 에이전트별 결과
            ResultsDisplay.display_agent_results_grid(selected_entry["all_results"])

    elif st.session_state.final_result and st.session_state.exec_info:
        final_result = st.session_state.final_result
        all_results = st.session_state.all_results
        comparison = st.session_state.comparison
        exec_info = st.session_state.exec_info

        st.header("📈 분석 결과")
        
        # 실행 정보
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("총 에이전트", exec_info['total_agents'])
        with col2:
            st.metric("성공", exec_info['successful_agents'])
        with col3:
            st.metric("실패", exec_info['failed_agents'])
        with col4:
            st.metric("중단", exec_info.get('cancelled_agents', 0))
        with col5:
            st.metric("신뢰도", f"{final_result['overall_confidence']:.1%}")
        
        st.divider()
        
        # 에러 표시
        if exec_info['errors']:
            ResultsDisplay.display_error_status(exec_info['errors'])
            st.divider()
        
        # 최종 결과
        ResultsDisplay.display_final_results(final_result)
        
        st.divider()
        
        # 모델 간 비교
        ResultsDisplay.display_comparison_table(comparison)
        
        st.divider()
        
        # 에이전트별 결과
        ResultsDisplay.display_agent_results_grid(all_results)

with tab2:
    st.header("📖 사용 방법")
    
    st.markdown("""
    ### 1️⃣ API 키 설정
    좌측 사이드바에서 사용할 LLM 제공업체의 API 키를 입력하세요.
    - 최소 하나 이상의 API 키가 필요합니다
    - 더 많은 API 키를 입력할수록 더 정확한 교차 검증이 가능합니다
    
    ### 2️⃣ 엑셀 스키마 파일 준비
    추출할 데이터 필드를 정의한 엑셀 파일을 준비하세요.
    
    **필수 컬럼:**
    - `필드명`: 추출할 데이터의 이름
    - `설명`: 필드에 대한 상세 설명
    - `데이터타입`: 텍스트, 숫자, 날짜, 불린, 리스트 중 선택
    - `검증규칙`: 추출 시 적용할 규칙 (선택사항)
    
    ### 3️⃣ 보고서 파일 업로드
    분석할 보고서를 PDF 또는 텍스트 파일로 업로드하세요.
    
    ### 4️⃣ 분석 실행
    "분석 실행" 버튼을 클릭하면:
    1. 9개 에이전트가 병렬로 데이터를 추출합니다
    2. 각 모델 내에서 일관성을 검증합니다
    3. 모델 간 결과를 비교합니다
    4. 최종 결과와 신뢰도 점수를 제공합니다
    
    ### 5️⃣ 결과 확인
    - **최종 검증 결과**: 9개 에이전트의 합의로 도출된 최종 데이터
    - **모델 간 비교**: 각 모델의 결과 차이점 확인
    - **에이전트별 결과**: 개별 에이전트의 상세 추출 결과
    
    ### 💡 팁
    - 신뢰도가 낮은 필드는 수동으로 재확인하세요
    - 모델 간 결과가 다른 경우, 원본 보고서를 참조하세요
    - JSON 또는 CSV로 결과를 다운로드할 수 있습니다
    """)
    
    st.divider()
    
    st.header("⚙️ 시스템 정보")
    st.code(f"""
모델 설정:
- OpenAI: {OPENAI_MODEL}
- Anthropic: {ANTHROPIC_MODEL}
- Google: {GOOGLE_MODEL}

에이전트 구성:
- 각 모델당 3개 에이전트
- 총 9개 병렬 실행

신뢰도 계산:
- 모델 내 일관성 (40%)
- 모델 간 합의 (60%)
    """)

# 푸터
st.divider()
st.caption("🤖 멀티-LLM 보고서 분석 시스템 v1.0 | 9개 AI 에이전트 교차 검증")
