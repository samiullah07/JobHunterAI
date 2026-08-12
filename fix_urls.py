path = "src/jobhunter/adapters/parsing/llm_resume_parser.py"
content = open(path, encoding="utf-8").read()

# Fix: add github/linkedin (without _url suffix) to the contact extraction
old_github = '''        for key in ("github", "github_url", "githubUrl"):
            if key in profiles and "github_url" not in d:
                d["github_url"] = profiles[key]'''

new_github = '''        for key in ("github", "github_url", "githubUrl"):
            if key in profiles and "github_url" not in d:
                url = profiles[key]
                if url and not url.startswith("http"):
                    url = "https://" + url
                d["github_url"] = url'''

if old_github in content:
    content = content.replace(old_github, new_github)
    print("FIXED: github URL with https prefix")
else:
    print("github block not found")

old_linkedin = '''        for key in ("linkedin", "linkedin_url", "linkedinUrl"):
            if key in profiles and "linkedin_url" not in d:
                d["linkedin_url"] = profiles[key]'''

new_linkedin = '''        for key in ("linkedin", "linkedin_url", "linkedinUrl"):
            if key in profiles and "linkedin_url" not in d:
                url = profiles[key]
                if url and not url.startswith("http"):
                    url = "https://" + url
                d["linkedin_url"] = url'''

if old_linkedin in content:
    content = content.replace(old_linkedin, new_linkedin)
    print("FIXED: linkedin URL with https prefix")
else:
    print("linkedin block not found")

# Also extract github/linkedin from CONTACT dict (not just profiles dict)
# The normalizer already handles the profiles dict, but contact dict has them too
old_contact_end = '''        if "location" not in d and "location" in contact:
            d["location"] = contact["location"]'''

new_contact_end = '''        if "location" not in d and "location" in contact:
            d["location"] = contact["location"]
        # Extract github/linkedin from contact if not already found
        for key in ("github", "github_url", "githubUrl"):
            if key in contact and "github_url" not in d:
                url = contact[key]
                if url and not url.startswith("http"):
                    url = "https://" + url
                d["github_url"] = url
        for key in ("linkedin", "linkedin_url", "linkedinUrl"):
            if key in contact and "linkedin_url" not in d:
                url = contact[key]
                if url and not url.startswith("http"):
                    url = "https://" + url
                d["linkedin_url"] = url'''

if old_contact_end in content:
    content = content.replace(old_contact_end, new_contact_end)
    print("FIXED: extract github/linkedin from contact dict")
else:
    print("contact end block not found")

open(path, "w", encoding="utf-8").write(content)
