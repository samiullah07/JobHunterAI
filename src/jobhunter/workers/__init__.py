"""Celery task workers for autonomous pipeline."""
from .celery_app import app
from .discovery import discover_jobs_task