import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.project_schema import ApiResponse
from app.schemas.webhook_schema import GitHubWebhookResult
from app.services.github_webhook_service import GitHubWebhookError, process_github_push


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    if not settings.github_webhook_secret:
        return True

    if not signature_header:
        return False

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected_signature}"

    return hmac.compare_digest(expected_header, signature_header)


@router.post("/github", response_model=ApiResponse[GitHubWebhookResult])
async def handle_github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    db: Session = Depends(get_db),
) -> ApiResponse[GitHubWebhookResult]:
    payload_body = await request.body()

    if not verify_github_signature(payload_body, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub signature.",
        )

    if x_github_event != "push":
        return ApiResponse(
            data=GitHubWebhookResult(
                processed=False,
                reason="Only push events are supported.",
            ),
        )

    try:
        payload = await request.json()
        processed, reason, project, commit, task = process_github_push(
            db=db,
            payload=payload,
            delivery_id=x_github_delivery,
        )
        return ApiResponse(
            data=GitHubWebhookResult(
                processed=processed,
                reason=reason,
                project_id=project.id if project else None,
                commit_id=commit.id if commit else None,
                task_id=task.id if task else None,
            ),
        )
    except GitHubWebhookError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process GitHub webhook.",
        ) from exc
