import boto3
from PIL import Image
import enum
import io
import logging
from datetime import datetime, timezone


logger = logging.getLogger()
logger.setLevel("INFO")

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

uploaded_images_bucket_name = "gj-uploaded-image"
resized_images_bucket_name = "gj-resized-image"
table_name = "ImageMetadata"
max_image_size = (800, 800)


class ImageStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    MODERATED = "MODERATED"
    MODERATED_AND_RESIZED = "MODERATED_AND_RESIZED"


class ModerationResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PROCESSING_ERROR = "PROCESSING_ERROR"


def resize_image(image_id, image_obj):
    image = Image.open(io.BytesIO(image_obj["Body"].read()))

    if image.size[0] <= max_image_size[0] and image.size[1] <= max_image_size[1]:
        logger.info("Resizing isn't required. Image is already in the allowed size - image_id: %s", image_id)
        return False, None

    logger.info("Resizing the image - image_id: %s", image_id)
    image.thumbnail(max_image_size)
    resized_buffer = io.BytesIO()
    image.save(resized_buffer, format="JPEG")
    logger.info("Image Resizing has been done - image_id: %s", image_id)
    resized_buffer.seek(0)
    return True, resized_buffer


def lambda_handler(event, context):
    image_id = event["image_id"]
    moderation_result = event["moderation_result"]

    if moderation_result != ModerationResult.PASS:
        return {"image_id": image_id, "message": "Image moderation didn't pass. No resizing is required."}

    image_obj = s3.get_object(Bucket=uploaded_images_bucket_name, Key=image_id)

    try:
        is_resized, resized_buffer = resize_image(image_id, image_obj)
    except Exception as e:
        logger.exception("Exception occurred while resizing the image - image_id: %s", image_id)
        return {"image_id": image_id, "message": e.__doc__, "error": repr(e)}

    if not is_resized:
        return {
            "image_id": image_id,
            "message": "Image is already in the allowed size. No resizing is required."
        }

    # Save the resized image back to S3
    s3.put_object(
        Bucket=resized_images_bucket_name, Key=image_id, Body=resized_buffer
    )

    try:
        table = dynamodb.Table(table_name)
        table.update_item(
            Key={"image_id": image_id},
            UpdateExpression="set image_status=:image_status, updated_at=:updated_at",
            ExpressionAttributeValues={
                ":image_status": ImageStatus.MODERATED_AND_RESIZED,
                ":updated_at": str(datetime.now(timezone.utc)),
            },
        )
        logger.info("Status updated in DDB - image_id: %s", image_id)
    except Exception:
        logger.exception("Couldn't update the status in DDB - image_id: %s", image_id)

    return {
        "image_id": image_id,
        "image_status": ImageStatus.MODERATED_AND_RESIZED,
    }
