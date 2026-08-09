from jobhunter.workers.celery_app import app
from celery.schedules import crontab

app.conf.beat_schedule = {
    'discover-jobs-every-12h': {
        'task': 'discover_jobs',
        'schedule': crontab(minute=0, hour='*/12'),
    },
}

print("Beat schedule configured: discover_jobs every 12 hours")