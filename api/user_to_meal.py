import os
import re
import time
import json
import datetime
import random
from typing import List, Dict, Any, Tuple
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv

# 선택적 임포트 - 라이브러리가 없어도 애플리케이션이 실행되도록 함
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("경고: openai가 설치되지 않았습니다. OpenAI 기능이 제한됩니다.")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("경고: psycopg2가 설치되지 않았습니다. PostgreSQL 기능이 제한됩니다.")

# --------- .env 로드 (.env 탐색 범위 확장) ---------
# 파일 위치 기준 탐색 + CWD 기준 탐색을 모두 시도
load_dotenv()
load_dotenv(find_dotenv(usecwd=True))

# --------- 데이터베이스 연결 정보 (SQLite 우선, PostgreSQL 대체) ---------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./miniproject.db")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")


def load_user_payload_from_db(user_id: str) -> dict:
    """
    users 테이블에서 최신 레코드를 읽어 user_payload 형식으로 변환.
    SQLite와 PostgreSQL 모두 지원.
    """
    # SQLite 사용 여부 확인
    use_sqlite = DATABASE_URL.startswith("sqlite")
    
    if use_sqlite:
        # SQLite 연결
        import sqlite3
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, user_age, gender, height, weight,
                       activity_level, diet_goal, created_at
                FROM Users
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise FileNotFoundError(f"해당 user_id 레코드가 없습니다: {user_id}")
            
            # SQLite Row 객체를 dict로 변환
            row_dict = dict(row)
        finally:
            conn.close()
    else:
        # PostgreSQL 연결
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL 라이브러리(psycopg2)가 설치되지 않았습니다.")
        
        if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
            raise RuntimeError(
                "PostgreSQL 접속 환경변수(DB_HOST/DB_NAME/DB_USER/DB_PASS)가 비어 있습니다."
            )

        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
        )
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT user_id, user_age, gender, height, weight,
                           activity_level, diet_goal, created_at
                    FROM "Users"
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise FileNotFoundError(f"해당 user_id 레코드가 없습니다: {user_id}")
                row_dict = dict(row)
        finally:
            conn.close()

    # --- 정규화 (공통 로직) ---
    g = (row_dict.get("gender") or "").strip().upper()
    sex = (
        "male"
        if g in ("M", "MALE")
        else ("female" if g in ("F", "FEMALE") else "")
    )

    def _to_int(x):
        try:
            return int(round(float(x)))
        except Exception:
            return None

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    height_cm = _to_int(row_dict.get("height"))
    weight_kg = _to_float(row_dict.get("weight"))

    # 활동량 한글 → 내부 등급
    act_raw = (row_dict.get("activity_level") or "").strip()
    if (
        ("매일" in act_raw)
        or ("3" in act_raw and "번" in act_raw)
        or ("주" in act_raw and any(k in act_raw for k in ["4", "5", "6", "7"]))
    ):
        activity_level = "high"
    elif "2" in act_raw and "번" in act_raw or "주 2" in act_raw:
        activity_level = "moderate"
    elif act_raw:
        activity_level = "low"
    else:
        activity_level = "moderate"

    goal_txt = (row_dict.get("diet_goal") or "").strip()
    goals = [goal_txt] if goal_txt else []

    payload = {
        "age": row_dict.get("user_age") or None,
        "sex": sex,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_level": activity_level,
        "goals": goals,
        "dietary_preferences": [],  # 현재 테이블에 없으므로 빈 배열
        "allergies": [],  # 현재 테이블에 없으므로 빈 배열
        "daily_calorie_target": None,
        "notes": "",
    }
    return payload


# -----------------------------
# 예시 사용자 입력
# -----------------------------
EXAMPLE_USER_PAYLOAD = {
    "age": 29,
    "sex": "male",
    "height_cm": 175,
    "weight_kg": 72,
    "activity_level": "moderate",
    "goals": ["체중 증량", "단백질 충분"],
    "dietary_preferences": [""],
    "allergies": ["견과류"],
    "daily_calorie_target": 2100,
    "notes": "아침에 바쁜 편, 우유 OK, 빵류 가끔 섭취",
}

# --------- 키 읽기 ---------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    print("경고: 환경 변수 OPENAI_API_KEY가 비어 있습니다. OpenAI 기능이 제한됩니다.")

# --------- OpenAI 클라이언트 ---------
client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI 클라이언트 초기화 실패: {e}")
        client = None

