import os
from dotenv import load_dotenv
import google.generativeai as genai
import time

# 환경 변수 로드
load_dotenv()

GEMINI_API_KEY = None
try:
    import streamlit as st
    # Streamlit 환경에서 secrets 먼저 조회
    GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY", st.secrets.get("GEMINI_API_KEY"))
except Exception:
    pass

if not GEMINI_API_KEY:
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY"))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("경고: GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")


def summarize_text(text, video_title=""):
    """
    주어진 텍스트(자막)를 Gemini API를 사용하여 요약합니다.
    """
    if not GEMINI_API_KEY:
        return "API 키가 없어 요약할 수 없습니다."
        
    if not text or len(text.strip()) < 10:
        return "요약할 텍스트가 부족합니다."

    # 프롬프트 구성 (개조식 및 bullet-point 완전 강제)
    prompt = f"""
    당신은 일류 투자기관의 수석 거시경제 분석가(Macro Strategist)입니다.
    아래의 '{video_title}' 유튜브 영상 자막 텍스트를 분석하여, 투자자들이 즉시 참고하고 붙여넣어 활용하기 좋은 건조하고 전문적인 **[거시경제 분석 보고서]** 포맷으로 요약해 주세요.

    [⚠️ 작성 규격 - 극도 중요]
    1. **줄글 서술 절대 금지**: 소제목 아래에 긴 줄글이나 문단 형태의 설명은 일절 사용하지 마십시오.
    2. **100% 개조식(Bullet Point) 강제**: 모든 본문 내용은 반드시 마크다운 말머리기호(`- `)로 시작하는 한 줄 단위의 짧고 핵심적인 개조식 리스트로만 작성하십시오.
    3. **어투 통일**: 
       - 구어체(~요, ~했습니다) 사용 절대 금지.
       - 종결어미는 오직 명사형 및 분석조(~다, ~함, ~임, ~것으로 판단됨, ~전망)로만 끝낼 것.

    [레이아웃 아키텍처]
    아래의 3단 마크다운 포맷을 단 1글자도 빠짐없이 완벽하게 지켜서 렌더링하십시오:

    ### 📊 [1. 핵심 요약]
    - (영상의 전체 핵심 주제와 아젠다를 개조식 문어체로 2~3줄 요약)

    ### 📈 [2. 거시경제 지표 및 핵심 분석]
    - (영상에서 다룬 구체적인 경제 수치, 지표, 핵심 사건 등을 정밀 쪼개서 개조식`- ` 리스트로 4~5개 상세 기술)

    ### 🎯 [3. 전망 및 투자자 대응 전략]
    - (향후 글로벌 시장 전망 및 투자자들이 취해야 할 포지션 전략을 개조식`- ` 리스트로 3개 내외 제시)

    [자막 텍스트]
    {text}
    """

    try:
        # 모델 설정 (gemini-3-flash-preview: 최신 Gemini 3 프리뷰 모델)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        # API 호출
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        print(f"Gemini API 요약 중 오류 발생: {e}")
        return f"요약 실패: {str(e)}"

def summarize_audio(audio_path, video_title=""):
    """
    오디오 파일을 Gemini API에 업로드하여 소리를 직접 분석하고 요약합니다.
    """
    if not GEMINI_API_KEY:
        return "API 키가 없어 요약할 수 없습니다."
        
    if not audio_path or not os.path.exists(audio_path):
        return "오디오 파일을 찾을 수 없습니다."

    try:
        # 1. 파일 업로드
        print(f"[{video_title}] 오디오 파일 업로드 중...")
        sample_file = genai.upload_file(path=audio_path)
        
        # 2. 파일 처리 대기 (Processing 상태 확인)
        while sample_file.state.name == "PROCESSING":
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            raise ValueError("오디오 파일 업로드/처리 실패")

        # 3. 요약 프롬프트 구성 (개조식 및 bullet-point 완전 강제)
        prompt = f"""
        당신은 일류 투자기관의 수석 거시경제 분석가(Macro Strategist)입니다.
        첨부된 오디오 파일의 내용을 듣고 '{video_title}' 영상의 핵심을 투자자들이 즉시 참고하고 붙여넣어 활용하기 좋은 건조하고 전문적인 **[거시경제 분석 보고서]** 포맷으로 요약해 주세요.

        [⚠️ 작성 규격 - 극도 중요]
        1. **줄글 서술 절대 금지**: 소제목 아래에 긴 줄글이나 문단 형태의 설명은 일절 사용하지 마십시오.
        2. **100% 개조식(Bullet Point) 강제**: 모든 본문 내용은 반드시 마크다운 말머리기호(`- `)로 시작하는 한 줄 단위의 짧고 핵심적인 개조식 리스트로만 작성하십시오.
        3. **어투 통일**: 
           - 구어체(~요, ~했습니다) 사용 절대 금지.
           - 종결어미는 오직 명사형 및 분석조(~다, ~함, ~임, ~것으로 판단됨, ~전망)로만 끝낼 것.

        [레이아웃 아키텍처]
        아래의 3단 마크다운 포맷을 단 1글자도 빠짐없이 완벽하게 지켜서 렌더링하십시오:

        ### 📊 [1. 핵심 요약]
        - (영상의 전체 핵심 주제와 아젠다를 개조식 문어체로 2~3줄 요약)

        ### 📈 [2. 거시경제 지표 및 핵심 분석]
        - (영상에서 다룬 구체적인 경제 수치, 지표, 핵심 사건 등을 정밀 쪼개서 개조식`- ` 리스트로 4~5개 상세 기술)

        ### 🎯 [3. 전망 및 투자자 대응 전략]
        - (향후 글로벌 시장 전망 및 투자자들이 취해야 할 포지션 전략을 개조식`- ` 리스트로 3개 내외 제시)
        """

        # 4. 모델 설정 및 생성
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content([prompt, sample_file])
        
        # 5. API 서버에서 업로드된 파일 삭제 (유지 관리)
        genai.delete_file(sample_file.name)
        
        return response.text
        
    except Exception as e:
        print(f"Gemini 오디오 분석 중 오류 발생: {e}")
        return f"오디오 요약 실패: {str(e)}"


if __name__ == "__main__":
    # 간단한 테스트
    sample_text = "안녕하세요. 오늘은 파이썬의 기초에 대해 알아보겠습니다. 파이썬은 배우기 쉽고 간결한 문법을 가진 프로그래밍 언어입니다. 특히 데이터 분석과 인공지능 분야에서 널리 쓰이고 있습니다. 변수 선언부터 조건문, 반복문까지 하나씩 살펴보겠습니다. 구독과 좋아요 부탁드립니다!"
    print("--- 테스트: 텍스트 요약 ---")
    summary = summarize_text(sample_text, "파이썬 기초 강의 1편")
    print(summary)
