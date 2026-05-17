import yt_dlp
import os

def download_audio_only(video_id, output_dir="temp_audio"):
    """
    유튜브 영상 ID를 받아 해당 영상의 오디오만 m4a 포맷으로 다운로드합니다.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = os.path.join(output_dir, f"{video_id}.m4a")
    
    # 이미 파일이 존재하면 다운로드 건너뜀
    if os.path.exists(output_path):
        return output_path

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f"{video_id}.%(ext)s"),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
        # FFmpeg가 없어도 동작하기 위해 최대한 기본 설정을 활용 (yt-dlp는 m4a는 별도 인코더 없이도 추출 가능할 때가 많음)
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 실제 생성된 파일 경로 확인 (extension이 다를 수 있으므로 체크)
        if os.path.exists(output_path):
            return output_path
        
        # .m4a가 아니더라도 생성된 파일 찾기
        for f in os.listdir(output_dir):
            if f.startswith(video_id):
                return os.path.abspath(os.path.join(output_dir, f))
                
        return None
    except Exception as e:
        print(f"오디오 다운로드 오류 ({video_id}): {e}")
        return None

if __name__ == "__main__":
    # 테스트 코드
    test_id = "8sF5a7xa32w" # 홍장원의 불앤베어 최신 영상 중 하나
    print(f"--- 오디오 추출 테스트 ({test_id}) ---")
    path = download_audio_only(test_id)
    if path:
        print(f"성공: {path}")
    else:
        print("실패")
