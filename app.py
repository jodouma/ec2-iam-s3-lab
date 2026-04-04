import base64
import io
import mimetypes
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    CredentialRetrievalError,
    NoCredentialsError,
    PartialCredentialsError,
)
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont


app = Flask(__name__)

# Central lab configuration.
# Change the bucket dynamically by setting S3_BUCKET_NAME in the environment
# before starting the app. Default stays on the classroom bucket below.
AWS_REGION = os.getenv("AWS_REGION") or None
DEFAULT_S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "leaders-university-1337")
S3_UPLOAD_PREFIX = os.getenv("S3_UPLOAD_PREFIX", "uploads/")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
ACTIVE_CONFIG = {"bucket_name": DEFAULT_S3_BUCKET_NAME}
APP_SIGNATURE = "Leaders University - Youssef Douma"


STATE_DETAILS = {
    "NO_AWS_ACCESS": {
        "code": "NO_AWS_ACCESS",
        "title": "DO NOT HAVE ACCESS TO AWS / S3",
        "summary": "The application could not find usable AWS credentials, so it cannot call STS or S3.",
        "likely_missing_action": "No valid AWS credentials available (credential chain did not resolve)",
        "proposed_fix": "Run with AWS credentials locally, or attach an IAM role / instance profile to the EC2 instance.",
        "theme": "danger",
    },
    "NO_LIST_ACCESS": {
        "code": "NO_LIST_ACCESS",
        "title": "DO NOT HAVE ACCESS TO LIST THE BUCKET",
        "summary": "AWS identity exists, but bucket listing is blocked.",
        "likely_missing_action": "s3:ListBucket",
        "proposed_fix": "Grant s3:ListBucket on the bucket ARN to the IAM role or user used by this app.",
        "theme": "warning",
    },
    "NO_READ_ACCESS": {
        "code": "NO_READ_ACCESS",
        "title": "DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS",
        "summary": "The app can list the bucket, but it cannot read one or more image objects.",
        "likely_missing_action": "s3:GetObject",
        "proposed_fix": "Grant s3:GetObject on the image object keys in the bucket.",
        "theme": "warning",
    },
    "NO_WRITE_ACCESS": {
        "code": "NO_WRITE_ACCESS",
        "title": "DO NOT HAVE WRITE ACCESS TO THE BUCKET",
        "summary": "The app can read images, but uploading the generated demo image failed.",
        "likely_missing_action": "s3:PutObject",
        "proposed_fix": "Grant s3:PutObject on the upload prefix used by the application.",
        "theme": "warning",
    },
    "FULL_SUCCESS": {
        "code": "FULL_SUCCESS",
        "title": "FULL SUCCESS: EC2 ROLE / AWS ACCESS IS WORKING",
        "summary": "Credentials, listing, reading, and uploading all succeeded.",
        "likely_missing_action": "None",
        "proposed_fix": "No fix needed. Use this state to explain how least privilege still enabled exactly the required actions.",
        "theme": "success",
    },
}


def current_bucket_name() -> str:
    return ACTIVE_CONFIG["bucket_name"]


def set_bucket_name(bucket_name: str) -> str:
    cleaned = (bucket_name or "").strip()
    if not cleaned:
        raise ValueError("Bucket name cannot be empty.")
    ACTIVE_CONFIG["bucket_name"] = cleaned
    return cleaned


def aws_session() -> boto3.session.Session:
    return boto3.session.Session(region_name=AWS_REGION)


def aws_clients() -> Tuple[Any, Any, boto3.session.Session]:
    session = aws_session()
    s3 = session.client("s3")
    sts = session.client("sts")
    return s3, sts, session


def serialize_exception(exc: Exception) -> Dict[str, Any]:
    details: Dict[str, Any] = {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }

    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        meta = exc.response.get("ResponseMetadata", {})
        details.update(
            {
                "aws_error_code": err.get("Code"),
                "aws_error_message": err.get("Message"),
                "http_status": meta.get("HTTPStatusCode"),
                "request_id": meta.get("RequestId"),
            }
        )

    details["trace"] = traceback.format_exc(limit=2)
    return details


