import asyncio
from jobhunter.config import get_settings
from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
from jobhunter.adapters.parsing.llm_resume_parser import LlmResumeParser

async def test():
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(api_key=settings.groq_api_key, base_url=settings.groq_base_url, model=settings.groq_model, usage_tracker=tracker)
    parser = LlmResumeParser(llm=llm)
    
    fb = open("Sami_Ullah_CV.docx", "rb").read()
    parsed = await parser.parse(fb, "Sami_Ullah_CV.docx")
    
    print(f"full_name: {parsed.full_name}")
    print(f"skills: {len(parsed.skills) if parsed.skills else 0}")
    print(f"projects: {len(parsed.projects) if parsed.projects else 0}")
    print(f"github_url: {parsed.github_url}")
    print(f"linkedin_url: {parsed.linkedin_url}")
    
    if parsed.projects:
        for p in parsed.projects:
            print(f"  PROJECT: {p.name} | url={p.url}")
    else:
        print("  PROJECTS IS NONE OR EMPTY")
        print(f"  raw type: {type(parsed.projects)}")

asyncio.run(test())
