# MiniProject - AI 기반 식단 추천 시스템

이 프로젝트는 AI를 활용한 개인 맞춤형 식단 추천 시스템입니다.

## 주요 기능

- **개인 맞춤 식단 추천**: 사용자 프로필을 기반으로 한 아침/점심/저녁 식단 추천
- **YouTube 레시피 분석**: YouTube에서 레시피 영상을 검색하고 자막을 분석하여 재료와 조리법 추출
- **AI 이미지 생성**: 추천된 식단의 이미지를 AI로 생성
- **데이터베이스 연동**: PostgreSQL 지원

## 사용한 기술 스택
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database**: PostgreSQL, SQLite
- **AI/ML**: OpenAI API, Google API (YouTube)

## 프로젝트 구조

```
MiniProject/
├── api/                    # AI API 모듈
│   ├── __init__.py        # API 라우터 정의
|   ├── image.py           # 사용자가 이미지 넣었을때 분석하는 ai
│   ├── meal_to_food.py    # YouTube 레시피 분석 ai
│   ├── meal_to_img.py     # AI 이미지 생성
│   ├── user_to_meal.py    # 식단 추천 생성
│   └── test4.py          # 통합 테스트
├── account/              # 사용자 계정 관리
|   ├── account_crud.py   # 계정 관련 데이터베이스와의 상호작용 
|   ├── account_router.py # API 라우터 정의
|   ├── account_schema.py # API 데이터 모델 및 스키마 정의
├── utils/                # s3에 이미지 저장
├── ai/                   # AI 관련 기능 (account와 같은 폴더 구조)
├── main.py              # FastAPI 메인 애플리케이션
├── models.py            # 데이터베이스 모델
├── config.py            # 설정
├── database.py          # 데이터베이스 연결
└── requirements.txt     # 의존성 패키지
```

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`env_example.txt` 파일을 참고하여 `.env` 파일을 생성하고 필요한 API 키들을 설정하세요:

```bash
# 필수 환경변수
OPENAI_API_KEY=your-openai-api-key
YOUTUBE_API_KEY=your-youtube-api-key
SECRET_KEY="your_super_secret_key_is_here"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 데이터베이스 URL (택 1)
DATABASE_URL="postgresql://user:password@host:port/dbname" # PostgreSQL 예시
DATABASE_URL="sqlite:///./miniproject.db" # SQLite 예시

# 선택적 환경변수 (S3 사용 시)
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
S3_BUCKET_NAME="your-s3-bucket-name"
AWS_REGION="your-aws-region"
```

### 3. 애플리케이션 실행

```bash
uvicorn main:app --reload
```

## API 엔드포인트

### 👤 사용자 인증 및 계정
**Prefix:** `/users`

- `POST /signup`: 사용자 회원가입
- `POST /login`: 로그인 및 Access Token 발급 (HTTPOnly 쿠키)
- `GET /logout`: 로그아웃 (쿠키 삭제)

### 🥑 사용자 프로필 및 설정
**Prefix:** `/users`

- `PATCH /inital/info`: 초기 설문 정보(신체, 활동량 등) 입력 및 업데이트
- `GET /profile/info`: 개인 프로필 정보 조회
- `GET /food-setting`: 음식 설정 정보(선호, 알러지 등) 조회
- `PATCH /food-setting`: 음식 설정 정보 업데이트

### 📸 섭취 기록 및 분석
**Prefix:** `/users`

- `POST /eaten-food-image`: 먹은 음식 사진 업로드 및 AI 영양 정보 분석/저장
- `GET /eaten/foods/info`: 전체 음식 기록 목록 조회 (test중)
- `GET /eaten/foods/{eaten_food_no}`: 유저가 먹은 특정 음식 기록 상세 정보 조회

### 🤖 AI 식단 추천
**Prefix:** `/ai`

- `POST /generate-recommendation/food`: 현재 사용자의 프로필 기반 AI 맞춤 식단 추천 생성 및 저장
- `GET /meal-kit/detail`: 추천 식단 상세 정보 조회 (밀키트 포함, `recommendation_id` 필요)
- `GET /recommendations/{recommendation_id}/recipe`: 추천 식단 레시피 상세 정보 조회
- `GET /meal-kit/purchase-link/{meal_kit_id}`: 특정 밀키트의 구매 링크(YouTube) 정보 조회


## 주요 모듈 설명

### meal_to_food.py

YouTube API를 사용하여 레시피 영상을 검색하고, 자막을 분석하여 재료와 조리법을 추출합니다.

### meal_to_img.py

OpenAI의 이미지 생성 API를 사용하여 추천된 식단의 이미지를 생성합니다.

### user_to_meal.py

사용자 프로필을 기반으로 AI를 활용하여 개인 맞춤형 식단을 추천합니다.

### test4.py

전체 파이프라인을 테스트하는 통합 테스트 모듈입니다.

## 데이터베이스 지원

- **SQLite**: 기본 설정, 개발 환경에 적합
- **PostgreSQL**: 프로덕션 환경 지원

환경변수 `DATABASE_URL`을 설정하여 데이터베이스를 선택할 수 있습니다.

## 주의사항

- OpenAI API 키와 YouTube API 키가 필요합니다.
- API 사용량에 따라 비용이 발생할 수 있습니다.
- 이미지 생성 기능은 OpenAI의 이미지 생성 모델을 사용합니다.

## 문제 해결
- API키 오류: .env 파일에 환경변수가 올바르게 설정되었는지 다시 한번 확인하세요.
- 데이터베이스 연결 오류: DATABASE_URL이 현재 환경(SQLite 또는 PostgreSQL)에 맞게 정확히 입력되었는지 확인하세요.
- 의존성 오류: pip install -r requirements.txt 명령을 다시 실행하여 모든 패키지가 정상적으로 설치되었는지 확인하세요. 특히 bcrypt==4.0.1
- 서버 실행 오류:FastAPI나 Uvicorn 실행 시 발생하는 오류 메세지를 확인하여 문제를 파악하세요.

### 로그 확인

애플리케이션 실행 시 콘솔에서 경고 메시지를 확인하여 설정 문제를 파악할 수 있습니다.
