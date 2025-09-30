import os, re, time, json
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv, find_dotenv
import config

# 선택적 임포트 - 라이브러리가 없어도 애플리케이션이 실행되도록 함
try:
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("경고: google-api-python-client가 설치되지 않았습니다. YouTube 기능이 제한됩니다.")

try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    print("경고: youtube-transcript-api가 설치되지 않았습니다. 자막 기능이 제한됩니다.")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("경고: openai가 설치되지 않았습니다. OpenAI 기능이 제한됩니다.")

# --------- .env 로드 ---------
# 1) 기본 탐색(.env를 현재 파일/상위 폴더에서 탐색)
load_dotenv(override=True)  # 이미 설정된 OS 환경변수를 기본적으로 덮어쓰지 않음
# 2) 현재 작업 디렉터리 기준 추가 탐색(IDE/터미널 실행 위치가 다른 경우 보강)
load_dotenv(find_dotenv(usecwd=True))  # 못 찾으면 None, 찾으면 그 경로를 로드

# --------- 키 읽기 ---------
OPENAI_API_KEY = config.OPENAI_API_KEY
YOUTUBE_API_KEY = config.YOUTUBE_API_KEY

if not OPENAI_API_KEY:
    print("경고: 환경 변수 OPENAI_API_KEY가 비어 있습니다. OpenAI 기능이 제한됩니다.")
if not YOUTUBE_API_KEY:
    print("경고: 환경 변수 YOUTUBE_API_KEY가 비어 있습니다. YouTube 기능이 제한됩니다.")

# --------- 클라이언트 ---------
client = None
yt = None

if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI 클라이언트 초기화 실패: {e}")
        client = None

if GOOGLE_API_AVAILABLE and YOUTUBE_API_KEY:
    try:
        yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    except Exception as e:
        print(f"YouTube API 클라이언트 초기화 실패: {e}")
        yt = None