def is_access_denied(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        code = (exc.response.get("Error", {}).get("Code") or "").lower()
        return code in {"accessdenied", "accessdeniedexception", "unauthorizedoperation", "allaccessdisabled"}
    return False


def infer_credential_source(session: boto3.session.Session) -> Optional[str]:
    creds = session.get_credentials()
    if not creds:
        return None

    method = getattr(creds, "method", None)
    mapping = {
        "env": "Environment variables",
        "shared-credentials-file": "AWS shared credentials file/profile",
        "config-file": "AWS config profile",
        "assume-role": "AssumeRole profile",
        "assume-role-with-web-identity": "Web identity role",
        "iam-role": "EC2 instance metadata / IAM role",
        "container-role": "Container task role",
        "custom-process": "Credential process",
        "sso": "AWS IAM Identity Center / SSO",
    }
    return mapping.get(method, method)


def build_demo_image_bytes(text: Optional[str] = None) -> bytes:
    width, height = 900, 420
    image = Image.new("RGB", (width, height), color=(24, 28, 47))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        blue = int(140 + (y / max(height - 1, 1)) * 70)
        draw.line((0, y, width, y), fill=(40, 60 + (y % 40), blue))

    banner_text = text or f"IAM Lab Demo\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    font = ImageFont.load_default()

    draw.rounded_rectangle((55, 55, width - 55, height - 55), radius=28, outline=(255, 255, 255), width=4)
    draw.ellipse((80, 80, 180, 180), fill=(255, 195, 0))
    draw.ellipse((720, 230, 840, 350), fill=(130, 255, 190))
    draw.rectangle((130, 280, 760, 315), fill=(255, 255, 255))
    draw.multiline_text((220, 125), banner_text, fill=(255, 255, 255), font=font, spacing=10)
    draw.text((130, 290), "EC2 IAM Role + S3 Demo Upload", fill=(24, 28, 47), font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def make_upload_key() -> str:
    prefix = S3_UPLOAD_PREFIX if S3_UPLOAD_PREFIX.endswith("/") else f"{S3_UPLOAD_PREFIX}/"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}iam-role-demo-{stamp}.png"


def make_uploaded_file_key(filename: str) -> str:
    prefix = S3_UPLOAD_PREFIX if S3_UPLOAD_PREFIX.endswith("/") else f"{S3_UPLOAD_PREFIX}/"
    safe_name = os.path.basename(filename or "upload.bin").replace(" ", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}{stamp}-{safe_name}"


def existing_demo_image_key(s3: Any) -> Optional[str]:
    """
    Keep demo-image generation classroom-friendly by reusing an existing generated
    demo image when one is already present instead of filling the bucket with near-
    identical files.
    """
    prefix = S3_UPLOAD_PREFIX if S3_UPLOAD_PREFIX.endswith("/") else f"{S3_UPLOAD_PREFIX}/"
    response = s3.list_objects_v2(Bucket=current_bucket_name(), Prefix=prefix, MaxKeys=100)
    for item in response.get("Contents", []):
        key = item.get("Key", "")
        if os.path.basename(key).startswith("iam-role-demo-") and key.lower().endswith(".png"):
            return key
    return None


def list_candidate_images(s3: Any, limit: int = 200) -> List[Dict[str, Any]]:
    response = s3.list_objects_v2(Bucket=current_bucket_name(), MaxKeys=limit)
    candidates: List[Dict[str, Any]] = []

    for item in response.get("Contents", []):
        key = item.get("Key", "")
        if key.lower().endswith(IMAGE_EXTENSIONS):
            candidates.append(
                {
                    "key": key,
                    "size": item.get("Size"),
                    "last_modified": item.get("LastModified").isoformat() if item.get("LastModified") else None,
                }
            )
    return candidates


def image_response_payload(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            **image,
            "url": f"/image/{base64.urlsafe_b64encode(image['key'].encode()).decode()}",
        }
        for image in images
    ]


