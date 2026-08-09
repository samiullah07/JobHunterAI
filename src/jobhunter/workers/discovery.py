import asyncio
import structlog

import httpx

from jobhunter.workers.celery_app import app
from jobhunter.application.use_cases.job_discovery import JobDiscoveryService
from jobhunter.infrastructure.db.unit_of_work import unit_of_work
from jobhunter.adapters.boards.greenhouse import GreenhouseConnector
from jobhunter.adapters.boards.lever import LeverConnector
from jobhunter.adapters.boards.remoteok import RemoteOkConnector
from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import JobSearchQuery

# Import repositories at module level to avoid circular imports
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository

logger = structlog.get_logger()


async def discover_jobs_scheduled():
    """Main job discovery logic for scheduled tasks."""
    client = httpx.AsyncClient()
    try:
        greenhouse_connector = GreenhouseConnector(client)
        lever_connector = LeverConnector(client)
        remoteok_connector = RemoteOkConnector(client)

        async with unit_of_work() as session:
            connectors = [greenhouse_connector, lever_connector, remoteok_connector]

            job_repo = SQLAlchemyJobRepository(session)
            company_repo = SQLAlchemyCompanyRepository(session)

            service = JobDiscoveryService(
                connectors=connectors,
                job_repo=job_repo,
                company_repo=company_repo,
                session=session,
            )

            # --- RemoteOK (no board token needed) ---
            remoteok_query = JobSearchQuery(keywords="python", location="", limit=50)
            remoteok_report = await service.discover(query=remoteok_query, sources=[JobSource.REMOTEOK])

            # --- Greenhouse companies (each needs a board_token) ---
            greenhouse_boards = ["anthropic", "scaleai", "databricks", "mongodb", "datadog", "elastic", "gitlab", "cloudflare", "stripe", "figma"]
            for board in greenhouse_boards:
                gh_query = JobSearchQuery(board_token=board, limit=50)
                gh_report = await service.discover(query=gh_query, sources=[JobSource.GREENHOUSE])
                for k, v in gh_report.per_source.items():
                    logger.info("greenhouse_board_done", board=board, fetched=v.fetched, new=v.new)

            # --- Lever companies (each needs a board_token) ---
            lever_boards = ["wpromote", "revealtech", "2A"]
            for board in lever_boards:
                lv_query = JobSearchQuery(board_token=board, limit=50)
                lv_report = await service.discover(query=lv_query, sources=[JobSource.LEVER])
                for k, v in lv_report.per_source.items():
                    logger.info("lever_board_done", board=board, fetched=v.fetched, new=v.new)

            # Use remoteok_report as the main report for return value
            report = remoteok_report

            # Log results per source
            for source_tag, counts in report.per_source.items():
                logger.info(
                    "discovery_completed",
                    source=source_tag,
                    fetched=counts.fetched,
                    new=counts.new,
                    duplicates=counts.duplicates,
                    errors=counts.errors,
                )

            # Return structured results
            result = {
                "greenhouse": report.per_source.get("greenhouse", {}),
                "lever": report.per_source.get("lever", {}),
                "remoteok": report.per_source.get("remoteok", {}),
            }
            return result
    finally:
        await client.aclose()


@app.task(name="discover_jobs")
def discover_jobs_task():
    """Celery task wrapper for scheduled job discovery."""
    return asyncio.run(discover_jobs_scheduled())
