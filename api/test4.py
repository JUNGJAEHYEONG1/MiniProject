import os
import json
import time
from dotenv import load_dotenv, find_dotenv
import re
import traceback
# .env 로드
load_dotenv()
load_dotenv(find_dotenv(usecwd=True))


# 올바른 상대 임포트 사용
from .user_to_meal import run_generation, load_user_payload_from_db


def step1_generate_recommendation():
    # DB 데이터만 사용 (더미 금지)
    user_id = os.getenv("USER_ID")
    if not user_id:
        raise RuntimeError(
            "USER_ID 환경변수가 없습니다. DB 데이터로만 실행하려면 USER_ID를 지정하세요."
        )

    print(f"- DB에서 설문 로드: USER_ID={user_id}")
    user_payload = load_user_payload_from_db(user_id)
    print("- DB 로드 성공: user_payload 확보")

    print("\n[STEP 1] run_generation 호출 시작")
    print("- 입력: 최소 사용자 프로필 JSON 1개")
    try:
        result = run_generation(
            user_payload, print_pretty=False, save_pretty_file=True
        )

        # 가장 최근 recommendation_*.json 경로 찾기
        out_dir = "out"
        latest = None
        latest_mtime = -1
        if os.path.isdir(out_dir):
            for fn in os.listdir(out_dir):
                if fn.startswith("recommendation_") and fn.endswith(".json"):
                    p = os.path.join(out_dir, fn)
                    m = os.path.getmtime(p)
                    if m > latest_mtime:
                        latest_mtime = m
                        latest = p
        saved_path = latest

        print("- 진행: 모델 호출 → 후처리 → 재료 생성 → 링크 부착 → 파일 저장 완료")
        print("- 출력 샘플(plan_meta만):")
        print(
            json.dumps(
                {"plan_meta": result.get("plan_meta", {})}, ensure_ascii=False, indent=2
            )
        )
        print(f"- 아웃풋 파일: {saved_path}")
        return result, saved_path

    except Exception as e:
        # 더미 금지: 바로 에러로 종료
        raise RuntimeError(f"run_generation 실패: {e}")


# 2) meal_to_img: make_pictures_for_meals 테스트
def step2_make_images(plan_json_path: str) -> dict:
    print("\n[STEP 2] make_pictures_for_meals 호출 시작")
    print(f"- 입력: recommendation JSON 경로 = {plan_json_path}")

    generated_image_paths = {}

    try:
        from .meal_to_img import make_pictures_for_meals

        # 1. make_pictures_for_meals가 반환하는 것은 상대 경로 딕셔너리입니다.
        relative_paths = make_pictures_for_meals(plan_json_path, variability=0.2)

        # 2. 반환된 상대 경로들을 절대 경로로 변환합니다.
        for meal_key, rel_path in relative_paths.items():
            # os.path.abspath()를 사용해 완전한 경로를 만듭니다.
            absolute_path = os.path.abspath(rel_path)
            generated_image_paths[meal_key] = absolute_path

        print("- 진행: 타이틀 추출 → 프롬프트 생성 → 이미지 생성 → 파일 저장 완료")

    except Exception as e:
        print(f"! 이미지 생성 중 오류 발생: {e}")
        traceback.print_exc()
        print("- 진행: 이미지 생성 스텝을 건너뜁니다.")

    # 3. 절대 경로가 담긴 딕셔너리를 반환합니다.
    return generated_image_paths


