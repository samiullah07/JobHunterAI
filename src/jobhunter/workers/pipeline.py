"""One-click pipeline orchestrator — discover → generate → queue."""
import asyncio
import structlog
from typing import Callable

logger = structlog.get_logger()


class PipelineResult:
    """Collects results from each pipeline step."""
    def __init__(self):
        self.steps_completed = []
        self.steps_failed = []
        self.discovery = None
        self.generation = None
        self.queueing = None
        self.error = None

    @property
    def success(self) -> bool:
        return len(self.steps_failed) == 0

    def summary(self) -> dict:
        return {
            "completed": self.steps_completed,
            "failed": self.steps_failed,
            "discovery": self.discovery,
            "generation": self.generation,
            "queueing": self.queueing,
            "error": self.error,
        }


async def run_full_pipeline(
    generation_limit: int = 5,
    on_progress: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Run the full job-hunting pipeline: discover → generate → queue.

    Args:
        generation_limit: How many top matches to generate CVs for (default 5).
        on_progress: Optional callback(step_name, message) for progress updates.

    Returns:
        PipelineResult with per-step outcomes.
    """
    result = PipelineResult()

    def _progress(step: str, msg: str) -> None:
        logger.info("pipeline_progress", step=step, message=msg)
        if on_progress:
            on_progress(step, msg)

    # --- Step 1: Discover ---
    _progress("discover", "Fetching jobs from Greenhouse, Lever, RemoteOK...")
    try:
        from jobhunter.workers.discovery import discover_jobs_scheduled
        discovery_result = await discover_jobs_scheduled()
        result.discovery = discovery_result
        result.steps_completed.append("discover")
        _progress("discover", f"Discovery complete: {discovery_result}")
    except Exception as exc:
        logger.error("pipeline_discover_failed", error=str(exc))
        result.steps_failed.append("discover")
        result.error = f"Discovery failed: {type(exc).__name__}"
        # Continue to generation with existing jobs even if discovery fails
        _progress("discover", f"Discovery failed: {type(exc).__name__}. Using existing jobs.")

    # --- Step 2: Generate ---
    _progress("generate", f"Generating tailored CVs and cover letters (top {generation_limit} matches)...")
    try:
        from jobhunter.workers.generation import generate_for_top_matches
        gen_result = await generate_for_top_matches(limit=generation_limit)
        result.generation = gen_result
        result.steps_completed.append("generate")
        _progress("generate", f"Generated {gen_result.get('generated', 0)} CVs + cover letters")
    except Exception as exc:
        logger.error("pipeline_generate_failed", error=str(exc))
        result.steps_failed.append("generate")
        result.error = f"Generation failed: {type(exc).__name__}"
        _progress("generate", f"Generation failed: {type(exc).__name__}. Continuing...")

    # --- Step 3: Queue ---
    _progress("queue", "Creating applications for review...")
    try:
        from jobhunter.workers.queueing import queue_applications_for_review
        queue_result = await queue_applications_for_review()
        result.queueing = queue_result
        result.steps_completed.append("queue")
        _progress("queue", f"Queued {queue_result.get('queued', 0)} applications for review")
    except Exception as exc:
        logger.error("pipeline_queue_failed", error=str(exc))
        result.steps_failed.append("queue")
        result.error = f"Queueing failed: {type(exc).__name__}"
        _progress("queue", f"Queueing failed: {type(exc).__name__}")

    # --- Summary ---
    logger.info(
        "pipeline_complete",
        completed=result.steps_completed,
        failed=result.steps_failed,
        discovery=result.discovery,
        generation=result.generation,
        queueing=result.queueing,
    )
    return result