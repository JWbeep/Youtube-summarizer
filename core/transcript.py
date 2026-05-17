from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# youtube-transcript-api v1.x 에서는 인스턴스를 생성해서 사용
_api = YouTubeTranscriptApi()

def get_transcript(video_id):
    """
    주어진 YouTube 비디오 ID의 자막을 추출합니다.
    한국어(ko)를 최우선으로, 없으면 영어(en) 또는 자동 생성 자막을 시도합니다.
    (youtube-transcript-api v1.x 호환)
    """
    try:
        # 사용 가능한 자막 목록 가져오기 (v1.x: 인스턴스 메서드 사용)
        transcript_list = _api.list(video_id)
        
        transcript = None
        
        # 1. 한국어 수동 자막 시도
        try:
            transcript = transcript_list.find_manually_created_transcript(['ko'])
            print(f"[{video_id}] 한국어 수동 자막을 찾았습니다.")
        except Exception:
            pass
        
        # 2. 한국어 자동 생성 자막 시도
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(['ko'])
                print(f"[{video_id}] 한국어 자동 생성 자막을 찾았습니다.")
            except Exception:
                pass

        # 3. 영어 자막을 한국어로 번역 시도
        if transcript is None:
            try:
                en_transcript = transcript_list.find_transcript(['en'])
                transcript = en_transcript.translate('ko')
                print(f"[{video_id}] 영어 자막을 한국어로 번역했습니다.")
            except Exception:
                pass

        # 4. 아무 언어 자막이나 찾아서 한국어로 번역
        if transcript is None:
            try:
                first_transcript = list(transcript_list)[0]
                transcript = first_transcript.translate('ko')
                print(f"[{video_id}] {first_transcript.language} 자막을 한국어로 번역했습니다.")
            except Exception:
                pass

        if transcript is None:
            print(f"[{video_id}] 사용 가능한 자막이 없습니다.")
            return None

        # 자막 데이터 가져오기 (v1.x: fetch()는 FetchedTranscript 객체 반환)
        fetched = transcript.fetch()

        # TextFormatter로 텍스트 추출
        formatter = TextFormatter()
        text = formatter.format_transcript(fetched)

        # 줄바꿈을 공백으로 변경하여 하나의 긴 텍스트로 만들기
        text = text.replace('\n', ' ')
        return text
        
    except Exception as e:
        print(f"[{video_id}] 자막을 가져올 수 없습니다. 원인: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    # 테스트 실행
    test_video_id = "Epn7943q2hg"
    print(f"--- 테스트: 비디오 {test_video_id} 자막 추출 ---")
    
    text = get_transcript(test_video_id)
    if text:
        print(f"추출 성공! 길이: {len(text)}자")
        print(f"미리보기: {text[:300]}...")
    else:
        print("자막 추출 실패")
