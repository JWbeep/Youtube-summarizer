import json
import os

CACHE_DIR = "data/summaries"

def _ensure_dir():
    """요약 저장 폴더가 없으면 생성합니다."""
    os.makedirs(CACHE_DIR, exist_ok=True)

def _get_path(video_id):
    return os.path.join(CACHE_DIR, f"{video_id}.json")

def save_summary(video_data, summary_text):
    """
    영상 정보와 생성된 요약 텍스트를 JSON 파일로 저장합니다.
    (이미 존재하면 덮어씁니다)
    """
    _ensure_dir()
    path = _get_path(video_data['video_id'])
    
    data_to_save = {
        "video": video_data,
        "summary": summary_text
    }
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[{video_data['video_id']}] 저장 실패: {e}")
        return False

def get_summary(video_id):
    """
    저장된 요약 JSON 파일을 불러옵니다.
    없으면 None을 반환합니다.
    """
    path = _get_path(video_id)
    if not os.path.exists(path):
        return None
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[{video_id}] 불러오기 실패: {e}")
        return None

def has_summary(video_id):
    """해당 비디오의 요약이 이미 저장되어 있는지 확인합니다."""
    return os.path.exists(_get_path(video_id))
