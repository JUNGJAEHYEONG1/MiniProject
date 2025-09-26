import boto3
import os
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile
import traceback

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


def upload_file_to_s3(file: UploadFile, user_no: int):
    """
    UploadFile 객체를 S3에 업로드하고 해당 파일의 URL을 반환합니다.
    """
    try:
        # S3에 저장될 파일 경로 설정 (UploadFile 객체의 filename 속성 사용)
        object_name = f"{user_no}/{file.filename}"

        # 파일 업로드 (UploadFile 객체의 file 속성을 upload_fileobj에 전달)
        s3_client.upload_fileobj(
            file.file,
            AWS_S3_BUCKET_NAME,
            object_name,
            ExtraArgs={'ContentType': file.content_type}  # UploadFile 객체의 content_type 속성 사용
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
        traceback.print_exc()  # <-- 이 라인을 추가하면 전체 오류 스택을 볼 수 있습니다.
        return None