# MiniProject - AI 기반 식단 추천 시스템

이 프로젝트는 AI를 활용한 개인 맞춤형 식단 추천 시스템입니다.

## 주요 기능

- **개인 맞춤 식단 추천**: 사용자 프로필을 기반으로 한 아침/점심/저녁 식단 추천
- **YouTube 레시피 분석**: YouTube에서 레시피 영상을 검색하고 자막을 분석하여 재료와 조리법 추출
- **AI 이미지 생성**: 추천된 식단의 이미지를 AI로 생성
- **데이터베이스 연동**: SQLite/PostgreSQL 지원

## 프로젝트 구조

```
MiniProject/
├── api/                    # AI API 모듈
│   ├── __init__.py        # API 라우터 정의
│   ├── meal_to_food.py    # YouTube 레시피 분석
│   ├── meal_to_img.py     # AI 이미지 생성
│   ├── user_to_meal.py    # 식단 추천 생성
│   └── test4.py          # 통합 테스트
├── account/               # 사용자 계정 관리
├── ai/                   # AI 관련 기능
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
DATABASE_URL=sqlite:///./miniproject.db

# 선택적 환경변수
SECRET_KEY=your-secret-key
S3_BUCKET=your-s3-bucket
```

### 3. 애플리케이션 실행

```bash
uvicorn main:app --reload
```

## API 엔드포인트

### 식단 추천 API

- `POST /api/generate-recommendation/{user_id}`: 사용자별 맞춤 식단 추천 생성
- `POST /api/analyze-foods`: 음식 분석 (재료 및 레시피 추출)
- `POST /api/generate-images`: 식단 이미지 생성

### 상태 확인

- `GET /api/health`: API 상태 확인

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

### 일반적인 문제

1. **API 키 오류**: 환경변수가 올바르게 설정되었는지 확인하세요.
2. **데이터베이스 연결 오류**: DATABASE_URL이 올바른지 확인하세요.
3. **의존성 오류**: `pip install -r requirements.txt`를 다시 실행하세요.

### 로그 확인

애플리케이션 실행 시 콘솔에서 경고 메시지를 확인하여 설정 문제를 파악할 수 있습니다.
