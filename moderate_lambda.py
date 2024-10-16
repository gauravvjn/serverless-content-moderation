import boto3
import enum
import logging
from datetime import datetime, timezone


logger = logging.getLogger()
logger.setLevel("INFO")

dynamodb = boto3.resource("dynamodb")
rekognition = boto3.client("rekognition")

bucket_name = "gj-uploaded-image"
table_name = "ImageMetadata"


class ImageStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    MODERATED = "MODERATED"
    MODERATED_AND_RESIZED = "MODERATED_AND_RESIZED"


class ModerationResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PROCESSING_ERROR = "PROCESSING_ERROR"


def moderate_image(image_id):
    # Perform content moderation using ML model or third-party API
    # Here we are using AWS rekognition for POC purpose.
    logger.info("Moderation has started - image_id: %s", image_id)

    moderation_flags = None
    try:
        response = rekognition.detect_moderation_labels(
            Image={"S3Object": {"Bucket": bucket_name, "Name": image_id}}
        )
    except Exception:
        logger.exception("Exception occurred during moderation  - image_id: %s", image_id)
        return ModerationResult.PROCESSING_ERROR, moderation_flags

    moderation_labels = response["ModerationLabels"]
    moderation_result = ModerationResult.FAIL if moderation_labels else ModerationResult.PASS
    moderation_flags = ", ".join([label["Name"] for label in moderation_labels])
    logger.info("Moderation completed - image_id: %s, moderation_result: %s", image_id, moderation_result)
    return moderation_result, moderation_flags


def lambda_handler(event, context):
    image_id = event["image_id"]

    moderation_result, moderation_flags = moderate_image(image_id)
    if moderation_result not in [ModerationResult.PASS, ModerationResult.FAIL]:
        return {
            "image_id": image_id,
            "moderation_result": moderation_result,
        }

    try:
        table = dynamodb.Table(table_name)
        table.update_item(
            Key={"image_id": image_id},
            UpdateExpression="set image_status=:image_status, moderation_result=:moderation_result, moderation_flags=:moderation_flags, updated_at=:updated_at",
            ExpressionAttributeValues={
                ":image_status": ImageStatus.MODERATED,
                ":moderation_result": moderation_result,
                ":moderation_flags": moderation_flags,
                ":updated_at": str(datetime.now(timezone.utc)),
            },
        )
        logger.info("Status updated in DDB - image_id: %s", image_id)
    except Exception:
        logger.exception("Couldn't update the status in DDB - image_id: %s", image_id)

    return {
        "image_id": image_id,
        "image_status": ImageStatus.MODERATED,
        "moderation_result": moderation_result,
        "moderation_flags": moderation_flags,
    }
