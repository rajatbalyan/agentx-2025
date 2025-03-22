from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from gh_controller import GitHubController
from pm import create_cron_job
app = FastAPI()


class SentryJobCreate(BaseModel):
    gh_token: str
    owner: str
    repo: str
    runner: bool
    runner_name: str
    cron: bool
    cron_interval: Optional[int] = 10


@app.get('/')
def health_check():
    return {"success": True}


@app.post('/create_sentry_job')
async def sentry_job(job: SentryJobCreate):
    try:
        gh_controller = GitHubController(job.gh_token, job.owner, job.repo)
        if(job.runner):
            gh_controller.register_self_hosted_runner(job.runner_name)
        if(job.cron):
            create_cron_job(job)
        return {
            "success": True, 
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create sentry job: {str(e)}"
        )