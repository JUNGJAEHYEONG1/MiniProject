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


import boto3
import traceback
import uuid
import os
from botocore.exceptions import NoCredentialsError
from fastapi import UploadFile

# ... (기존 S3 클라이언트 설정) ...


def upload_file_to_s3(
    file,  # FastAPI의 UploadFile 객체 또는 open()으로 연 파일 객체
    user_no: int,
    save_path: str = "user_eats"
):
    """
    파일 객체를 S3에 업로드하고 해당 파일의 URL을 반환합니다.
    """
    try:
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 이 부분이 수정된 핵심 로직입니다 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

        # 1. isinstance 대신 hasattr를 사용하여 객체의 특징으로 타입을 구별합니다.
        if hasattr(file, 'filename'):
            # .filename 속성이 있으면 FastAPI의 UploadFile 객체로 간주합니다.
            filename = file.filename
            file_to_upload = file.file
            content_type = file.content_type
        elif hasattr(file, 'name'):
            # .name 속성이 있으면 open()으로 연 일반 파일 객체로 간주합니다.
            filename = os.path.basename(file.name)
            file_to_upload = file
            content_type = 'image/png'  # AI 생성 이미지는 png로 가정
        else:
            # 두 속성 모두 없는 경우, 예외를 발생시킵니다.
            raise ValueError("Unsupported file type provided to upload_file_to_s3")

        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        # S3에 저장될 최종 파일 경로를 구성합니다.
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