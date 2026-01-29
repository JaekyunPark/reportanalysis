# 멀티-LLM 보고서 분석 시스템

9개 AI 에이전트(ChatGPT, Claude, Gemini 각 3개)를 활용한 교차 검증 데이터 추출 시스템

## 🌟 주요 기능

- **9개 병렬 에이전트**: OpenAI, Anthropic, Google 각 3개씩 총 9개 에이전트 동시 실행
- **교차 검증**: 모델 내 일관성 및 모델 간 합의를 통한 신뢰도 높은 결과 도출
- **자동 신뢰도 계산**: 각 필드별 신뢰도 점수 자동 산출
- **직관적인 UI**: Streamlit 기반의 사용하기 쉬운 웹 인터페이스
- **다양한 형식 지원**: PDF, 텍스트 파일 보고서 분석 가능

## 📋 시스템 요구사항

- Python 3.8 이상
- 최소 하나 이상의 LLM API 키 (OpenAI, Anthropic, Google)

## 🚀 설치 방법

### 1. 저장소 클론 또는 다운로드

```bash
cd reportanalysis
```

### 2. 가상환경 생성 (권장)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

## 🔑 API 키 준비

다음 중 최소 하나 이상의 API 키가 필요합니다:

- **OpenAI API Key**: https://platform.openai.com/api-keys
- **Anthropic API Key**: https://console.anthropic.com/
- **Google AI API Key**: https://makersuite.google.com/app/apikey

> 💡 **팁**: 더 많은 API 키를 사용할수록 더 정확한 교차 검증이 가능합니다.

## 📊 엑셀 스키마 파일 준비

추출할 데이터 필드를 정의한 엑셀 파일을 준비하세요.

### 필수 컬럼

| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 필드명 | 추출할 데이터의 이름 | "회사명", "총매출액" |
| 설명 | 필드에 대한 상세 설명 | "보고서를 작성한 회사의 이름" |
| 데이터타입 | 데이터 타입 | 텍스트, 숫자, 날짜, 불린, 리스트 |
| 검증규칙 | 추출 시 적용할 규칙 (선택) | "YYYY-MM-DD 형식", "단위: 원" |

### 샘플 파일

`sample_schema.csv` 파일을 참고하세요. Excel로 열어서 `.xlsx` 형식으로 저장하여 사용할 수 있습니다.

## 🎯 사용 방법

### 1. 애플리케이션 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 앱이 실행됩니다.

### 2. API 키 입력

좌측 사이드바에서 사용할 LLM 제공업체의 API 키를 입력합니다.

### 3. 파일 업로드

- **엑셀 스키마 파일**: 추출 항목을 정의한 엑셀 파일
- **보고서 파일**: 분석할 PDF 또는 텍스트 파일

### 4. 분석 실행

"분석 실행" 버튼을 클릭하면:
1. 9개 에이전트가 병렬로 데이터 추출
2. 모델 내 일관성 검증
3. 모델 간 결과 비교
4. 최종 결과 및 신뢰도 점수 제공

### 5. 결과 확인

- **최종 검증 결과**: 9개 에이전트의 합의로 도출된 데이터
- **모델 간 비교**: 각 모델의 결과 차이점
- **에이전트별 결과**: 개별 에이전트의 상세 결과
- **결과 다운로드**: JSON 또는 CSV 형식으로 다운로드

## 🏗️ 프로젝트 구조

