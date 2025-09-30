"""
Image.py

이미지 속 음식을 항목별로 인식 → 각 항목의 kcal/탄/단/지(g) 추정 → JSON 반환 및 저장
- OpenAI API (예: gpt-4o)를 사용합니다.
- 로컬 이미지 파일을 바로 base64로 인코딩하여 전송합니다.
- 모델이 반환한 JSON을 검증하고, 총합(total)만 포함한 JSON을 <입력파일명>.nutrition.json 으로 저장합니다.

백엔드 연동(예: FastAPI) 예시:
    from Image import analyze_image_bytes
    @app.post("/analyze")
    async def analyze(image: UploadFile = File(...)):
        data = await image.read()
        return analyze_image_bytes(data, filename=image.filename)

사용법:
  python Image.py --image ./sample.jpg \
                                --model gpt-4o \
                                --out ./result.json

사전 준비:
  - 환경변수 OPENAI_API_KEY 설정 필요
"""
from __future__ import annotations

from dotenv import load_dotenv, find_dotenv

__all__ = [
    "analyze_image_with_openai",
    "analyze_image_bytes",
]
import argparse
import json
import os
import re
import sys
from typing import Any, Dict

from typing import Tuple
import config


import base64
from openai import OpenAI

# .env 로드
load_dotenv(override=True)
load_dotenv(find_dotenv(usecwd=True))
# =====================
# Prompt Templates
# =====================
SYSTEM_PROMPT = (
    "다음 규칙을 엄격히 따르세요.\n"
    "1) 입력 이미지를 분석해 접시에 있는 각각의 음식 항목을 분리해 이름을 정합니다.\n"
    "2) 각 항목별로 단일 1인분 기준의 대략적 열량(kcal)과 탄수화물/단백질/지방(g)을 추정합니다.\n"
    "3) 모든 수치는 숫자만(단위 없음)으로 표기하고 g 단위로 가정합니다.\n"
    "4) 결과는 유효한 JSON만 출력합니다. 추가 설명 금지.\n"
    "5) JSON의 키는 영어로, 항목 내부의 name_ko 값은 한국어로 표기합니다.\n"
    "6) 불확실하면 Unknown 항목을 최소한으로 추가하고 수치는 0으로 둡니다(남발 금지).\n"
    "7) 한 접시에 여러 음식이 섞여 있으면 가능한 한 대표 항목으로 분해합니다.\n"
    "8) 총합(kcal, carb_g, protein_g, fat_g)을 별도로 제공합니다.\n"
    "9) 소수점은 한 자리까지 표기합니다(필요 시 반올림).\n"
    "10) 응답은 오직 유효한 JSON만, 코드펜스/주석/설명 금지.\n"
    "11) 출력은 items/total의 kcal/carb_g/protein_g/fat_g만 포함합니다. 다른 필드는 절대 출력하지 마세요.\n"
    "12) 응답 전 내부적으로 다음 체크리스트로 스스로 검증하되, 체크리스트 내용은 출력하지 않습니다: 색(흰/노란/빨강 계열), 질감(바삭/유광/반투명), 형태(큐브/반달/면류), 소스 색(춘장=검은색/김치양념=주황~빨강), 접시 맥락(짜장면+탕수육 세트=단무지/양파/춘장).\n"
)

USER_PROMPT_TEMPLATE = (
    "이미지에 보이는 모든 음식을 항목별로 식별하고, 아래 스키마로만 응답하세요.\n"
    "- 각 항목 key: 영어 소문자 스네이크케이스(예: galbijjim, white_rice, kimchi)\n"
    "- 값 오브젝트 필드:\n"
    "  - name_ko: 한국어 음식명\n"
    "  - kcal: 숫자\n"
    "  - carb_g: 숫자\n"
    "  - protein_g: 숫자\n"
    "  - fat_g: 숫자\n"
    "- total: 모든 항목 합계(kcal, carb_g, protein_g, fat_g)\n\n"
    "반드시 아래 JSON 형식만 출력하세요:\n"
    "{\n"
    '  "items": {\n'
    '    "<english_key>": {\n'
    '      "name_ko": "<korean name>",\n'
    '      "kcal": <number>,\n'
    '      "carb_g": <number>,\n'
    '      "protein_g": <number>,\n'
    '      "fat_g": <number>\n'
    "    }\n"
    "  },\n"
    '  "total": {\n'
    '    "kcal": <number>,\n'
    '    "carb_g": <number>,\n'
    '    "protein_g": <number>,\n'
    '    "fat_g": <number>\n'
    "  }\n"
    "}\n\n"
    "이미지 설명: {image_caption}\n"
)

