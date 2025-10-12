# make_picture_to_meal.py
import os, json, time, math, random, datetime
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv
import config
import re
import requests
import traceback
# 선택적 임포트 - 라이브러리가 없어도 애플리케이션이 실행되도록 함
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("경고: openai가 설치되지 않았습니다. 이미지 생성 기능이 제한됩니다.")

# .env 로드
load_dotenv(override=True)
load_dotenv(find_dotenv(usecwd=True))

OPENAI_API_KEY = config.OPENAI_API_KEY
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


import time


def make_pictures_for_meals(plan_json_path: str, variability: float = 0.2) -> dict:
    saved_paths = {}

    with open(plan_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for meal_key in ("breakfast", "lunch", "dinner"):
        meal_info = data.get(meal_key)
        if not meal_info or not isinstance(meal_info, dict):
            continue

        title = meal_info.get("title", "").strip()
        if not title:
            continue

        try:
            # DALL-E API 호출
            response = client.images.generate(
                model="dall-e-3",
                prompt=f"한국 음식: {title}, 식욕을 돋우는 아름다운 음식 사진, 고화질, 레스토랑 퀄리티",
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_data = requests.get(image_url).content

            sanitized_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_").replace(",", "")
            out_path = os.path.join(OUT_DIR, f"{meal_key}_{sanitized_title}.png")

            with open(out_path, 'wb') as img_file:
                img_file.write(image_data)

            print(f"[saved] {out_path}")
            saved_paths[meal_key] = out_path

            # 각 이미지 생성 후 1초 대기 (rate limit 방지)
            time.sleep(1)

        except Exception as e:
            print(f"! {meal_key} 이미지 생성 실패: {e}")
            traceback.print_exc()
            saved_paths[meal_key] = None

    return saved_paths

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