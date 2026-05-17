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

    # 프롬프트 구성 (이전 대화에서 정했던 '블로그 작성 스타일' 참고 - 원하시면 수정 가능)
    prompt = f"""
    아래는 '{video_title}' 유튜브 영상의 자막 텍스트입니다.
    이 내용을 독자가 알기 쉽고 흥미롭게 한국어로 요약해주세요.
    
    [요약 규칙]
    1. 전체 내용을 3~5개의 핵심 문단으로 정리할 것.
    2. 너무 딱딱하지 않게, 친근한 블로그 말투(~했답니다, ~하더라고요 등)를 적절히 섞어 쓸 것.
    3. (선택사항) 영상에서 강조한 팁이나 중요한 정보가 있다면 말머리 기호(-)로 눈에 띄게 정리할 것.
    4. 불필요한 인사말이나 아웃트로는 제외하고 핵심 정보만 전달할 것.

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

        # 3. 요약 프롬프트 구성
        prompt = f"""
        당신은 전문적인 블로그 작가이자 경제 전문 요약가입니다.
        첨부된 오디오 파일의 내용을 듣고 '{video_title}' 영상의 핵심을 요약해주세요.
        
        [요약 규칙]
        1. 전체 내용을 3~5개의 핵심 문단으로 정리할 것.
        2. 친근한 블로그 말투(~했답니다, ~하더라고요 등)를 사용할 것.
        3. 중요한 숫자나 핵심 팁은 리스트 형식(-)으로 강조할 것.
        4. 오디오의 시작과 끝에 나오는 인사말을 제외하고 본론만 전달할 것.
        5. 오디오 내용이 한국어가 아닌 경우에도 이해하여 한국어로 요약할 것.
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