USER_PROMPT_DETAIL2 = (
    "가능하면 아래 '추가 필드'를 각 항목에 포함하세요:\n"
    "- portion_g: 추정 1인분 그램 수 (숫자)\n"
    "- confidence: 인식 신뢰도 0~1 (숫자)\n"
    "- sodium_mg: 나트륨 (숫자)\n"
    "- sugar_g: 당류 (숫자)\n"
    "- fiber_g: 식이섬유 (숫자)\n"
    "- serving_desc: 분량/용기 설명 (문자열)\n"
    "total에도 위 필드가 존재하면 합계를 제공합니다.\n"
)

USER_PROMPT_DETAIL3 = (
    "가능하면 각 항목에 bbox: [x, y, w, h] (0~1 정규화, 좌상단 기준) 를 포함하세요.\n"
)

DISAMBIGUATION_BLOCK = (
    "[DISAMBIGUATION — Korean–Chinese meal cues]\n"
    "A) Main-dish prior: If you detect jjajangmyeon or tangsuyuk, typical sides are: danmuji (yellow pickled radish), raw onion cubes, and chunjang (black bean paste). Kimchi (kkakdugi) is uncommon in this set.\n"
    "B) Color/texture rules for radish/onion/kimchi:\n"
    "  - danmuji: bright yellow, glossy, crescent or half-moon slices.\n"
    "  - raw onion: white to off-white, semi-translucent, sharp edges; served dry next to chunjang.\n"
    "  - kkakdugi: orange/red due to gochugaru; seasoning visible; often wet with kimchi juice; pores on radish surface.\n"
    "C) If a white cube side with no red/orange seasoning is observed, classify as raw onion (not kkakdugi).\n"
    "D) If confidence between onion vs kkakdugi is low, default to onion unless red seasoning is clearly visible.\n"
    "E) Never invent kimchi when black bean paste and danmuji are present without red seasoning.\n"
    "F) Do not output alternatives or explanations—apply these rules silently and return only the JSON.\n"
)

VISION_RULES_BLOCK = (
    "[VISION CUES — general]\n"
    "Rice vs tofu vs radish/onion: white rice=granular grains; tofu=smooth rectangular blocks with pores; onion=layered, semi-translucent white; radish=opaque white with fine pores, often in broth/kimchi.\n"
    "Fried vs boiled: fried has irregular golden/brown crust, specular highlights; boiled/steamed shows matte, uniform surface.\n"
    "Sauce hues: gochujang/kimchi=orange/red with visible flakes; chunjang=dark brown/black gloss; soy-braise=dark brown with sesame/scallion.\n"
    "Noodle cues: cylindrical strands, uniform thickness, often glossy with sauce pooling.\n"
)

# =====================
# Helpers
# =====================


def extract_json(text: str) -> str:
    """모델이 실수로 텍스트를 덧붙였을 경우, JSON 블록만 뽑아냅니다."""
    # 먼저 코드블록 안의 JSON을 시도
    codeblock = re.search(r"```(?:json)?\n(.*?)\n```", text, re.S | re.I)
    if codeblock:
        return codeblock.group(1).strip()
    # 중괄호 범위를 최대한 보수적으로 추출
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()
    return text.strip()


def clean_json_text(s: str) -> str:
    """LLM가 생성한 JSON 유사 텍스트를 실제 JSON으로 가까이 정리.
    - 스마트쿼트 → 일반 쿼트
    - 코드펜스/마크다운 제거
    - // 주석, /* */ 주석 제거
    - 닫기 직전의 꼬리 콤마 제거
    """
    if not s:
        return s
    # 코드펜스 제거
    s = re.sub(r"```(?:json)?\n|```", "", s, flags=re.I)
    # 스마트 쿼트 → 일반 쿼트
    s = (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    # 주석 제거
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"(^|\n)\s*//.*?(?=\n|$)", "\n", s)
    # 꼬리 콤마 제거
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # 공백 정리
    return s.strip()


