from pydantic import BaseModel


class GitHubWebhookResult(BaseModel):
    processed: bool
    reason: str | None = None
    project_id: str | None = None
    commit_id: str | None = None
    task_id: str | None = None