def attempt_read_test(s3: Any, image_keys: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not image_keys:
        return True, None, None

    first_key = image_keys[0]["key"]
    try:
        s3.get_object(Bucket=current_bucket_name(), Key=first_key, Range="bytes=0-63")
        return True, {"tested_key": first_key, "message": "Successfully read bytes from an image object."}, None
    except Exception as exc:  # noqa: BLE001
        return False, None, serialize_exception(exc)


def attempt_upload_test(s3: Any) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    existing_key = existing_demo_image_key(s3)
    if existing_key:
        return True, existing_key, None

    key = make_upload_key()
    body = build_demo_image_bytes()
    try:
        s3.put_object(
            Bucket=current_bucket_name(),
            Key=key,
            Body=body,
            ContentType="image/png",
            Metadata={"generated-by": "iam-role-s3-lab"},
        )
        return True, key, None
    except Exception as exc:  # noqa: BLE001
        return False, None, serialize_exception(exc)


def empty_diagnostics() -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bucket": current_bucket_name(),
        "region": AWS_REGION,
        "credential_source": None,
        "credentials_available": False,
        "identity": None,
        "steps": {
            "credentials": {"ok": False, "details": None, "error": None},
            "list_bucket": {"ok": False, "details": None, "error": None},
            "read_object": {"ok": False, "details": None, "error": None},
            "upload_object": {"ok": False, "details": None, "error": None},
        },
        "images": [],
        "state": STATE_DETAILS["NO_AWS_ACCESS"],
    }


def run_diagnostics() -> Dict[str, Any]:
    report = empty_diagnostics()

    try:
        s3, sts, session = aws_clients()
        report["credential_source"] = infer_credential_source(session)

        session.get_credentials().get_frozen_credentials()  # type: ignore[union-attr]
        report["credentials_available"] = True
        report["steps"]["credentials"] = {
            "ok": True,
            "details": {"message": "Credential chain returned usable credentials."},
            "error": None,
        }
    except (NoCredentialsError, PartialCredentialsError, CredentialRetrievalError, AttributeError) as exc:
        report["steps"]["credentials"] = {"ok": False, "details": None, "error": serialize_exception(exc)}
        report["state"] = STATE_DETAILS["NO_AWS_ACCESS"]
        return report
    except Exception as exc:  # noqa: BLE001
        report["steps"]["credentials"] = {"ok": False, "details": None, "error": serialize_exception(exc)}
        report["state"] = STATE_DETAILS["NO_AWS_ACCESS"]
        return report

    try:
        identity = sts.get_caller_identity()
        report["identity"] = {
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }
    except Exception as exc:  # noqa: BLE001
        report["identity"] = {"error": serialize_exception(exc)}

    try:
        images = list_candidate_images(s3)
        report["images"] = images
        report["steps"]["list_bucket"] = {
            "ok": True,
            "details": {
                "message": "Bucket listing succeeded.",
                "image_count": len(images),
            },
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        report["steps"]["list_bucket"] = {"ok": False, "details": None, "error": serialize_exception(exc)}
        report["state"] = STATE_DETAILS["NO_LIST_ACCESS"] if is_access_denied(exc) else STATE_DETAILS["NO_LIST_ACCESS"]
        return report

    can_read, read_details, read_error = attempt_read_test(s3, report["images"])
    report["steps"]["read_object"] = {"ok": can_read, "details": read_details, "error": read_error}
    if not can_read:
        report["state"] = STATE_DETAILS["NO_READ_ACCESS"]
        return report

    upload_ok, upload_key, upload_error = attempt_upload_test(s3)
    report["steps"]["upload_object"] = {
        "ok": upload_ok,
        "details": {"message": "Upload test succeeded.", "key": upload_key} if upload_ok else None,
        "error": upload_error,
    }
    if not upload_ok:
        report["state"] = STATE_DETAILS["NO_WRITE_ACCESS"]
        return report

    report["state"] = STATE_DETAILS["FULL_SUCCESS"]
    return report


def fetch_image_bytes(key: str) -> Tuple[io.BytesIO, str]:
    s3, _, _ = aws_clients()
    response = s3.get_object(Bucket=current_bucket_name(), Key=key)
    content_type = response.get("ContentType") or "application/octet-stream"
    body = response["Body"].read()
    return io.BytesIO(body), content_type


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        bucket_name=current_bucket_name(),
        default_bucket_name=DEFAULT_S3_BUCKET_NAME,
        aws_region=AWS_REGION or "auto",
        upload_prefix=S3_UPLOAD_PREFIX,
        app_signature=APP_SIGNATURE,
    )