def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """필수 스키마 최소 검증 및 숫자형 강제 변환/반올림(소수점 1자리)"""

    def to_num(x: Any) -> float:
        try:
            return round(float(x), 1)
        except Exception:
            return 0.0

    if not isinstance(payload, dict):
        raise ValueError("최상위 구조가 dict(JSON object)가 아닙니다.")

    items = payload.get("items", {})
    total = payload.get("total", {})
    if not isinstance(items, dict) or not isinstance(total, dict):
        raise ValueError("'items'와 'total' 키가 필요합니다.")

    clean_items: Dict[str, Any] = {}
    for k, v in items.items():
        if not isinstance(v, dict):
            continue
        name_ko = v.get("name_ko", "Unknown")
        kcal = to_num(v.get("kcal", 0))
        carb_g = to_num(v.get("carb_g", 0))
        protein_g = to_num(v.get("protein_g", 0))
        fat_g = to_num(v.get("fat_g", 0))

        # optional fields
        portion_g_val = v.get("portion_g", None)
        confidence_val = v.get("confidence", None)
        sodium_mg_val = v.get("sodium_mg", None)
        sugar_g_val = v.get("sugar_g", None)
        fiber_g_val = v.get("fiber_g", None)
        serving_desc_val = v.get("serving_desc", None)
        bbox_val = v.get("bbox", None)

        item_obj = {
            "name_ko": name_ko,
            "kcal": kcal,
            "carb_g": carb_g,
            "protein_g": protein_g,
            "fat_g": fat_g,
        }
        if portion_g_val is not None:
            item_obj["portion_g"] = to_num(portion_g_val)
        if confidence_val is not None:
            item_obj["confidence"] = to_num(confidence_val)
        if sodium_mg_val is not None:
            item_obj["sodium_mg"] = to_num(sodium_mg_val)
        if sugar_g_val is not None:
            item_obj["sugar_g"] = to_num(sugar_g_val)
        if fiber_g_val is not None:
            item_obj["fiber_g"] = to_num(fiber_g_val)
        if isinstance(serving_desc_val, str) and serving_desc_val.strip():
            item_obj["serving_desc"] = serving_desc_val.strip()
        if isinstance(bbox_val, (list, tuple)) and len(bbox_val) == 4:
            try:
                item_obj["bbox"] = [round(float(x), 4) for x in bbox_val]
            except Exception:
                pass

        clean_items[k] = item_obj

    # total 강제 보정: 항목 합계를 재계산하여 신뢰성 향상
    sum_kcal = round(sum(v["kcal"] for v in clean_items.values()), 1)
    sum_carb = round(sum(v["carb_g"] for v in clean_items.values()), 1)
    sum_prot = round(sum(v["protein_g"] for v in clean_items.values()), 1)
    sum_fat = round(sum(v["fat_g"] for v in clean_items.values()), 1)

    # optional sums if present in any item
    has_sodium = any("sodium_mg" in v for v in clean_items.values())
    has_sugar = any("sugar_g" in v for v in clean_items.values())
    has_fiber = any("fiber_g" in v for v in clean_items.values())
    sum_sodium = (
        round(sum(v.get("sodium_mg", 0) for v in clean_items.values()), 1)
        if has_sodium
        else None
    )
    sum_sugar = (
        round(sum(v.get("sugar_g", 0) for v in clean_items.values()), 1)
        if has_sugar
        else None
    )
    sum_fiber = (
        round(sum(v.get("fiber_g", 0) for v in clean_items.values()), 1)
        if has_fiber
        else None
    )

    clean_total = {
        "kcal": to_num(total.get("kcal", sum_kcal)) if total else sum_kcal,
        "carb_g": to_num(total.get("carb_g", sum_carb)) if total else sum_carb,
        "protein_g": to_num(total.get("protein_g", sum_prot)) if total else sum_prot,
        "fat_g": to_num(total.get("fat_g", sum_fat)) if total else sum_fat,
    }
    if has_sodium:
        clean_total["sodium_mg"] = (
            to_num(total.get("sodium_mg", sum_sodium)) if total else sum_sodium
        )
    if has_sugar:
        clean_total["sugar_g"] = (
            to_num(total.get("sugar_g", sum_sugar)) if total else sum_sugar
        )
    if has_fiber:
        clean_total["fiber_g"] = (
            to_num(total.get("fiber_g", sum_fiber)) if total else sum_fiber
        )

    return {"items": clean_items, "total": clean_total}