# -----------------------------
# PROMPTS
# -----------------------------
seed = int(time.time() * 1000) % 100000
random.seed(seed)
concept_hint = f"""
[무작위 테마 시드]: {seed}
- 아침 콘셉트 후보: 우유+토스트/주먹밥+국/죽+반찬/요거트+과일
- 점심 콘셉트 후보: 덮밥/비빔/국수/찌개 정식
- 저녁 콘셉트 후보: 구이 정식/전골/조림/볶음/비빔
- 세 끼 메인 단백질 로테이션(가금/어류/소/돼지/계란/유제품/콩류 중 중복 최소화)
- 끼니별 칼로리·단백질 목표 ±15% 허용
"""

SYSTEM = f"""
너는 개인 맞춤형 음식 추천 코치이자 영양사다.
STRICT JSON RESPONSE:
- 오직 JSON 1개(한 줄, minified)만 출력. 코드블록/주석/설명 금지.
- RFC 8259 유효 JSON(모든 키 쌍따옴표, 마지막 쉼표 금지, 타입 정확).
도메인 규칙:
- 한국 사용자 기준. 알레르기/선호/식사 정도/운동 빈도 반영.
- 같은 끼니 내 유사 메뉴 중복 금지. 의학적 진단 금지.
{concept_hint}
"""

DEV = """
[출력 스키마]
오직 아래 구조만 출력(최상위 키 3개: breakfast, lunch, dinner):
{
  "breakfast": { "title": string, "subtitle": string, "items": [ { "name": string, "macros": { "protein_g": number, "carb_g": number, "fat_g": number }, "prep_time_min": integer } ] },
  "lunch":     { "title": string, "subtitle": string, "items": [ { "name": string, "macros": { "protein_g": number, "carb_g": number, "fat_g": number }, "prep_time_min": integer } ] },
  "dinner":    { "title": string, "subtitle": string, "items": [ { "name": string, "macros": { "protein_g": number, "carb_g": number, "fat_g": number }, "prep_time_min": integer } ] }
}

[출력 규칙]
- 각 끼니(items) 배열 길이는 정확히 5.
- 조화 규칙: 한 끼니는 한 가지 식문화/메뉴 컨셉으로 통일(예: 한식+한식). 메인 1개(탄수/단백 중심), 보조 반찬 2~3개, 음료/후식 0~1개로 구성. 무관한 조합 금지.
- title은 12자 이내 핵심 문구, subtitle은 30자 이내 한 문장 요약.
- 각 항목 키는 name, macros(protein_g/carb_g/fat_g), prep_time_min만 허용. 모든 수치는 숫자.
- JSON 1개를 한 줄(minified)로만 출력.

[타이틀·서브타이틀 규칙]
- title: ‘메인(주재료+조리법) + 대표 사이드 1~2개’를 드러내는 자연스러운 한국어. 예) "닭가슴살 구이와 시금치나물, 미소된장국"
- subtitle: 맛·식감·조리 포인트 한 문장(30자 이내)
"""

MEAL_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "macros": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "protein_g": {"type": "number"},
                "carb_g": {"type": "number"},
                "fat_g": {"type": "number"},
            },
            "required": ["protein_g", "carb_g", "fat_g"],
        },
        "prep_time_min": {"type": "integer"},
    },
    "required": ["name", "macros", "prep_time_min"],
}

MEAL_CONTAINER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "maxLength": 24},
        "subtitle": {"type": "string", "maxLength": 64},
        "items": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": MEAL_ITEM_SCHEMA,
        },
    },
    "required": ["title", "subtitle", "items"],
}

MEALS_SCHEMA = {
    "name": "MealsAll",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "breakfast": MEAL_CONTAINER_SCHEMA,
            "lunch": MEAL_CONTAINER_SCHEMA,
            "dinner": MEAL_CONTAINER_SCHEMA,
        },
        "required": ["breakfast", "lunch", "dinner"],
    },
}

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")


def extract_json_text_chat(resp):
    try:
        t = resp.choices[0].message.content
        if t:
            return t.strip().strip("` ")
    except Exception:
        pass
    return None


def _strip_json_strings(src: str) -> str:
    return re.sub(r'"(\\.|[^"\\])*"', "", src)