```
reportanalysis/
├── app.py                      # 메인 Streamlit 애플리케이션
├── config.py                   # 설정 파일
├── requirements.txt            # 의존성 목록
├── sample_schema.csv           # 샘플 스키마 파일
│
├── llm_clients/               # LLM API 클라이언트
│   ├── __init__.py
│   ├── base_client.py         # 기본 클라이언트 클래스
│   ├── openai_client.py       # OpenAI 클라이언트
│   ├── anthropic_client.py    # Anthropic 클라이언트
│   └── google_client.py       # Google 클라이언트
│
├── data_processing/           # 데이터 처리 모듈
│   ├── __init__.py
│   ├── excel_parser.py        # 엑셀 파서
│   ├── report_loader.py       # 보고서 로더
│   └── prompt_builder.py      # 프롬프트 빌더
│
├── agents/                    # 에이전트 관리
│   ├── __init__.py
│   ├── agent_orchestrator.py  # 병렬 실행 조정자
│   └── result_validator.py    # 결과 검증 및 비교
│
├── ui_components/             # UI 컴포넌트
│   ├── __init__.py
│   └── results_display.py     # 결과 표시 컴포넌트
│
└── utils/                     # 유틸리티
    ├── __init__.py
    └── error_handler.py       # 에러 처리
```

## ⚙️ 설정 (config.py)

### 모델 설정

```python
OPENAI_MODEL = "gpt-5.2"
ANTHROPIC_MODEL = "claude-sonnet-4.5"
GOOGLE_MODEL = "gemini-3-pro-preview"
```

### 신뢰도 임계값

```python
CONFIDENCE_THRESHOLD_HIGH = 0.9   # 높은 신뢰도
CONFIDENCE_THRESHOLD_MEDIUM = 0.7 # 중간 신뢰도
CONFIDENCE_THRESHOLD_LOW = 0.5    # 낮은 신뢰도
```

### 가중치 설정

```python
INTRA_MODEL_WEIGHT = 0.4  # 모델 내 일관성 가중치
CROSS_MODEL_WEIGHT = 0.6  # 모델 간 합의 가중치
```

## 🔍 신뢰도 계산 방식

최종 신뢰도는 다음 두 요소를 결합하여 계산됩니다:

1. **모델 내 일관성 (40%)**: 동일 모델의 3개 에이전트 간 결과 일치도
2. **모델 간 합의 (60%)**: 서로 다른 모델 간 결과 일치도

```
최종 신뢰도 = (모델 내 일관성 × 0.4) + (모델 간 합의 × 0.6)
```

## 💡 사용 팁

- **신뢰도가 낮은 필드**: 수동으로 원본 보고서를 확인하세요
- **모델 간 불일치**: 각 모델의 결과를 비교하여 가장 정확한 값을 선택하세요
- **API 비용 관리**: 필요한 모델만 선택적으로 사용할 수 있습니다
- **대용량 파일**: PDF가 너무 큰 경우 처리 시간이 길어질 수 있습니다

## ⚠️ 주의사항

- 미래 모델명(GPT-5.2, Claude Sonnet 4.5, Gemini-3-pro-preview)을 사용하고 있습니다
- 해당 모델이 출시되기 전까지는 API 호출 시 에러가 발생할 수 있습니다
- 실제 사용 시에는 `config.py`에서 현재 사용 가능한 모델명으로 변경하세요:
  - OpenAI: `gpt-4o`, `gpt-4-turbo`
  - Anthropic: `claude-3-5-sonnet-20241022`
  - Google: `gemini-2.0-flash-exp`, `gemini-1.5-pro-latest`

## 🐛 문제 해결

### API 키 오류
- API 키가 올바른지 확인하세요
- API 사용 한도를 확인하세요

### 파일 업로드 실패
- 파일 크기가 50MB 이하인지 확인하세요
- 파일 형식이 지원되는지 확인하세요 (PDF, TXT, XLSX, XLS)

### 실행 시간이 너무 긴 경우
- 보고서 파일 크기를 줄이세요
- 추출 필드 수를 줄이세요

## 📝 라이선스

이 프로젝트는 개인 및 상업적 용도로 자유롭게 사용할 수 있습니다.

## 🤝 기여

버그 리포트, 기능 제안, 풀 리퀘스트를 환영합니다!

---

**Made with ❤️ using Streamlit, OpenAI, Anthropic, and Google AI**