# =====================
# Image base64 helper
# =====================


def _read_image_b64(image_path: str) -> Tuple[str, str]:
    lower = image_path.lower()
    if lower.endswith(".png"):
        mime = "image/png"
    elif lower.endswith(".webp"):
        mime = "image/webp"
    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
        mime = "image/jpeg"
    else:
        mime = "application/octet-stream"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return mime, b64


# =====================
# MIME guesser for bytes API
# =====================


def _guess_mime_from_filename(filename: str) -> str:
    lower = (filename or "").lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


# =====================
# Core OpenAI Vision Call (b64 input)
# =====================


def _analyze_b64_core(
    mime: str,
    b64: str,
    *,
    model: str = "gpt-4o",
    image_caption: str = "",
    verbose: bool = False,
    debug: bool = False,
    detail: int = 1,
) -> Dict[str, Any]:
    # Build prompts (reuse existing constants)
    system_prompt = (
        SYSTEM_PROMPT + "\n" + DISAMBIGUATION_BLOCK + "\n" + VISION_RULES_BLOCK
    )
    base_up = USER_PROMPT_TEMPLATE.split("이미지 설명:")[0].rstrip()
    extras = []
    if detail >= 2:
        extras.append(USER_PROMPT_DETAIL2)
    if detail >= 3:
        extras.append(USER_PROMPT_DETAIL3)
    user_prompt = (
        base_up
        + "\n"
        + ("\n".join(extras) if extras else "")
        + f"\n이미지 설명: {image_caption}\n"
    )

    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise EnvironmentError(
            "환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다. 'export OPENAI_API_KEY=...' 후 다시 실행하세요."
        )
    client = OpenAI(api_key=api_key)

    if verbose:
        print(f"[INFO] 모델 호출: {model}")

    # OpenAI Responses API with image input and JSON forcing
    try:
        resp = client.responses.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.0,
            max_output_tokens=1024,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "input_image",
                            "image": {
                                "format": mime.split("/")[-1],
                                "b64": b64,
                            },
                        },
                    ],
                },
            ],
        )
        try:
            text = resp.output_text or ""
        except Exception:
            text = getattr(resp, "output", "") or getattr(resp, "content", "") or ""
    except TypeError as e:
        # Older SDKs may not support `Responses` or `response_format`.
        if verbose:
            print(
                "[INFO] SDK가 Responses.response_format을 지원하지 않아 Chat Completions로 폴백합니다."
            )
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            },
        ]
        try:
            chat_resp = client.chat.completions.create(
                model=(model or "gpt-4o-mini"),
                messages=chat_messages,
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        except TypeError:
            # Very old SDKs: no response_format supported; rely on prompt-only JSON
            chat_resp = client.chat.completions.create(
                model=(model or "gpt-4o-mini"),
                messages=chat_messages,
                temperature=0.0,
                max_tokens=1024,
            )
        text = chat_resp.choices[0].message.content or ""

    if debug:
        print("[DEBUG] 1차 응답 원본:")
        print(text)

    raw_json = extract_json(text)
    cleaned = clean_json_text(raw_json)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e1:
        if debug:
            print(
                f"[WARN] 1차 JSON 파싱 실패: {e1}\n---RAW BEGIN---\n{raw_json}\n---RAW END---"
            )
        # Retry by explicitly re-prompting for JSON only
        resp2 = client.responses.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.0,
            max_output_tokens=1024,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                            + "\nReturn ONLY valid JSON. No code fences, no comments, no trailing commas.",
                        },
                        {
                            "type": "input_image",
                            "image": {"format": mime.split("/")[-1], "b64": b64},
                        },
                    ],
                },
            ],
        )
        text2 = getattr(resp2, "output_text", "") or ""
        if debug:
            print("[DEBUG] 2차 응답 원본:")
            print(text2)
        cleaned2 = clean_json_text(extract_json(text2))
        parsed = json.loads(cleaned2)

    validated = validate_payload(parsed)

    if detail == 1:
        for k, v in list(validated.get("items", {}).items()):
            for extra_key in [
                "portion_g",
                "confidence",
                "sodium_mg",
                "sugar_g",
                "fiber_g",
                "serving_desc",
                "bbox",
            ]:
                if extra_key in v:
                    v.pop(extra_key, None)
        for extra_key in ["sodium_mg", "sugar_g", "fiber_g"]:
            validated.get("total", {}).pop(extra_key, None)

    return validated


