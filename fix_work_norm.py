path = "src/jobhunter/adapters/parsing/llm_resume_parser.py"
content = open(path, encoding="utf-8").read()

old_work = """    if "work_experiences" in d and isinstance(d["work_experiences"], list):
        for exp in d["work_experiences"]:
            if isinstance(exp, dict):
                if "company" in exp and "company_name" not in exp:
                    exp["company_name"] = exp.pop("company")
                if "is_current" not in exp:
                    exp["is_current"] = False"""

new_work = """    # Wrap single work experience dict in a list
    if "work_experiences" in d and isinstance(d["work_experiences"], dict):
        d["work_experiences"] = [d["work_experiences"]]
    if "work_experiences" in d and isinstance(d["work_experiences"], list):
        for exp in d["work_experiences"]:
            if isinstance(exp, dict):
                # company variations -> company_name
                if "company_name" not in exp:
                    for k in ("company", "employer", "organization", "companyName"):
                        if k in exp:
                            exp["company_name"] = exp.pop(k)
                            break
                if "company_name" not in exp:
                    exp["company_name"] = "Unknown"
                # title variations -> title
                if "title" not in exp:
                    for k in ("jobTitle", "job_title", "role", "position", "designation"):
                        if k in exp:
                            exp["title"] = exp.pop(k)
                            break
                if "title" not in exp:
                    exp["title"] = "Unknown Role"
                # start_date: default if missing
                if "start_date" not in exp:
                    for k in ("startDate", "start", "from", "fromDate"):
                        if k in exp:
                            exp["start_date"] = exp.pop(k)
                            break
                if "start_date" not in exp:
                    exp["start_date"] = "2020-01-01"
                # end_date variations
                if "end_date" not in exp:
                    for k in ("endDate", "end", "to", "toDate"):
                        if k in exp:
                            exp["end_date"] = exp.pop(k)
                            break
                # is_current default
                if "is_current" not in exp:
                    exp["is_current"] = False"""

if old_work in content:
    content = content.replace(old_work, new_work)
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: comprehensive work experience sub-object normalization")
else:
    print("FAILED: work experience block not found")
