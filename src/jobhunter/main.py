"""FastAPI entrypoint."""

from fastapi import FastAPI

from jobhunter import __version__
from jobhunter.api.applications import router as applications_router
from jobhunter.api.cover_letters import router as cover_letters_router
from jobhunter.api.jobs import router as jobs_router
from jobhunter.api.profiles import router as profiles_router
from jobhunter.api.resumes import router as resumes_router
from jobhunter.api.review import router as review_router
from jobhunter.api.scoring import router as scoring_router
from jobhunter.common.logging import configure_logging
from jobhunter.config import get_settings

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="JobHunter Agent", version=__version__)
app.include_router(profiles_router)
app.include_router(jobs_router)
app.include_router(scoring_router)
app.include_router(resumes_router)
app.include_router(cover_letters_router)
app.include_router(applications_router)
app.include_router(review_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "env": settings.app_env}