# =====================
# OpenAI Vision Call
# =====================


def analyze_image_with_openai(
    image_path: str,
    model: str = "gpt-4o",
    image_caption: str = "",
    verbose: bool = False,
    debug: bool = False,
    detail: int = 1,
) -> Dict[str, Any]:
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise EnvironmentError(
            "환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다. 'export OPENAI_API_KEY=...' 후 다시 실행하세요."
        )

    # MIME + base64 from file path
    mime, b64 = _read_image_b64(image_path)
    if verbose:
        print(f"[INFO] 이미지 로드: {image_path} ({mime})")
    return _analyze_b64_core(
        mime,
        b64,
        model=model,
        image_caption=image_caption,
        verbose=verbose,
        debug=debug,
        detail=detail,
    )


# =====================
# Public API: analyze_image_bytes
# =====================


def analyze_image_bytes(
    image_bytes: bytes,
    filename: str = "upload.jpg",
    model: str = "gpt-4o",
    image_caption: str = "",
    verbose: bool = False,
    debug: bool = False,
    detail: int = 1,
) -> Dict[str, Any]:
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise EnvironmentError(
            "환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다. 'export OPENAI_API_KEY=...' 후 다시 실행하세요."
        )

    # Guess MIME from filename and b64-encode bytes
    mime = _guess_mime_from_filename(filename)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    if verbose:
        print(f"[INFO] 이미지(바이트) 수신: {filename or '[no name]'} ({mime})")

    return _analyze_b64_core(
        mime,
        b64,
        model=model,
        image_caption=image_caption,
        verbose=verbose,
        debug=debug,
        detail=detail,
    )


# =====================
# CLI
# =====================


def main():
    parser = argparse.ArgumentParser(
        description="Analyze food in an image and output nutrition JSON."
    )
    parser.add_argument(
        "--image", required=True, help="Path to an image file (jpg/png/webp)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model (e.g., gpt-4o, gpt-4.1-mini)",
    )
    parser.add_argument(
        "--caption",
        default="",
        help="Optional short caption/hint about the image (e.g., 'Korean meal with galbijjim, rice, kimchi')",
    )
    parser.add_argument(
        "--out", default=None, help="Output JSON path. Default: <image>.nutrition.json"
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress logs")
    parser.add_argument(
        "--debug", action="store_true", help="Print raw model responses"
    )
    parser.add_argument(
        "--only-json",
        action="store_true",
        help="Print only the final JSON to stdout (no extra logs)",
    )
    parser.add_argument(
        "--detail",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Detail level: 1=basic macros(기본, 출력 최소화), 2=+portion/confidence/micro-nutrients, 3=+bbox if possible",
    )
    args = parser.parse_args()

    try:
        result_raw = analyze_image_with_openai(
            args.image,
            model=args.model,
            image_caption=args.caption,
            verbose=args.verbose,
            debug=args.debug,
            detail=args.detail,
        )
        try:
            result = validate_payload(result_raw)
        except (KeyError, ValueError):
            result = result_raw
    except Exception as e:
        print(
            f"[ERROR] 분석 실패: {e}\n- 해결 팁: --verbose 로 재실행하여 RAW 응답을 확인하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ---- Output shape override: only keep total ----
    # The user requested that both console output and saved JSON contain only the 'total' section.
    if isinstance(result, dict):
        result = {"total": result.get("total", {})}

    # 출력 저장 경로
    out_path = args.out
    if not out_path:
        base, _ = os.path.splitext(args.image)
        out_path = base + ".nutrition.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 콘솔 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.only_json:
        print(f"\n[OK] 저장 완료 → {out_path}")


if __name__ == "__main__":
    main()