@app.post("/api/config/bucket")
def api_config_bucket():
    payload = request.get_json(silent=True) or {}
    try:
        bucket_name = set_bucket_name(payload.get("bucket_name", ""))
        return jsonify({"ok": True, "bucket_name": bucket_name, "message": "Active bucket updated."})
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.get("/api/diagnostics")
def api_diagnostics():
    return jsonify(run_diagnostics())


@app.get("/api/images")
def api_images():
    try:
        s3, _, _ = aws_clients()
        images = image_response_payload(list_candidate_images(s3))
        return jsonify({"ok": True, "images": images, "count": len(images)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "images": [], "count": 0, "error": serialize_exception(exc)}), 403 if is_access_denied(exc) else 500


@app.get("/image/<encoded_key>")
def image_proxy(encoded_key: str):
    key = base64.urlsafe_b64decode(encoded_key.encode()).decode()
    image_io, content_type = fetch_image_bytes(key)
    return send_file(image_io, mimetype=content_type, download_name=os.path.basename(key))


@app.post("/api/upload-demo-image")
def api_upload_demo_image():
    if request.files:
        s3, _, _ = aws_clients()
        uploaded = []

        try:
            for file_storage in request.files.getlist("files"):
                if not file_storage or not file_storage.filename:
                    continue

                file_bytes = file_storage.read()
                key = make_uploaded_file_key(file_storage.filename)
                content_type = file_storage.mimetype or mimetypes.guess_type(file_storage.filename)[0] or "application/octet-stream"

                s3.put_object(
                    Bucket=current_bucket_name(),
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type,
                    Metadata={"uploaded-by": "iam-role-s3-lab", "source": "local-file-picker"},
                )
                uploaded.append({"key": key, "filename": file_storage.filename, "content_type": content_type})

            return jsonify({"ok": True, "message": "Files uploaded successfully.", "uploaded": uploaded, "count": len(uploaded)})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "message": "File upload failed.", "error": serialize_exception(exc)}), 403 if is_access_denied(exc) else 500

    payload = request.get_json(silent=True) or {}
    requested_text = payload.get("text")
    s3, _, _ = aws_clients()

    existing_key = existing_demo_image_key(s3)
    if existing_key:
        return jsonify(
            {
                "ok": True,
                "message": "Existing demo image reused to avoid duplicates.",
                "key": existing_key,
                "reused_existing": True,
            }
        )

    key = make_upload_key()
    body = build_demo_image_bytes(requested_text)

    try:
        s3.put_object(
            Bucket=current_bucket_name(),
            Key=key,
            Body=body,
            ContentType="image/png",
            Metadata={"generated-by": "iam-role-s3-lab", "lab": "leaders-university"},
        )
        return jsonify({"ok": True, "message": "Demo image uploaded successfully.", "key": key})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "message": "Upload failed.", "error": serialize_exception(exc)}), 403 if is_access_denied(exc) else 500


@app.post("/api/refresh")
def api_refresh():
    return jsonify(run_diagnostics())


@app.errorhandler(BotoCoreError)
def handle_botocore_error(exc: BotoCoreError):
    return jsonify({"ok": False, "error": serialize_exception(exc)}), 500


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=os.getenv("FLASK_ENV") == "development")