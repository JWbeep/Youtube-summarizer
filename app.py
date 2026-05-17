import streamlit as st
import os
import json
import glob
from dotenv import load_dotenv

# core 모듈 임포트
from core.fetcher import fetch_videos_for_channels
from core.transcript import get_transcript
from core.summarizer import summarize_text, summarize_audio
from core.storage import save_summary, get_summary, has_summary
from core.audio_fetcher import download_audio_only

# 환경변수 로드
load_dotenv()

# Streamlit 기본 설정
st.set_page_config(
    page_title="유튜브 요약 생성기",
    page_icon="📺",
    layout="wide"
)

# 데이터 경로 정의
LATEST_LIST_PATH = "data/latest_video_list.json"
CACHE_DIR = "data/summaries"

# 기본 폴더 생성
os.makedirs("data", exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 데이터 도우미 함수
# ------------------------------------------------------------------
def load_latest_video_list():
    """마지막으로 유튜브 API에서 수집한 영상 목록 캐시를 불러옵니다."""
    if os.path.exists(LATEST_LIST_PATH):
        try:
            with open(LATEST_LIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"영상 목록 캐시를 불러오는데 오류가 발생했습니다: {e}")
    return []

def save_latest_video_list(video_list):
    """유튜브 API에서 수집한 최신 영상 목록을 로컬 파일로 저장합니다."""
    try:
        with open(LATEST_LIST_PATH, "w", encoding="utf-8") as f:
            json.dump(video_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"영상 목록 캐시를 저장하는데 오류가 발생했습니다: {e}")

# ------------------------------------------------------------------
# 세션 상태(Session State) 초기화
# ------------------------------------------------------------------
if "latest_videos" not in st.session_state:
    # 앱 시작 시 항상 빈 화면으로 시작 (이전 캐시 자동 로드 금지)
    st.session_state.latest_videos = []

if "displayed_video_ids" not in st.session_state:
    # 우측 메인 화면에 띄울 비디오 ID들의 목록 (처음엔 빈 화면)
    st.session_state.displayed_video_ids = []

# ------------------------------------------------------------------
# 사이드바 설정 및 최신 목록 로드
# ------------------------------------------------------------------
st.sidebar.title("📺 유튜브 요약 생성기")
st.sidebar.markdown("""
구독 중인 채널의 최신 영상을 골라
AI가 스마트하게 요약해 드립니다.
""")

# ① [유튜브 최신 영상 목록 조회] 버튼
if st.sidebar.button("🔄 최신 영상 목록 가져오기", use_container_width=True):
    # 버튼 클릭 시 기존 캐시 파일 및 세션 상태 완전 초기화
    st.session_state.displayed_video_ids = []
    st.session_state.latest_videos = []
    
    # 기존 영상 목록 캐시 파일 삭제
    if os.path.exists(LATEST_LIST_PATH):
        try:
            os.remove(LATEST_LIST_PATH)
        except Exception:
            pass
    
    with st.spinner("유튜브 채널의 최신 영상 리스트를 동기화하는 중..."):
        latest = fetch_videos_for_channels()
        if latest:
            st.session_state.latest_videos = latest
            save_latest_video_list(latest)
            
            # 신규 업데이트 비디오 개수 계산 (로컬 캐시 summaries 폴더에 요약이 없는 영상들)
            new_videos = [v for v in latest if not has_summary(v['video_id'])]
            
            if len(new_videos) > 0:
                st.sidebar.success(f"새로 요약 가능한 최신 동영상 {len(new_videos)}개를 발견했습니다!")
            else:
                # 이미 모든 동영상이 요약 완료된 상태이거나 새로운 영상이 업로드되지 않은 경우
                st.sidebar.info("최신 업데이트 된 영상이 없습니다.")
        else:
            st.sidebar.warning("설정된 채널의 최신 동영상을 찾지 못했습니다. API 키와 설정을 확인해주세요.")

st.sidebar.divider()

# ② 최신 영상 체크박스 리스트 표시
selected_video_ids = []
if st.session_state.latest_videos:
    st.sidebar.subheader("📌 요약할 영상 선택")
    st.sidebar.markdown("<small>요약을 원하는 영상을 체크한 뒤 아래 버튼을 눌러주세요.</small>", unsafe_allow_html=True)
    
    # [채널명 | 재생목록명] 조합으로 다중 그룹핑 생성
    video_groups = {}
    for video in st.session_state.latest_videos:
        ch = video['channel_name']
        corner = video.get('corner_name', '일반 업로드')
        group_key = (ch, corner)
        
        if group_key not in video_groups:
            video_groups[group_key] = []
        video_groups[group_key].append(video)
        
    for (ch_name, corner_name), v_list in video_groups.items():
        # 채널명 | 재생목록명 소제목 출력
        display_header = f"🔹 {ch_name} | {corner_name}" if corner_name else f"🔹 {ch_name}"
        st.sidebar.markdown(f"**{display_header}**")
        
        for video in v_list:
            v_id = video['video_id']
            title = video['title']
            published = video['published_at'][:10]
            
            # 이미 요약 캐시가 로컬에 있는 영상은 옆에 '✅ 완료' 표시
            is_cached = has_summary(v_id)
            
            # 만약 기존 캐시파일 요약 내용에 에러 메시지가 박혀 있다면 완료 마킹에서 배제
            if is_cached:
                existing_data = get_summary(v_id)
                if not existing_data or "요약 실패" in existing_data.get("summary", ""):
                    is_cached = False
                    
            status_badge = " [✅ 완료]" if is_cached else ""
            
            # 텍스트 길이를 2배 이상인 60자로 확장하여 제목 잘림 최소화
            display_title = f"{title[:60]}..." if len(title) > 60 else title
            cb_label = f"{display_title} ({published}){status_badge}"
            
            checked = st.sidebar.checkbox(cb_label, value=False, key=f"cb_{v_id}")
            if checked:
                selected_video_ids.append(v_id)
                
        st.sidebar.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)
