# make_picture_to_meal.py
import os, json, time, math, random, datetime
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv
# 선택적 임포트 - 라이브러리가 없어도 애플리케이션이 실행되도록 함
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("경고: openai가 설치되지 않았습니다. 이미지 생성 기능이 제한됩니다.")

# .env 로드
load_dotenv()
load_dotenv(find_dotenv(usecwd=True))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    print("경고: 환경 변수 OPENAI_API_KEY가 비어 있습니다. 이미지 생성 기능이 제한됩니다.")

# OpenAI 클라이언트
client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI 클라이언트 초기화 실패: {e}")
        client = None

# --------------------------------
# 설정
# --------------------------------
# 이미지 모델/파라미터는 환경에 맞게 교체
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")  # 예시용
OUT_DIR = os.getenv("MEAL_PIC_OUT_DIR", "meal_pics")
os.makedirs(OUT_DIR, exist_ok=True)

def now_seed() -> int:
    return int(time.time() * 1000) % 10**9

def build_image_prompt(title: str, meal_key: str, seed: int) -> str:
    """
    한국 음식 메뉴 타이틀을 기반으로 상징 이미지를 만드는 프롬프트.
    메인과 사이드를 함께 보여주는 정갈한 상차림, 과도한 텍스트 대신 음식 묘사 중심.
    """
    # 타이틀에서 메인/사이드 추출 힌트(쉼표/와 구분)
    # 모델이 알아서 해석하도록 설명적 지시 포함
    base = f"""
한국 한 끼 상차림 일러스트. 단정한 탁상 위에 '{title}'의 메인 요리와 대표 사이드가 함께 보이게 구성.
- 색감: 은은하고 따뜻한 자연광
- 구도: 45도 상부 앵글, 정갈한 식기
- 스타일: 사실적인 일러스트와 사진 사이, 선명한 질감
- 배경: 깨끗한 무지 또는 아주 흐린 주방 분위기
- 텍스트: 이미지 내부에 텍스트는 삽입하지 않음
- 포커스: 메인 요리를 가장 크게, 사이드는 작게 보조 배치
- 랜덤 시드: {seed}
- 끼니: {meal_key}
"""
    return base.strip()

def image_file_name(title: str, meal_key: str) -> str:
    # 파일명 안전화
    safe_title = "".join([c if c.isalnum() else "_" for c in title])[:40]
    return f"{meal_key}_{safe_title}.png"

def generate_image_from_prompt(prompt: str, size: str = "1024x1024", quality: str = "high") -> bytes:
    """
    이미지 생성 호출.
    주의: 실제 이미지 생성 API는 사용하는 환경/모델에 따라 메서드명이 다를 수 있음.
    OpenAI 최신 문서에 맞게 수정 필요.
    """
    if not client:
        raise RuntimeError("OpenAI 클라이언트가 설정되지 않았습니다.")
    
    try:
        # 아래는 예시 형식. 실제 SDK의 이미지 메서드/필드는 환경에 맞게 교체.
        # 공식 문서: platform.openai.com/docs/api-reference (엔드포인트/파라미터 확인)
        result = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        # SDK에 따라 b64_json 또는 URL 등을 반환할 수 있음
        if hasattr(result, "data") and result.data and hasattr(result.data[0], "b64_json"):
            import base64
            return base64.b64decode(result.data[0].b64_json)
        # URL 응답인 경우 직접 다운로드 필요
        if hasattr(result, "data") and result.data and hasattr(result.data[0], "url"):
            import requests
            url = result.data[0].url
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
        raise RuntimeError("이미지 생성 응답 형식이 예상과 다릅니다.")
    except Exception as e:
        raise RuntimeError(f"이미지 생성 중 오류 발생: {e}")

def save_image(png_bytes: bytes, path: str):
    with open(path, "wb") as f:
        f.write(png_bytes)

def load_plan_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def make_pictures_for_meals(plan_json_path: str, variability: float = 0.3):
    """
    plan_json_path: recommendation_타임스탬프.json 경로
    variability: 0.0~1.0, 클수록 더 다양한 스타일(시드 흔들기)
    """
    data = load_plan_json(plan_json_path)

    # 끼니별 title 추출
    meals = []
    for meal_key in ("breakfast", "lunch", "dinner"):
        title = ((data.get(meal_key) or {}).get("title") or "").strip()
        if not title:
            continue
        meals.append((meal_key, title))

    if not meals:
        print("생성할 제목이 없습니다.")
        return

    # 공통 베이스 시드 + 끼니별 변주
    base_seed = now_seed()
    for idx, (meal_key, title) in enumerate(meals):
        # 변주를 위해 베이스 시드에 가중 무작위 더함
        local_seed = (base_seed * (idx + 3) + int(random.random() * 10**6)) % 10**9
        # variability 비율만큼 추가 난수 섞기
        if variability > 0:
            jitter = int(variability * 10**6 * random.random())
            local_seed = (local_seed + jitter) % 10**9

        prompt = build_image_prompt(title=title, meal_key=meal_key, seed=local_seed)
        print(f"[{meal_key}] title='{title}', seed={local_seed}")

        img_bytes = generate_image_from_prompt(prompt, size="1024x1024", quality="high")
        out_name = image_file_name(title, meal_key)
        out_path = os.path.join(OUT_DIR, out_name)
        save_image(img_bytes, out_path)
        print(f"[saved] {out_path}")

if __name__ == "__main__":
    # 가장 최근 recommendation_*.json을 자동 탐색하거나, 직접 경로를 인자로 넘기도록 구현 가능
    # 여기서는 예시로 최신 파일을 탐색
    out_dir = "out"
    latest = None
    latest_mtime = -1
    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            if fn.startswith("recommendation_") and fn.endswith(".json"):
                path = os.path.join(out_dir, fn)
                mtime = os.path.getmtime(path)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest = path

    if latest:
        make_pictures_for_meals(latest, variability=0.4)
    else:
        print("out 디렉토리에서 recommendation_*.json 파일을 찾지 못했습니다.")