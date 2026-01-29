"""
멀티-LLM 보고서 분석 시스템
메인 Streamlit 애플리케이션
"""
import streamlit as st
import asyncio
import os
from pathlib import Path

from data_processing import ExcelParser, ReportLoader, PromptBuilder
from agents import AgentOrchestrator, ResultValidator
from ui_components import ResultsDisplay
from config import MAX_FILE_SIZE_MB, OPENAI_MODEL, ANTHROPIC_MODEL, GOOGLE_MODEL

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
    
    st.subheader("🔑 API 키")
    
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help=f"GPT 모델 사용: {OPENAI_MODEL}"
    )
    
    anthropic_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help=f"Claude 모델 사용: {ANTHROPIC_MODEL}"
    )
    
    google_key = st.text_input(
        "Google API Key",
        type="password",
        help=f"Gemini 모델 사용: {GOOGLE_MODEL}"
    )
    
    st.divider()
    
    st.subheader("📊 모델 정보")
    st.info(f"""
    **사용 모델:**
    - 🤖 OpenAI: {OPENAI_MODEL}
    - 🧠 Anthropic: {ANTHROPIC_MODEL}
    - ✨ Google: {GOOGLE_MODEL}
    
    **에이전트 구성:**
    - 각 모델당 3개 에이전트
    - 총 9개 병렬 실행
    """)

# 메인 영역
tab1, tab2 = st.tabs(["📤 파일 업로드 & 분석", "ℹ️ 사용 방법"])

with tab1:
    # 파일 업로드
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
            file_size = len(excel_file.getvalue()) / (1024 * 1024)
            st.caption(f"파일 크기: {file_size:.2f} MB")
    
    with col2:
        st.subheader("📄 보고서 파일")
        report_file = st.file_uploader(
            "분석할 보고서 파일을 업로드하세요",
            type=['pdf', 'txt'],
            help=f"최대 {MAX_FILE_SIZE_MB}MB까지 업로드 가능"
        )
        
        if report_file:
            st.success(f"✅ {report_file.name} 업로드 완료")
            file_size = len(report_file.getvalue()) / (1024 * 1024)
            st.caption(f"파일 크기: {file_size:.2f} MB")
    
    st.divider()
    
    # 분석 실행 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_analysis = st.button(
            "🚀 분석 실행",
            type="primary",
            use_container_width=True,
            disabled=not (excel_file and report_file)
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
                # 진행 상황 표시
                progress_container = st.container()
                
                with progress_container:
                    with st.spinner("📊 엑셀 스키마 로드 중..."):
                        # 임시 파일로 저장
                        temp_excel_path = f"temp_{excel_file.name}"
                        with open(temp_excel_path, "wb") as f:
                            f.write(excel_file.getvalue())
                        
                        schema = ExcelParser.load_extraction_schema(temp_excel_path)
                        os.remove(temp_excel_path)
                        
                        st.success(f"✅ 스키마 로드 완료: {schema['total_fields']}개 필드")
                    
                    with st.spinner("📄 보고서 로드 중..."):
                        # 임시 파일로 저장
                        temp_report_path = f"temp_{report_file.name}"
                        with open(temp_report_path, "wb") as f:
                            f.write(report_file.getvalue())
                        
                        # 파일 형식에 따라 로드
                        if report_file.name.endswith('.pdf'):
                            report_text = ReportLoader.load_pdf(temp_report_path)
                        else:
                            report_text = ReportLoader.load_text(temp_report_path)
                        
                        os.remove(temp_report_path)
                        
                        st.success(f"✅ 보고서 로드 완료: {len(report_text)} 문자")
                    
                    with st.spinner("🔨 추출 프롬프트 생성 중..."):
                        prompt = PromptBuilder.build_extraction_prompt(schema, report_text)
                        st.success("✅ 프롬프트 생성 완료")
                    
                    with st.spinner("🤖 9개 에이전트 실행 중... (시간이 소요될 수 있습니다)"):
                        # 에이전트 실행
                        orchestrator = AgentOrchestrator(api_keys)
                        
                        # asyncio 이벤트 루프 실행
                        all_results = asyncio.run(orchestrator.run_all_agents(prompt))
                        
                        exec_info = all_results["execution_info"]
                        st.success(
                            f"✅ 실행 완료: {exec_info['successful_agents']}/{exec_info['total_agents']} "
                            f"에이전트 성공 ({exec_info['execution_time_seconds']}초)"
                        )
                    
                    with st.spinner("🔍 결과 검증 및 비교 중..."):
                        # 결과 검증
                        final_result = ResultValidator.aggregate_final_result(all_results)
                        comparison = ResultValidator.compare_cross_model_results(
                            all_results["openai_results"],
                            all_results["anthropic_results"],
                            all_results["google_results"]
                        )
                        
                        st.success("✅ 검증 완료")
                
                st.divider()
                st.balloons()
                
                # 결과 표시
                st.header("📈 분석 결과")
                
                # 실행 정보
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 에이전트", exec_info['total_agents'])
                with col2:
                    st.metric("성공", exec_info['successful_agents'], 
                             delta=f"-{exec_info['failed_agents']}" if exec_info['failed_agents'] > 0 else None)
                with col3:
                    st.metric("실행 시간", f"{exec_info['execution_time_seconds']}초")
                with col4:
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
                
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                st.exception(e)

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