else:
    st.sidebar.info("💡 위의 '최신 영상 목록 가져오기' 버튼을 누르시면 수집이 시작됩니다!")


st.sidebar.divider()

# ③ [선택한 영상 요약 실행] 버튼
if selected_video_ids:
    btn_label = f"📝 선택한 {len(selected_video_ids)}개 영상 요약하기"
    if st.sidebar.button(btn_label, type="primary", use_container_width=True):
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        success_count = 0
        total_selected = len(selected_video_ids)
        
        # 선택한 영상 데이터 매칭
        selected_videos = [v for v in st.session_state.latest_videos if v['video_id'] in selected_video_ids]
        
        for idx, video in enumerate(selected_videos):
            v_id = video['video_id']
            v_title = video['title']
            
            status_text.text(f"처리 중 ({idx+1}/{total_selected}): {v_title[:15]}...")
            
            # 이미 완벽한 요약이 존재하는지 확인
            if has_summary(v_id):
                existing_data = get_summary(v_id)
                if existing_data and "요약 실패" not in existing_data.get("summary", ""):
                    # 완벽한 요약본이 있으므로 API 호출 없이 바로 패스
                    success_count += 1
                    progress_bar.progress((idx + 1) / total_selected)
                    continue
            
            # 신규 요약 진행
            # 1. 자막 다운로드 시도
            transcript = get_transcript(v_id)
            
            summary = None
            if transcript:
                # 자막 기반 요약 진행 (Gemini 3)
                summary = summarize_text(transcript, v_title)
            else:
                # 자막이 없는 경우 오디오 다운로드 시도
                status_text.text(f"자막 없음 - 오디오 다운로드 중: {v_title[:12]}...")
                audio_path = download_audio_only(v_id)
                
                if audio_path:
                    status_text.text(f"오디오 분석 및 요약 중: {v_title[:12]}...")
                    summary = summarize_audio(audio_path, v_title)
                    
                    # 임시 파일 즉시 청소
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception as e:
                        print(f"오디오 파일 임시 청소 실패: {e}")
            
            # 최종 요약 결과 판단 및 안전 저장
            if summary and "요약 실패" not in summary and "오디오 요약 실패" not in summary:
                save_summary(video, summary)
                success_count += 1
            else:
                # 오류 기록 남김 (무한 반복 방지)
                save_summary(video, f"요약 생성 중 에러가 발생했습니다: {summary or '알 수 없는 오류'}")
                
            progress_bar.progress((idx + 1) / total_selected)
            
        status_text.text(f"요약 완료! ({success_count}/{total_selected} 성공)")
        
        # 버튼을 눌러 요약 처리가 끝난 비디오 ID 목록만 우측 화면에 렌더링되도록 세션에 저장
        st.session_state.displayed_video_ids = selected_video_ids
        
        # Streamlit 세션 강제 갱신 트리거
        st.rerun()

# ------------------------------------------------------------------
# 우측 메인 화면 렌더링
# ------------------------------------------------------------------
st.title("최신 영상 요약")

# 조건부 렌더링: 사용자가 체크 후 요약을 클릭한 경우에만 요약 카드를 띄움
if not st.session_state.displayed_video_ids:
    st.info("💡 왼쪽 사이드바에서 원하는 최신 영상을 체크한 후, **'선택한 영상 요약하기'** 버튼을 누르시면 요약 결과가 이곳에 출력됩니다!")
else:
    st.markdown("선택하신 최신 동영상의 AI 요약 분석 결과입니다.")
    
    # 세션에 저장된 displayed_video_ids 에 해당하는 요약본만 파일에서 로드
    displayed_summaries = []
    for v_id in st.session_state.displayed_video_ids:
        data = get_summary(v_id)
        if data:
            displayed_summaries.append(data)
            
    # 최신 날짜순으로 재정렬하여 출력
    displayed_summaries.sort(key=lambda x: x['video']['published_at'], reverse=True)
    
    if not displayed_summaries:
        st.warning("선택된 영상들 중 표시할 수 있는 유효한 요약 데이터가 없습니다.")
    else:
        # 필터 기능 구현 (현재 화면에 출력된 요약 리스트 기준)
        channels = list(set([s['video']['channel_name'] for s in displayed_summaries]))
        selected_channel = st.selectbox("채널 필터", ["전체 보기"] + channels)
        
        # 카드 형태로 리스트 출력
        for item in displayed_summaries:
            video = item['video']
            summary = item['summary']
            
            # 채널 필터 적용
            if selected_channel != "전체 보기" and video['channel_name'] != selected_channel:
                continue
                
            with st.container():
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video['thumbnail_url'], use_container_width=True)
                    
                with col2:
                    # 코너명이 있으면 예쁜 뱃지로 출력
                    corner_badge = f"🧩 **{video['corner_name']}**" if video.get('corner_name') else ""
                    
                    st.subheader(video['title'])
                    st.markdown(f"**📺 {video['channel_name']}** | 📅 {video['published_at'][:10]} | {corner_badge}")
                    st.markdown(f"[➡️ YouTube에서 원본 영상 보기]({video['video_url']})")
                    
                # 요약 내용 토글
                with st.expander("📝 AI 영상 요약 내용 (Gemini 3)", expanded=True):
                    st.markdown(summary)
                    
                st.divider()
