import asyncio
from jobhunter.config import get_settings
from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
from jobhunter.adapters.parsing.text_extractor import extract_text
from jobhunter.adapters.parsing.llm_resume_parser import _normalize_parsed_fields
import json

async def debug():
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    
    file_bytes = open("Sami_Ullah_CV.docx", "rb").read()
    raw_text = extract_text(file_bytes, "Sami_Ullah_CV.docx")
    
    # Show what's in the CV about projects
    print("=== CV TEXT: PROJECT MENTIONS ===")
    for line in raw_text.splitlines():
        if any(w in line.lower() for w in ["project", "github", "linkedin", "rag", "agent", "copilot"]):
            print(f"  {line.strip()[:100]}")
    
    # Call LLM and see raw response BEFORE normalization
    from jobhunter.domain.profile import ParsedResume
    schema = json.dumps(ParsedResume.model_json_schema(), indent=2)
    result = await llm.complete_json(
        system="You are a resume parser. Extract structured data from resume text. Return JSON matching the schema. For fields you cannot determine, use null.",
        user=f"Parse this resume:\n\n{raw_text}",
        schema_hint=schema,
    )
    
    print("\n=== RAW LLM KEYS ===")
    print(list(result.keys()))
    
    # Check project-related keys
    print("\n=== PROJECT-RELATED DATA ===")
    for key in result:
        if any(w in key.lower() for w in ["project", "experience", "work", "employment", "career"]):
            val = result[key]
            print(f"  {key}: {type(val).__name__} = {json.dumps(val, indent=2)[:500]}")
    
    # Check URL-related data
    print("\n=== URL-RELATED DATA ===")
    for key in result:
        if any(w in key.lower() for w in ["github", "linkedin", "url", "link", "profile", "contact"]):
            val = result[key]
            print(f"  {key}: {json.dumps(val)[:200]}")
    
    # Now normalize and check what survives
    print("\n=== AFTER NORMALIZATION ===")
    normalized = _normalize_parsed_fields(result)
    print(f"  projects: {json.dumps(normalized.get('projects', 'MISSING'))[:300]}")
    print(f"  work_experiences: {json.dumps(normalized.get('work_experiences', 'MISSING'))[:300]}")
    print(f"  github_url: {normalized.get('github_url', 'MISSING')}")
    print(f"  linkedin_url: {normalized.get('linkedin_url', 'MISSING')}")

asyncio.run(debug())
