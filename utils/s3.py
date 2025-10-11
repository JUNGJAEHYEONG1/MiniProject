import boto3
import traceback
import uuid
import os
from botocore.exceptions import NoCredentialsError
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_REGION")

# S3 클라이언트 생성
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION
)


def upload_file_to_s3(
    file,  # FastAPI의 UploadFile 객체 또는 open()으로 연 파일 객체
    user_no: int,
    save_path: str = "user_eats"  # <-- 1. save_path 추가 및 기본값 설정
):
    """
    파일 객체를 S3에 업로드하고 해당 파일의 URL을 반환합니다.
    - file: FastAPI의 UploadFile 또는 open()으로 연 파일 객체
    - user_no: 사용자의 고유 번호
    - save_path: S3 내의 최상위 폴더 경로 (기본값: 'user_eats')
    """
    try:
        # 2. 파일 이름과 업로드할 파일 객체를 안전하게 가져옵니다.
        if isinstance(file, UploadFile):
            # FastAPI의 UploadFile 객체인 경우
            filename = file.filename
            file_to_upload = file.file
            content_type = file.content_type
        else:
            # open()으로 연 일반 파일 객체인 경우 (AI 생성 이미지)
            filename = os.path.basename(file.name)
            file_to_upload = file
            content_type = 'image/png' # AI 생성 이미지는 png로 가정

        # 3. S3에 저장될 최종 파일 경로를 구성합니다.
        #    - 유니크한 ID를 추가하여 파일 이름 중복을 방지합니다.
        #    - 예: user_eats/2/uuid-photo.jpg
        #    - 예: ai_recommendations/2/uuid-breakfast.png
        object_name = f"{save_path}/{user_no}/{uuid.uuid4()}-{filename}"

        # 파일 업로드
        s3_client.upload_fileobj(
            file_to_upload,
            AWS_S3_BUCKET_NAME,
            object_name,
            ExtraArgs={'ContentType': content_type}
        )

        # 업로드된 파일의 URL 생성
        file_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/{object_name}"

        print(f"S3 업로드 성공: {file_url}")
        return file_url

    except NoCredentialsError:
        print("AWS 자격 증명을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"S3 업로드 중 오류 발생: {e}")
        traceback.print_exc()
        return None