# 3) meal_to_food: analyze_foods 테스트(외부에서 음식 리스트를 인자로 주입)
def step3_analyze_foods(foods):
    print("\n[STEP 3] analyze_foods 호출 시작(외부 주입 음식 리스트)")
    print(f"- 입력: 음식명 리스트({len(foods)}개) = {foods}")

    # 요리 불필요 키워드(간단 분류 규칙)
    no_cook_keywords = [
        "과일", "사과", "바나나", "귤", "포도", "요거트", "우유", "두유",
        "샐러드", "견과", "아몬드", "호두", "땅콩", "김", "김치", "피클",
        "빵", "식빵", "크로와상", "초콜릿", "에너지바", "나물", "무침", "절임",
    ]

    def needs_cooking(name: str) -> bool:
        n = (name or "").strip()
        if not n:
            return False
        for kw in no_cook_keywords:
            if kw in n:
                return False
        cook_indicators = [
            "밥", "찌개", "국", "볶음", "조림", "구이", "찜", "수프",
            "전", "카레", "면", "파스타",
        ]
        for kw in cook_indicators:
            if kw in n:
                return True
        return len(n) >= 4

    need = [x for x in foods if needs_cooking(x)]
    skip = [x for x in foods if not needs_cooking(x)]

    print(f"- 판정: 요리 필요 {len(need)}개, 불필요 {len(skip)}개")
    if skip:
        print("- 요리 불필요 항목:")
        for s in skip:
            print(f"  • {s}")

    if not need:
        print("- 진행: 조리 필요한 항목이 없어 이 스텝 종료")
        return

    try:
        # 올바른 상대 임포트 사용
        from .meal_to_food import analyze_foods

        try:
            data = analyze_foods(need, top_k=1)
            print("- 진행: 유튜브 검색 → 자막/설명 수집 → 규칙/LLM 추출 → 결과 선택 완료")
            preview = data[:2] if isinstance(data, list) else data
            print("- 출력 미리보기(최대 2개):")
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        except Exception as e_inner:
            print("! 유튜브/LLM 의존 구간 실패: 안전 모드 더미 결과 사용")
            print(f"! 예외: {e_inner}")
            dummy = [
                {"food_name": nm, "youtube_link": None, "ingredients": [], "recipe": []}
                for nm in need
            ]
            print("- 진행: 음식명만 보존한 더미 데이터 생성")
            print("- 출력 미리보기(최대 2개):")
            print(json.dumps(dummy[:2], ensure_ascii=False, indent=2))
    except Exception as e:
        print("! 오류: meal_to_food 임포트/실행 실패(의존 라이브러리/키 필요)")
        print(f"! 예외: {e}")
        print("- 진행: 이 스텝은 건너뜀")


def extract_foods_from_plan(plan_json_path):
    with open(plan_json_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    foods = []
    for meal_key in ("breakfast", "lunch", "dinner"):
        container = plan.get(meal_key) or {}
        for it in container.get("items") or []:
            name = (it.get("name") or "").strip()
            if name:
                foods.append(name)
    # 중복 제거, 과도 호출 방지 제한
    dedup = []
    seen = set()
    for nm in foods:
        if nm not in seen:
            seen.add(nm)
            dedup.append(nm)
    return dedup[:12]


def generate_for_user(user_id: str):
    """
    외부(백엔드)에서 불러쓸 때 entrypoint.
    1) 추천 JSON 생성
    2) 이미지 생성
    3) 추천안에서 음식명 추출
    """
    # USER_ID 환경변수 세팅 (step1_generate_recommendation 내부에서 사용)
    os.environ["USER_ID"] = str(user_id)

    result, plan_path = step1_generate_recommendation()
    generated_image_paths = step2_make_images(plan_path)
    foods = extract_foods_from_plan(plan_path)
    return result, plan_path, foods, generated_image_paths


def main():
    print("=== test4.py: 통합 최소 테스트 시작 ===")
    # STEP 1
    result, plan_path = step1_generate_recommendation()
    # STEP 2
    if plan_path and os.path.exists(plan_path):
        step2_make_images(plan_path)
        # STEP 3: plan에서 음식명 추출해 전달
        foods = extract_foods_from_plan(plan_path)
        print(f"\n[INFO] 추천안에서 추출된 음식명({len(foods)}개): {foods}")
        step3_analyze_foods(foods)
    else:
        print("\n[STEP 2/3] 건너뜀: 추천안 파일 경로를 찾을 수 없음")
    print("\n=== test4.py: 통합 최소 테스트 종료 ===")


if __name__ == "__main__":
    main()