def is_likely_truncated(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if not stripped.endswith(("}", "]")):
        return True
    tmp = _strip_json_strings(stripped)
    if tmp.count("{") != tmp.count("}"):
        return True
    if tmp.count("[") != tmp.count("]"):
        return True
    return False


def _repair_model_json(src: str) -> str:
    cleaned = src.replace("\u200b", "").strip()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    def _fix_key(m: re.Match) -> str:
        prefix, key = m.group(1), m.group(2)
        return f'{prefix}"{key}":'

    cleaned = re.sub(r"([\{,]\s*)'([^']+)'\s*:", _fix_key, cleaned)

    def _fix_value(m: re.Match) -> str:
        value = m.group(1).replace('"', '\\"')
        return f':"{value}"'

    cleaned = re.sub(r":\s*'([^'\\]*)'", _fix_value, cleaned)
    cleaned = re.sub(r"\bTrue\b", "true", cleaned)
    cleaned = re.sub(r"\bFalse\b", "false", cleaned)
    cleaned = re.sub(r"\bNone\b", "null", cleaned)
    return cleaned


def safe_parse_json(s):
    if not s:
        return None
    s2 = s.replace("``````", "").strip()
    s2 = (
        s2.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    s3 = _repair_model_json(s2)
    for candidate in (s2, s3):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    for candidate in (s3, s2):
        try:
            m = re.search(r"(\{.*\}|\[.*\])", candidate, re.DOTALL)
            if m:
                return json.loads(m.group(1))
        except Exception:
            continue
    return None


def normalize_to_meals_obj(data):
    if isinstance(data, dict):
        out = {}
        for k in ("breakfast", "lunch", "dinner"):
            v = data.get(k)
            if isinstance(v, dict) and "items" in v and isinstance(v["items"], list):
                out[k] = v
        if out:
            for k in ("breakfast", "lunch", "dinner"):
                out.setdefault(k, {"title": "", "subtitle": "", "items": []})
            return out
    return None


def compute_kcal_from_macros(m):
    try:
        p = float(m.get("protein_g", 0))
        c = float(m.get("carb_g", 0))
        f = float(m.get("fat_g", 0))
    except Exception:
        p = c = f = 0.0
    pk = round(p * 4)
    ck = round(c * 4)
    fk = round(f * 9)
    total = pk + ck + fk
    if total > 0:
        protein_pct = round(pk * 100 / total)
        carb_pct = round(ck * 100 / total)
        fat_pct = round(fk * 100 / total)
    else:
        protein_pct = carb_pct = fat_pct = 0
    return (
        total,
        {"protein_kcal": pk, "carb_kcal": ck},
        {"protein_pct": protein_pct, "carb_pct": carb_pct, "fat_pct": fat_pct},
    )


def postprocess_to_full(raw, user_payload):
    out = {"plan_meta": {}, "breakfast": {}, "lunch": {}, "dinner": {}}
    daily_target = user_payload.get("daily_calorie_target")
    out["plan_meta"]["daily_calorie_target"] = (
        int(daily_target) if isinstance(daily_target, (int, float)) else None
    )
    out["plan_meta"]["goal_note"] = "사용자 목표를 반영한 추천"

    total_p = total_c = total_f = 0.0
    total_k = 0

    for meal_key in ("breakfast", "lunch", "dinner"):
        meal = raw.get(meal_key) or {}
        title = meal.get("title", "")
        subtitle = meal.get("subtitle", "")
        items = meal.get("items", []) or []

        arr = []
        for it in items:
            name = it.get("name", "")
            macros = it.get("macros", {}) or {}
            calories, breakdown, ratio = compute_kcal_from_macros(macros)
            item = {
                "name": name,
                "calories": calories,
                "macros": {
                    "protein_g": float(macros.get("protein_g", 0)),
                    "carb_g": float(macros.get("carb_g", 0)),
                    "fat_g": float(macros.get("fat_g", 0)),
                },
                "kcal_breakdown": breakdown,
                "macros_ratio": ratio,
                "prep_time_min": int(it.get("prep_time_min", 0)),
            }
            total_p += item["macros"]["protein_g"]
            total_c += item["macros"]["carb_g"]
            total_f += item["macros"]["fat_g"]
            total_k += calories
            arr.append(item)

        out[meal_key] = {"title": title, "subtitle": subtitle, "items": arr}

    out["plan_meta"]["total_calories"] = total_k
    out["plan_meta"]["macros_total"] = {
        "protein_g": round(total_p, 1),
        "carb_g": round(total_c, 1),
        "fat_g": round(total_f, 1),
    }
    pk = round(total_p * 4)
    ck = round(total_c * 4)
    fk = round(total_f * 9)
    tot = pk + ck + fk
    out["plan_meta"]["macros_ratio"] = {
        "protein_pct": round(pk * 100 / tot) if tot > 0 else 0,
        "carb_pct": round(ck * 100 / tot) if tot > 0 else 0,
        "fat_pct": round(fk * 100 / tot) if tot > 0 else 0,
    }
    return out


def chat_once(
    messages,
    max_tokens=2048,
    temperature=0.8,
    top_p=0.9,
    presence_penalty=0.3,
    frequency_penalty=0.2,
    schema=None,
):
    if not client:
        print("OpenAI 클라이언트가 사용할 수 없습니다.")
        return None, None
    
    try:
        kwargs = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "max_tokens": max_tokens,
        }
        if schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": schema,
            }
        resp = client.chat.completions.create(**kwargs)
        text = extract_json_text_chat(resp)
        finish_reason = getattr(resp.choices[0], "finish_reason", None)
        return text, finish_reason
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return None, None


