import json
import base64
import enum
import uuid
import boto3
import logging
from datetime import datetime, timezone


logger = logging.getLogger()
logger.setLevel("INFO")

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
stepfunctions = boto3.client("stepfunctions")

upload_bucket_name = "gj-uploaded-image"
table_name = "ImageMetadata"
stepfunctions_arn = "arn:aws:states:ap-south-1:850995540176:stateMachine:ContentModerationAndResizeStepFunction"



class ImageStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    MODERATED = "MODERATED"
    MODERATED_AND_RESIZED = "MODERATED_AND_RESIZED"


def lambda_handler(event, context):
    image_data = event["body-json"]
    image_id = str(uuid.uuid4())

    try:
        s3.put_object(
            Bucket=upload_bucket_name,
            Key=image_id,
            Body=base64.b64decode(image_data),
        )
        logger.info("Image uploaded - image_id: %s, bucket: %s", image_id, upload_bucket_name)
    except Exception as e:
        logger.exception("Couldn't upload the image: ")
        return {
            "image_status": ImageStatus.UPLOAD_FAILED,
            "error": repr(e),
        }
    datetime.utcnow().isoformat()
    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item={
            "image_id": image_id,
            "image_status": ImageStatus.UPLOADED,
            "created_at": str(datetime.now(timezone.utc)),
            "updated_at": str(datetime.now(timezone.utc)),
        })
        logger.info("Upload event added to DDB - image_id: %s", image_id)
    except Exception:
        logger.exception("Couldn't update the upload status in DDB - image_id: %s", image_id)


    try:
        stepfunctions.start_execution(
            stateMachineArn=stepfunctions_arn, input=json.dumps({"image_id": image_id})
        )
        logger.info("StepFunction triggered - image_id: %s", image_id)
    except Exception:
        logger.exception("Couldn't execute the StepFunctions - image_id: %s", image_id)

    return {
        "image_id": image_id,
        "image_status": ImageStatus.UPLOADED,
    }
