import os
from celery import Celery

# Load configuration from environment
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "jobhunter",
    broker=broker_url,
    backend=backend_url,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

# Autodiscover tasks from ["jobhunter.workers"]
app.autodiscover_tasks(["jobhunter.workers"])

print(f"Celery initialized: broker={broker_url}")
from jobhunter.workers.celery_app import app