def title_has_main_and_side(title: str) -> bool:
    main_kw = r"(덮밥|구이|볶음|전골|찌개|국수|비빔|조림|스튜|샐러드|토스트|죽|주먹밥)"
    has_main = re.search(main_kw, title) is not None
    has_side_join = ("와 " in title) or ("," in title) or ("와," in title)
    return bool(has_main and has_side_join)


def attempt_prompt(messages, schema, attempts=2, max_tokens=2048):
    last_text = None
    last_finish_reason = None
    curr_max = max_tokens
    for i in range(attempts):
        temp = min(0.7 + 0.1 * i, 1.0)
        pres = 0.3 + 0.05 * i
        freq = 0.2 + 0.05 * i

        text, finish_reason = chat_once(
            messages,
            max_tokens=curr_max,
            temperature=temp,
            top_p=0.9,
            presence_penalty=pres,
            frequency_penalty=freq,
            schema=schema,
        )
        if text:
            last_text = text
        if finish_reason:
            last_finish_reason = finish_reason
        if finish_reason == "length":
            curr_max = min(int(curr_max * 1.5), 4096)
            continue
        if not text or is_likely_truncated(text):
            curr_max = min(curr_max + 256, 4096)
            continue
        parsed = safe_parse_json(text)
        raw = normalize_to_meals_obj(parsed)
        if raw:
            titles_ok = all(
                title_has_main_and_side((raw.get(k) or {}).get("title", ""))
                for k in ("breakfast", "lunch", "dinner")
            )
            if not titles_ok and i + 1 < attempts:
                continue
            return raw, text, finish_reason, curr_max
    return None, last_text, last_finish_reason, curr_max


def build_prompt_variants(user_payload):
    primary_user_msg = (
        "오직 JSON 한 개(한 줄, minified)만 출력. 코드블록/주석/설명 금지.\n"
        "최상위 키는 breakfast, lunch, dinner 3개 모두 포함. 각 끼니는 {title, subtitle, items[5]} 구조.\n"
        "각 끼니의 items는 한 가지 컨셉으로 조화롭게 구성(메인 1, 보조 2~3, 음료/후식 0~1). 무관/중복 메뉴 금지.\n"
        '각 항목 키는 name, macros, prep_time_min만. macros는 {"protein_g":number,"carb_g":number,"fat_g":number}.\n\n'
        "[사용자]\n" + json.dumps(user_payload, ensure_ascii=False)
    )
    compact_user_msg = (
        "오직 JSON 한 개(한 줄). 최상위 키는 breakfast, lunch, dinner 3개 모두 포함. 각 끼니는 {title, subtitle, items[5]} 구조.\n"
        "한 끼니 내 조화 규칙 준수(메인/보조/음료·후식). 코드블록/설명 금지.\n"
        + json.dumps(user_payload, ensure_ascii=False)
    )
    prompt_variants = [
        (
            [
                {"role": "system", "content": SYSTEM + "\n" + DEV},
                {"role": "user", "content": primary_user_msg},
            ],
            MEALS_SCHEMA,
            3,
            3072,
        ),
        (
            [
                {"role": "system", "content": SYSTEM + "\n" + DEV},
                {"role": "user", "content": compact_user_msg},
            ],
            MEALS_SCHEMA,
            3,
            2560,
        ),
    ]
    return prompt_variants


