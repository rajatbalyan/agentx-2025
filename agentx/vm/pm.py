from pydantic import BaseModel
from typing import Optional


class SentryJobCreate(BaseModel):
    gh_token: str
    owner: str
    repo: str
    runner: bool
    runner_name: str
    cron: bool
    cron_interval: Optional[int] = 10



def create_cron_job(job: SentryJobCreate):
    pass