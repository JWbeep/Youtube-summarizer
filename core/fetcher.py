import os
import urllib.parse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import yaml
import sys

# Windows에서 이모지(⚡ 등) 출력 시 UnicodeEncodeError 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# 환경 변수 로드
load_dotenv()

def extract_playlist_id(url_or_id):
    """URL에서 재생목록 ID를 추출하거나, 이미 ID인 경우 그대로 반환합니다."""
    if not url_or_id:
        return None
        
    # 이미 ID 형태인 경우 (http로 시작하지 않고 띄어쓰기 등 없는 문자열)
    if not url_or_id.startswith('http'):
        return url_or_id
        
    try:
        parsed_url = urllib.parse.urlparse(url_or_id)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        # list 파라미터가 있으면 가져옴
        if 'list' in query_params:
            return query_params['list'][0]
    except Exception as e:
        print(f"URL 파싱 오류: {e}")
        
    return url_or_id

def load_channels_config(config_path="config/channels.yaml"):
    """채널 설정 파일을 로드합니다."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('channels', [])
    except Exception as e:
        print(f"채널 설정 로드 오류: {e}")
        return []

def get_youtube_client():
    """YouTube Data API 클라이언트를 반환합니다."""
    # 함수 호출 시점에 API 키를 읽어야 st.secrets가 완전히 초기화된 상태임을 보장
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("YOUTUBE_DATA_API_KEY", st.secrets.get("YOUTUBE_API_KEY"))
    except Exception:
        pass
    
    if not api_key:
        api_key = os.getenv("YOUTUBE_DATA_API_KEY", os.getenv("YOUTUBE_API_KEY"))
    
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY가 설정되지 않았습니다. Streamlit Secrets 또는 .env 파일을 확인하세요.")
    
    return build('youtube', 'v3', developerKey=api_key)

# ------------------------------------------------------------------
# 🔍 유튜브 자동 검색 도우미 함수 (신규 추가)
# ------------------------------------------------------------------
def get_channel_id_by_name(youtube, channel_name):
    """채널 이름을 사용하여 유튜브 채널 고유 ID를 실시간으로 검색해 반환합니다."""
    try:
        request = youtube.search().list(
            q=channel_name,
            type='channel',
            part='id',
            maxResults=1
        )
        response = request.execute()
        items = response.get('items', [])
        if items:
            return items[0]['id']['channelId']
    except Exception as e:
        print(f"채널 ID 자동 검색 실패 ({channel_name}): {e}")
        # 에러 내용을 상위로 전달 (None 대신 에러 문자열 반환)
        return f"_SEARCH_ERROR_:{e}"
    return None

def get_playlist_id_by_name(youtube, channel_id, playlist_name):
    """지정된 채널 내부의 모든 재생목록을 훑어, 이름이 완전히 일치하거나 정화된 이름이 일치하는 재생목록 ID를 찾아냅니다."""
    import re
    
    def clean_text(text):
        # 한글, 영어, 숫자만 남기고 공백 및 특수문자, 이모지 전부 제거
        return re.sub(r'[^a-zA-Z0-9가-힣]', '', text)

    try:
        request = youtube.playlists().list(
            channelId=channel_id,
            part='snippet',
            maxResults=50
        )
        response = request.execute()
        playlists = response.get('items', [])
        
        # 1단계: 100% 완벽하게 일치하는 경우 우선 매칭 (공백 정리 포함)
        for pl in playlists:
            title = pl['snippet']['title'].strip()
            if title == playlist_name.strip():
                return pl['id']
                
        # 2단계: 특수문자, 이모지, 띄어쓰기를 전부 걷어낸 '정화 텍스트' 기준으로 100% 일치 비교 (예외 복구)
        target_cleaned = clean_text(playlist_name)
        for pl in playlists:
            title_cleaned = clean_text(pl['snippet']['title'])
            if title_cleaned == target_cleaned and len(target_cleaned) > 0:
                return pl['id']
                
    except Exception as e:
        print(f"재생목록 ID 자동 검색 실패 ({playlist_name}): {e}")
    return None


def get_channel_uploads_playlist_id(youtube, channel_id):
    """특정 채널의 '업로드' 재생목록 ID를 가져옵니다."""
    try:
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = request.execute()
        items = response.get('items', [])
        if not items:
            return None
        return items[0]['contentDetails']['relatedPlaylists']['uploads']
    except HttpError as e:
        print(f"YouTube API 채널 정보 조회 오류 ({channel_id}): {e}")
        return None

def fetch_latest_videos(youtube, playlist_id, max_results=5):
    """재생목록에서 최신 영상을 가져옵니다."""
    try:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=max_results
        )
        response = request.execute()
        return response.get('items', [])
    except HttpError as e:
        print(f"YouTube API 재생목록 항목 조회 오류 ({playlist_id}): {e}")
        return []

def fetch_videos_for_channels(progress_callback=None):
    """설정된 모든 활성 채널의 최신 영상을 수집하고 필터링하여 반환합니다. (ID 자동 검색 지원)"""
    channels = load_channels_config()
    if not channels:
        print("설정된 채널이 없습니다.")
        return []
        
    try:
        youtube = get_youtube_client()
    except Exception as e:
        print(f"YouTube 클라이언트 초기화 실패: {e}")
        # 에러 내용을 상위로 전달하기 위해 특수 문자열 반환
        return [{"_error": str(e)}]

    all_videos = []
    active_channels = [c for c in channels if c.get('active', True)]
    total_channels = len(active_channels)
    
    for idx, channel in enumerate(active_channels):
        channel_name = channel.get('name')
        channel_id = channel.get('channel_id')
        max_results = channel.get('max_results', 5)
        corners = channel.get('corners', [])
        
        # 콜백 호출 (Streamlit UI 진행 상태바 업데이트용)
        if progress_callback:
            progress_callback(idx, total_channels, f"[{idx+1}/{total_channels}] {channel_name} 수집 중...")
            
        print(f"[{channel_name}] 데이터 수집 중...")
        
        # 1. 채널 ID가 생략되어 있는 경우, 이름으로 채널 ID 자동 검색
        if not channel_id:
            print(f"  - 채널 ID가 생략되어 실시간 자동 검색을 수행합니다: '{channel_name}'")
            channel_id = get_channel_id_by_name(youtube, channel_name)
            if not channel_id:
                print(f"  - 채널 '{channel_name}'의 ID를 찾을 수 없어 수집을 건너뜁니다.")
                continue
            # 검색 에러가 있을 경우 에러 전파
            if isinstance(channel_id, str) and channel_id.startswith("_SEARCH_ERROR_:"):
                error_detail = channel_id.replace("_SEARCH_ERROR_:", "")
                return [{"_error": f"채널 '{channel_name}' 검색 실패: {error_detail}"}]
            print(f"  - 채널 ID 조회 성공: '{channel_name}' -> ID: {channel_id}")
            
        if corners:
            # 코너별로 별도로 처리 (재생목록 ID가 지정되어 있거나 자동 검색할 경우)
            for corner in corners:
                corner_name = corner.get('name', '이름 없음')
                raw_playlist_val = corner.get('playlist_id')
                
                # URL이 들어오든, ID가 들어오든 자동으로 ID만 추출
                playlist_id = extract_playlist_id(raw_playlist_val)
                
                # 2. 재생목록 ID가 생략되어 있거나 비어있는 경우, 이름으로 재생목록 100% 완전일치 자동 검색
                if not playlist_id or playlist_id in ["여기에_재생목록_ID_입력", "여기에_URL을_붙여넣으세요"]:
                    print(f"  - 코너 '{corner_name}'의 재생목록 ID가 생략되어 완전 일치 자동 검색을 수행합니다...")
                    playlist_id = get_playlist_id_by_name(youtube, channel_id, corner_name)
                    
                if playlist_id:
                    print(f"  - 코너({corner_name}) 재생목록에서 수집 시작... (ID: {playlist_id})")
                    corner_items = fetch_latest_videos(youtube, playlist_id, max_results)
                    for item in corner_items:
                        item['corner_name'] = corner_name
                        _process_and_add_video(item, channel_name, channel_id, all_videos)
                else:
                    print(f"  - 코너('{corner_name}')의 정식 재생목록을 찾을 수 없어 수집을 건너뜁니다.")
        else:
            # 코너가 없는 일반 채널 (기존 방식 유지)
            playlist_id = get_channel_uploads_playlist_id(youtube, channel_id)
            if not playlist_id:
                print(f"  - 통째 수집: 재생목록 ID를 찾을 수 없습니다. (ID: {channel_id})")
                continue
                
            latest_items = fetch_latest_videos(youtube, playlist_id, max_results)
            for item in latest_items:
                item['corner_name'] = None
                _process_and_add_video(item, channel_name, channel_id, all_videos)
        if progress_callback:
            progress_callback(idx + 1, total_channels, f"[{idx+1}/{total_channels}] {channel_name} 완료!")
            
    return all_videos

def _process_and_add_video(item, channel_name, channel_id, all_videos):
    """API 결과를 통일된 포맷으로 변환하여 리스트에 추가합니다."""
    video_id = item['snippet']['resourceId']['videoId']
    title = item['snippet']['title']
    published_at = item['snippet']['publishedAt']
    thumbnail_url = item['snippet']['thumbnails'].get('high', item['snippet']['thumbnails'].get('default'))['url']
    corner_name = item.get('corner_name')
    
    video_data = {
        'video_id': video_id,
        'channel_name': channel_name,
        'channel_id': channel_id,
        'title': title,
        'published_at': published_at,
        'thumbnail_url': thumbnail_url,
        'video_url': f"https://www.youtube.com/watch?v={video_id}",
        'corner_name': corner_name
    }
    all_videos.append(video_data)
    print(f"  - 수집 완료: {title} ({corner_name if corner_name else '코너 분류 없음'})")
            
    return all_videos

if __name__ == "__main__":
    # 테스트 실행
    print("--- 테스트: YouTube 채널 최신 영상 목록 가져오기 ---")
    videos = fetch_videos_for_channels()
    for v in videos:
        print(f"[{v['channel_name']}] {v['title']} ({v['video_url']})")