ING_SCHEMA = {
    "name": "IngredientList",
    "strict": True,
    "schema": {
        "type": "array",
        "minItems": 5,
        "maxItems": 8,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}, "amount": {"type": "string"}},
            "required": ["name"],
        },
    },
}


def generate_ingredients_for(dish_name: str) -> list:
    messages = [
        {
            "role": "system",
            "content": '오직 JSON 한 개(한 줄). 코드블록/설명 금지. 배열만 출력.\n각 항목은 {"name": string, "amount": string} 키만 포함.',
        },
        {
            "role": "user",
            "content": f"요리 이름: {dish_name}\n이 요리를 만들 때 필요한 핵심 재료 5~8개를 간결하게 제시. 브랜드/광고/링크 금지.",
        },
    ]
    try:
        txt, _ = chat_once(
            messages,
            max_tokens=256,
            temperature=0.7,
            top_p=0.9,
            presence_penalty=0.2,
            frequency_penalty=0.2,
            schema=ING_SCHEMA,
        )
        data = safe_parse_json(txt)
        if isinstance(data, list):
            cleaned = []
            for it in data:
                if isinstance(it, dict) and "name" in it:
                    nm = str(it.get("name", "")).strip()
                    amt = str(it.get("amount", "")).strip() if it.get("amount") else ""
                    if nm:
                        cleaned.append({"name": nm, "amount": amt})
            random.shuffle(cleaned)
            k = random.randint(5, min(8, len(cleaned))) if cleaned else 0
            return cleaned[:k]
    except Exception:
        pass
    return []


def attach_coupang_search_links(plan_json: dict) -> dict:
    for meal_key in ("breakfast", "lunch", "dinner"):
        container = plan_json.get(meal_key, {}) or {}
        items = container.get("items", []) or []
        for it in items:
            dish_q = quote_plus(f"{it.get('name', '')} 밀키트")
            it["meal_kit_link"] = f"https://www.coupang.com/np/search?q={dish_q}"
            for ing in it.get("ingredients", []) or []:
                q = quote_plus(ing.get("name", ""))
                ing["purchase_link"] = f"https://www.coupang.com/np/search?q={q}"
    return plan_json


def run_generation(
    user_payload: dict, print_pretty: bool = True, save_pretty_file: bool = True
) -> dict:
    prompt_variants = build_prompt_variants(user_payload)

    raw = None
    last_raw_text = None
    last_finish_reason = None
    last_max_output_tokens = None

    for messages, schema, attempts, max_tokens in prompt_variants:
        candidate_raw, text, finish_reason, effective_max = attempt_prompt(
            messages, schema, attempts=attempts, max_tokens=max_tokens
        )
        if text:
            last_raw_text = text
        if finish_reason:
            last_finish_reason = finish_reason
        if effective_max:
            last_max_output_tokens = effective_max
        if candidate_raw:
            raw = candidate_raw
            break

    if raw is None:
        debug_path = None
        if last_raw_text:
            out_dir = "out"
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = os.path.join(out_dir, f"raw_response_{ts}.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(last_raw_text)
        payload = {"error": "MODEL_OUTPUT_NOT_JSON"}
        if debug_path:
            payload["debug_raw_path"] = debug_path
        if last_finish_reason:
            payload["last_finish_reason"] = last_finish_reason
        if "last_max_output_tokens" in locals():
            payload["last_max_output_tokens"] = last_max_output_tokens
        if print_pretty:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return payload

    final = postprocess_to_full(raw, user_payload)

    for meal_key in ("breakfast", "lunch", "dinner"):
        container = final.get(meal_key, {}) or {}
        for item in container.get("items", []) or []:
            ings = generate_ingredients_for(item.get("name", ""))
            if ings:
                item["ingredients"] = ings

    final = attach_coupang_search_links(final)

    if print_pretty:
        print(json.dumps(final, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(final, ensure_ascii=False, separators=(",", ":")))

    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"recommendation_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        if save_pretty_file:
            json.dump(final, f, ensure_ascii=False, indent=2)
        else:
            json.dump(final, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[saved] {out_path}")

    return final


def main():
    # 예시 데이터 주입 실행
    _ = run_generation(EXAMPLE_USER_PAYLOAD, print_pretty=True, save_pretty_file=True)


if __name__ == "__main__":
    # 표준 진입점 패턴: 스크립트 직접 실행 시에만 동작
    # 모듈로 임포트될 때는 main()이 자동 실행되지 않음
    main()