# --------- 검색 ---------
def search_recipe_videos(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    if not yt:
        print("YouTube API가 설정되지 않았습니다.")
        return []
    
    try:
        q = f"{query} 레시피 만드는 법 recipe how to make ingredients"
        resp = yt.search().list(
            q=q,
            part="id,snippet",
            maxResults=max(1, min(5, max_results)),
            type="video",
            safeSearch="moderate",
            relevanceLanguage="ko",
            videoCaption="any",
        ).execute()
        out = []
        for it in resp.get("items", []):
            vid = it["id"]["videoId"]
            title = it["snippet"]["title"]
            desc = it["snippet"].get("description", "")
            url = f"https://www.youtube.com/watch?v={vid}"
            out.append({"videoId": vid, "title": title, "description": desc, "url": url})
        return out
    except Exception as e:
        print(f"YouTube 검색 중 오류 발생: {e}")
        return []

# --------- 자막/텍스트 수집 ---------
def get_best_transcript(video_id: str, tries: int = 2) -> str:
    if not YOUTUBE_TRANSCRIPT_AVAILABLE:
        print("YouTube Transcript API가 사용할 수 없습니다.")
        return ""
    
    langs_priority = [["ko","en"], ["en","ko"]]
    for attempt in range(tries):
        for langs in langs_priority:
            try:
                tr = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                return " ".join(seg.get("text", "") for seg in tr if seg.get("text"))
            except (TranscriptsDisabled, NoTranscriptFound):
                continue
            except Exception:
                time.sleep(0.3)
                continue
        time.sleep(0.4 * (attempt + 1))  # 백오프
    return ""

def fetch_text_from_video_meta(video: Dict[str, str]) -> str:
    return video.get("description", "")

def get_video_text(video: Dict[str, str]) -> str:
    t = get_best_transcript(video["videoId"])
    if t.strip():
        return t
    meta = fetch_text_from_video_meta(video)
    return meta

# --------- 규칙 기반 1차 파서 ---------
UNIT_TOKENS = [
    "g","kg","mg","ml","l","L",
    "컵","큰술","작은술","티스푼","tbsp","tsp",
    "장","쪽","토막","줌","꼬집","알","개","봉","봉지","팩","캔","스틱"
]
AMOUNT_TOKENS = [
    "약간","소량","적당량","한","두","세","네","다섯","여섯","일곱","여덟","아홉","열","반","절반"
]
FRACTIONS = ["1/4","1/3","1/2","2/3","3/4","¼","⅓","½","⅔","¾"]

ING_SYNONYMS = {
    "파":"대파","쪽파":"대파","green onion":"대파","spring onion":"대파",
    "마늘":"마늘","갈릭":"마늘","garlic":"마늘",
    "양파":"양파","onion":"양파",
    "간장":"간장","soy sauce":"간장",
    "설탕":"설탕","sugar":"설탕",
    "소금":"소금","salt":"소금",
    "참기름":"참기름","sesame oil":"참기름",
    "식초":"식초","vinegar":"식초",
    "후추":"후추","black pepper":"후추",
}

# Python re는 같은 이름의 그룹을 대안(|) 양쪽에 둘 수 없으므로 분기별로 다른 이름 사용.
AMOUNT_RE_1 = r"(?P<amount1>(\d+(\.\d+)?|\d+\s*[-~]\s*\d+|\d+/\d+|" + "|".join(map(re.escape, FRACTIONS)) + "|" + "|".join(AMOUNT_TOKENS) + r"))"
UNIT_RE_1   = r"(?P<unit1>(" + "|".join(map(re.escape, UNIT_TOKENS)) + r"))"
AMOUNT_RE_2 = r"(?P<amount2>(\d+(\.\d+)?|\d+\s*[-~]\s*\d+|\d+/\d+|" + "|".join(map(re.escape, FRACTIONS)) + "|" + "|".join(AMOUNT_TOKENS) + r"))"
UNIT_RE_2   = r"(?P<unit2>(" + "|".join(map(re.escape, UNIT_TOKENS)) + r"))"

# 예: "- 돼지고기 200 g", "간장 1 큰술", "설탕 약간"
ING_LINE_RE = re.compile(
    rf"^\s*(?:[-•·]|\d+\.)?\s*(?:(?P<name1>.+?)\s+{AMOUNT_RE_1}\s*{UNIT_RE_1}?|{AMOUNT_RE_2}\s*{UNIT_RE_2}?\s*(?P<name2>.+))\s*$",
    re.IGNORECASE
)

COOK_VERBS = [
    "볶","끓","졸","재우","튀기","굽","섞","썰","다지","우려","삶","부치","데치",
    "간하","양념하","익히","붓","넣","덧붙","가열","볶아","끓여","졸여","섞어","섞으","담가"
]

def normalize_ingredient_name(name: str) -> str:
    nm = name.strip()
    nm = re.sub(r"\(.*?\)", "", nm)  # 괄호 설명 제거
    nm = re.sub(r"\s+", " ", nm)
    nm_l = nm.lower()
    for k, v in ING_SYNONYMS.items():
        if k in nm_l:
            return v
    return nm

def rule_based_extract(text: str) -> Tuple[List[str], List[str]]:
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    ingredients, steps = [], []
    for ln in lines:
        m = ING_LINE_RE.match(ln)
        if m:
            name = (m.group("name1") or m.group("name2") or "").strip()
            amount = (m.group("amount1") or m.group("amount2") or "").strip()
            unit   = (m.group("unit1") or m.group("unit2") or "").strip()
            name = normalize_ingredient_name(name)
            item = " ".join(x for x in [name, amount, unit] if x).strip()
            if item:
                ingredients.append(item)
        if any(v in ln for v in COOK_VERBS) or re.match(r"^\s*\d+\.", ln):
            steps.append(ln)
    def dedup(lst: List[str]) -> List[str]:
        seen, out = set(), []
        for x in lst:
            y = re.sub(r"\s+", " ", x).strip().lower()
            if y not in seen:
                seen.add(y)
                out.append(x.strip())
        return out
    return dedup(ingredients), dedup(steps)

# --------- 존대말 변환(규칙 기반) ---------
def to_polite_recipe(sent: str) -> str:
    s = sent.strip()
    # 이미 공손체면 유지
    if re.search(r"(하세요|해요|해주세요|주시기 바랍니다|십시오)[.!?]*$", s):
        return re.sub(r"[ \t]+$", "", s if re.search(r"[.!?]$", s) else s + ".")
    # 끝의 기호 제거
    s = re.sub(r"[.!?\s]+$", "", s)

    # 대표 명령형/서술형 패턴 간단 치환
    rules = [
        (r"(담아라|올려라|넣어라|섞어라|비벼라|끓여라|졸여라|부쳐라|데쳐라|구워라|볶아라|썰어라|다져라|재워라|가열하라|뿌려라|건져라|풀어라)$", "세요"),
        (r"(줘|줘라)$", "주세요"),
        (r"(담아|올려|넣어|섞어|비벼|끓여|졸여|부쳐|데쳐|구워|볶아|썰어|다져|재워|가열해|뿌려|건져|풀어)$", r"\g<0> 주세요"),
        (r"([가-힣]+)해라$", r"\1하세요"),
        (r"([가-힣]+)해$", r"\1하세요"),
        (r"([가-힣]+)다$", r"\1해 주세요"),
    ]
    for pat, rep in rules:
        ns = re.sub(pat, rep, s)
        if ns != s:
            s = ns

    if not re.search(r"[.!?]$", s):
        s += "."
    return s

def to_polite_recipes(recipes: List[str]) -> List[str]:
    return [to_polite_recipe(x) for x in recipes]

# --------- LLM 보정 ---------
def llm_refine_ingredients_steps(text: str, lang: str="ko") -> Tuple[List[str], List[str]]:
    if not client:
        print("OpenAI 클라이언트가 사용할 수 없습니다.")
        return [], []
    
    sys_msg = "간결하고 정확하게 한국어로 답하세요." if lang=="ko" else "Answer concisely in English."
    prompt = (
        "다음 자막/설명에서 재료와 레시피 단계를 추출하세요.\n"
        "- 재료: 글머리표 목록, 각 항목에 가능하면 계량 포함.\n"
        "- 레시피: 글머리표 목록, 모든 문장을 해요체 존대 명령형(예: '~해 주세요', '~하세요')으로 통일.\n"
        "- 다른 텍스트 출력 금지.\n\n"
        f"{text[:12000]}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        content = resp.choices[0].message.content or ""
        lines = [ln.strip(" -•\t").strip() for ln in content.splitlines() if ln.strip()]
        ing_idx = next((i for i,l in enumerate(lines) if re.search(r"^(재료|ingredients?)\b", l, re.I)), None)
        step_idx = next((i for i,l in enumerate(lines) if re.search(r"^(레시피|steps?|directions?)\b", l, re.I)), None)
        ings, steps = [], []
        if ing_idx is not None and step_idx is not None:
            if ing_idx < step_idx:
                ings = [x for x in lines[ing_idx+1:step_idx] if x]
                steps = [x for x in lines[step_idx+1:] if x]
            else:
                steps = [x for x in lines[step_idx+1:ing_idx] if x]
                ings = [x for x in lines[ing_idx+1:] if x]
        elif ing_idx is not None:
            ings = [x for x in lines[ing_idx+1:] if x]
        elif step_idx is not None:
            steps = [x for x in lines[step_idx+1:] if x]
        else:
            mid = max(1, len(lines)//2)
            ings, steps = lines[:mid], lines[mid:]
        ings = [re.sub(r"\s+", " ", x).strip() for x in ings]
        steps = [re.sub(r"\s+", " ", x).strip() for x in steps]
        steps = to_polite_recipes(steps)
        return ings, steps
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return [], []

# --------- 영상 단위 처리 ---------
def extract_recipe_from_video(video: Dict[str, str]) -> Dict[str, Any]:
    raw_text = get_video_text(video)
    ings1, steps1 = rule_based_extract(raw_text)
    ings, steps = ings1, steps1
    if len(ings) < 3 or len(steps) < 3:
        li, ls = llm_refine_ingredients_steps(raw_text, "ko")
        if li: ings = li
        if ls: steps = ls
    steps = to_polite_recipes(steps)
    return {
        "youtube_link": video["url"],
        "title": video["title"],
        "ingredients": ings,
        "recipe": steps,
        "video_id": video["videoId"]
    }

# --------- 메인 파이프라인 ---------
def analyze_foods(food_names: List[str], top_k: int = 1) -> List[Dict[str, Any]]:
    results = []
    for food in food_names:
        # 후보 5개 수집
        candidates = search_recipe_videos(food, max_results=5)
        if not candidates:
            results.append({
                "food_name": food,
                "youtube_link": None,
                "ingredients": [],
                "recipe": [],
            })
            continue

        # 설명 키워드 기반 가중치
        def score(v):
            desc = v.get("description","").lower()
            sc = 0
            for kw in ["재료","분량","큰술","작은술","tsp","tbsp","ingredients"]:
                if kw in desc:
                    sc += 1
            return sc

        ranked = sorted(candidates, key=score, reverse=True)

        picked = None
        for vid in ranked:
            item = extract_recipe_from_video(vid)
            ings = item.get("ingredients") or []
            steps = item.get("recipe") or []
            if len(ings) >= 3 and len(steps) >= 3:
                picked = item
                break
            time.sleep(0.2)  # 후보 간 간격

        if picked is None:
            first = ranked[0]
            results.append({
                "food_name": food,
                "youtube_link": first.get("url"),
                "ingredients": [],
                "recipe": [],
            })
        else:
            results.append({
                "food_name": food,
                "youtube_link": picked.get("youtube_link"),
                "ingredients": picked.get("ingredients", []),
                "recipe": picked.get("recipe", []),
            })

        time.sleep(0.25)  # 음식 간 rate-limit
    return results

if __name__ == "__main__":
    foods = ["비빔밥", "김치찌개", "불고기"]
    data = analyze_foods(foods, top_k=3)
    print(json.dumps(data, ensure_ascii=False, indent=2))
