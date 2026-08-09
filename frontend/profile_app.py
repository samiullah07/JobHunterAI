"""Streamlit profile entry form — single active profile, swappable."""
import streamlit as st
import asyncio
from datetime import date

st.set_page_config(page_title="Create Your Profile", page_icon="👤", layout="wide")

# Session state for repeatable lists
st.session_state.setdefault("skills", [])
st.session_state.setdefault("experiences", [])
st.session_state.setdefault("educations", [])

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

st.title("Create Your Profile")

# --- Basic Info ---
col1, col2 = st.columns(2)
first_name = col1.text_input("First Name *")
last_name = col2.text_input("Last Name *")
email = st.text_input("Email *")
phone = st.text_input("Phone")
user_location = st.text_input("Location (e.g. San Francisco, CA)")
linkedin_url = st.text_input("LinkedIn URL")
github_url = st.text_input("GitHub URL")
summary = st.text_area("Professional Summary")

# --- Skills ---
st.subheader("Skills")
new_skill = st.text_input("Type a skill and press Add", key="new_skill_input")
if st.button("Add Skill") and new_skill.strip():
    st.session_state.skills.append(new_skill.strip())
    st.rerun()
for i, skill in enumerate(st.session_state.skills):
    c1, c2 = st.columns([9, 1])
    c1.write(f"**{skill}**")
    if c2.button("X", key=f"rm_skill_{i}"):
        st.session_state.skills.pop(i)
        st.rerun()

# --- Work Experience ---
st.subheader("Work Experience")
with st.expander("Add a new experience"):
    exp_company = st.text_input("Company *", key="exp_company")
    exp_title = st.text_input("Job Title *", key="exp_title")
    exp_location = st.text_input("Location", key="exp_location")
    exp_start = st.date_input("Start Date *", value=date(2020, 1, 1), key="exp_start")
    exp_current = st.checkbox("I currently work here", key="exp_current")
    exp_end = None if exp_current else st.date_input("End Date", value=date.today(), key="exp_end")
    exp_desc = st.text_area("Description", key="exp_desc")
    if st.button("Add Experience") and exp_company.strip() and exp_title.strip():
        st.session_state.experiences.append({
            "company_name": exp_company.strip(),
            "title": exp_title.strip(),
            "location": exp_location.strip() or None,
            "start_date": exp_start,
            "end_date": exp_end,
            "is_current": exp_current,
            "description": exp_desc.strip() or None,
        })
        st.rerun()
for i, exp in enumerate(st.session_state.experiences):
    c1, c2 = st.columns([9, 1])
    current_tag = " (current)" if exp["is_current"] else ""
    c1.write(f"**{exp['title']}** at {exp['company_name']}{current_tag} — {exp['start_date']}")
    if c2.button("X", key=f"rm_exp_{i}"):
        st.session_state.experiences.pop(i)
        st.rerun()

# --- Education ---
st.subheader("Education")
with st.expander("Add education"):
    edu_inst = st.text_input("Institution *", key="edu_inst")
    edu_degree = st.text_input("Degree *", key="edu_degree")
    edu_field = st.text_input("Field of Study", key="edu_field")
    edu_start = st.date_input("Start Date *", value=date(2016, 9, 1), key="edu_start")
    edu_end = st.date_input("End Date", value=date(2020, 6, 1), key="edu_end")
    edu_gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, value=0.0, step=0.1, key="edu_gpa")
    if st.button("Add Education") and edu_inst.strip() and edu_degree.strip():
        st.session_state.educations.append({
            "institution": edu_inst.strip(),
            "degree": edu_degree.strip(),
            "field_of_study": edu_field.strip() or None,
            "start_date": edu_start,
            "end_date": edu_end,
            "gpa": edu_gpa if edu_gpa > 0 else None,
        })
        st.rerun()
for i, edu in enumerate(st.session_state.educations):
    c1, c2 = st.columns([9, 1])
    c1.write(f"**{edu['degree']}** — {edu['institution']}")
    if c2.button("X", key=f"rm_edu_{i}"):
        st.session_state.educations.pop(i)
        st.rerun()

# --- Save ---
st.divider()
if st.button("Save Profile", type="primary"):
    full_name = f"{first_name.strip()} {last_name.strip()}".strip()
    if not full_name or not email.strip():
        st.error("First Name, Last Name, and Email are required.")
    else:
        async def save_profile():
            from jobhunter.infrastructure.db.unit_of_work import unit_of_work
            from jobhunter.infrastructure.db.models import (
                UserProfile, Skill, WorkExperience, Education,
                Application, MatchScore, ResumeVersion, CoverLetterVersion,
            )
            from sqlalchemy import delete, select

            async with unit_of_work() as session:
                # Wipe existing profile + dependents
                pids = (await session.execute(select(UserProfile.id))).scalars().all()
                for pid in pids:
                    await session.execute(delete(Application).where(Application.profile_id == pid))
                    await session.execute(delete(MatchScore).where(MatchScore.profile_id == pid))
                    await session.execute(delete(ResumeVersion).where(ResumeVersion.profile_id == pid))
                    await session.execute(delete(CoverLetterVersion).where(CoverLetterVersion.profile_id == pid))
                    await session.execute(delete(Skill).where(Skill.profile_id == pid))
                    await session.execute(delete(WorkExperience).where(WorkExperience.profile_id == pid))
                    await session.execute(delete(Education).where(Education.profile_id == pid))
                await session.execute(delete(UserProfile))
                await session.flush()

                # Insert new profile
                profile = UserProfile(
                    full_name=full_name,
                    email=email.strip(),
                    phone=phone.strip() or None,
                    location=user_location.strip() or None,
                    summary=summary.strip() or None,
                    linkedin_url=linkedin_url.strip() or None,
                    github_url=github_url.strip() or None,
                )
                session.add(profile)
                await session.flush()

                for skill_name in st.session_state.skills:
                    session.add(Skill(profile_id=profile.id, name=skill_name))
                for exp in st.session_state.experiences:
                    session.add(WorkExperience(
                        profile_id=profile.id,
                        company_name=exp["company_name"],
                        title=exp["title"],
                        location=exp.get("location"),
                        start_date=exp["start_date"],
                        end_date=exp.get("end_date"),
                        is_current=exp["is_current"],
                        description=exp.get("description"),
                    ))
                for edu in st.session_state.educations:
                    session.add(Education(
                        profile_id=profile.id,
                        institution=edu["institution"],
                        degree=edu["degree"],
                        field_of_study=edu.get("field_of_study"),
                        start_date=edu["start_date"],
                        end_date=edu.get("end_date"),
                        gpa=edu.get("gpa"),
                    ))
                await session.flush()
                return str(profile.id)

        try:
            pid = _run_async(save_profile())
            st.success(f"Profile saved! ID: {pid}")
            st.balloons()
        except Exception as e:
            st.error(f"Save failed: {e}")
