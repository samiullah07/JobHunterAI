"""Results page — shows approved applications with apply links, cover letters, and resumes."""
import streamlit as st
import asyncio
import json

from jobhunter.adapters.rendering.pdf_resume import generate_resume_pdf


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def load_approved():
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from sqlalchemy import text
    async with unit_of_work() as session:
        rows = (await session.execute(text("""
            SELECT a.id, j.title, j.company_name, j.url, j.location, a.status,
                   cv.body_markdown, r.canonical_json, j.description_raw
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            LEFT JOIN cover_letter_versions cv ON a.cover_letter_version_id = cv.id
            LEFT JOIN resume_versions r ON a.resume_version_id = r.id
            WHERE a.status = 'APPROVED'
            ORDER BY a.created_at DESC
        """))).fetchall()
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "company": r[2],
                "url": r[3],
                "location": r[4] or "Remote",
                "status": r[5],
                "cover_letter": r[6] or "",
                "resume_json": r[7] if isinstance(r[7], dict) else (json.loads(r[7]) if r[7] else {}),
                "description": (r[8] or "")[:500],
            }
            for r in rows
        ]

st.title("My Applications")
st.markdown("Your approved applications — ready to apply!")

try:
    apps = _run_async(load_approved())
except Exception as e:
    st.error(f"Failed to load applications: {e}")
    apps = []

if not apps:
    st.info("No approved applications yet. Go to the Review page and approve some jobs first.")
else:
    st.markdown(f"**{len(apps)} approved applications** ready for you to apply:")
    st.divider()

    for app in apps:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.subheader(f"{app['title']} — {app['company']}")
                st.caption(f"Location: {app['location']}")
            with col2:
                st.link_button("Apply Now", app["url"], type="primary")
            with col3:
                st.write(f"Status: {app['status']}")

            tab1, tab2, tab3 = st.tabs(["Cover Letter", "Resume", "Job Description"])

            with tab1:
                st.markdown(app["cover_letter"])
                st.download_button(
                    "Download Cover Letter",
                    app["cover_letter"],
                    file_name=f"cover_letter_{app['company'].replace(' ', '_')}.md",
                    mime="text/markdown",
                    key=f"dl_cover_{app['id']}",
                )

            with tab2:
                r = app["resume_json"]
                if r:
                    st.markdown(f"**{r.get('full_name', '')}** | {r.get('email', '')} | {r.get('phone', '')}")
                    st.markdown(f"*{r.get('summary', '')}*")
                    for exp in r.get("experiences", []):
                        st.markdown(f"**{exp.get('title', '')}** at {exp.get('company', '')}")
                        for bullet in exp.get("bullets", []):
                            st.markdown(f"- {bullet}")
                    if r.get("skills"):
                        for sg in r["skills"]:
                            if isinstance(sg, dict):
                                cat = sg.get("category") or "Skills"
                                items = sg.get("skills", [])
                                st.markdown(f"**{cat}:** {', '.join(str(s) for s in items)}")
                    st.download_button(
                        "Download Resume (JSON)",
                        json.dumps(r, indent=2),
                        file_name=f"resume_{app['company'].replace(' ', '_')}.json",
                        mime="application/json",
                        key=f"dl_resume_{app['id']}",
                    )

                    # Add PDF download button
                    pdf_bytes = generate_resume_pdf(r)
                    st.download_button(
                        "Download Resume (PDF)",
                        pdf_bytes,
                        file_name=f"resume_{app['company'].replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{app['id']}",
                    )
                else:
                    st.write("No resume data available.")

            with tab3:
                st.markdown(app["description"])
                if app["url"]:
                    st.markdown(f"[View full listing]({app['url']})")

            st.divider()
