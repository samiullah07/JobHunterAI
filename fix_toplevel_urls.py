path = "src/jobhunter/adapters/parsing/llm_resume_parser.py"
content = open(path, encoding="utf-8").read()

# Add top-level github/linkedin extraction at the end of the normalize function, before return
old_return = "    return d"
new_return = """    # Top-level github/linkedin (Groq sometimes puts them here, not in contact/profiles)
    if "github_url" not in d:
        for key in ("github", "githubUrl", "github_url"):
            if key in d:
                url = d.pop(key)
                if url and not str(url).startswith("http"):
                    url = "https://" + str(url)
                d["github_url"] = url
                break
    if "linkedin_url" not in d:
        for key in ("linkedin", "linkedinUrl", "linkedin_url"):
            if key in d:
                url = d.pop(key)
                if url and not str(url).startswith("http"):
                    url = "https://" + str(url)
                d["linkedin_url"] = url
                break

    return d"""

# Replace only the LAST occurrence of "    return d" (which is the normalize function's return)
# Find the normalize function and replace its return
idx = content.rfind(old_return)
if idx > -1:
    content = content[:idx] + new_return + content[idx + len(old_return):]
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: added top-level github/linkedin extraction")
else:
    print("FAILED")
