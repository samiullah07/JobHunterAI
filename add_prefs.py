path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

# Find the end of the manual form, add a preferences-only updater
prefs_section = '''
# --- Quick Preferences Update (doesn't wipe CV data) ---
st.divider()
st.subheader("Update Job Preferences Only")
st.markdown("Update salary, remote, and visa without re-uploading your CV.")
col_p1, col_p2 = st.columns(2)
pref_salary_min = col_p1.number_input("Minimum Salary (annual)", min_value=0, max_value=500000, value=0, step=5000, key="pref_sal_min")
pref_salary_max = col_p2.number_input("Maximum Salary (annual)", min_value=0, max_value=500000, value=0, step=5000, key="pref_sal_max")
pref_remote = st.selectbox("Remote Preference", ["No preference", "Remote", "Hybrid", "Onsite"], key="pref_remote")
pref_visa = st.text_input("Visa Status (e.g. UK citizen, need sponsorship)", key="pref_visa")

if st.button("Save Preferences", key="save_prefs"):
    async def update_prefs():
        from jobhunter.infrastructure.db.unit_of_work import unit_of_work
        from jobhunter.infrastructure.db.models import UserProfile
        from sqlalchemy import select, update
        remote_map = {"No preference": None, "Remote": "REMOTE", "Hybrid": "HYBRID", "Onsite": "ONSITE"}
        async with unit_of_work() as session:
            stmt = update(UserProfile).values(
                salary_min=pref_salary_min if pref_salary_min > 0 else None,
                salary_max=pref_salary_max if pref_salary_max > 0 else None,
                remote_preference=remote_map.get(pref_remote),
                visa_status=pref_visa.strip() or None,
            )
            await session.execute(stmt)
            await session.flush()
            return True
    try:
        _run_async(update_prefs())
        st.success("Preferences saved! Your existing skills and projects are unchanged.")
    except Exception as exc:
        st.error(f"Save failed: {type(exc).__name__}")
'''

# Add at the very end of the file
content = content.rstrip() + "\n" + prefs_section + "\n"
open(path, "w", encoding="utf-8").write(content)
print("ADDED: preferences-only update section")
