content = open("frontend/pages/1_My_Profile.py", encoding="utf-8").read()
content = content.replace(
    "            await session.execute(delete(Project).where(Project.profile_id == pid))\n                await session.execute(delete(UserProfile))",
    "                    await session.execute(delete(Project).where(Project.profile_id == pid))\n                await session.execute(delete(UserProfile))"
)
open("frontend/pages/1_My_Profile.py", "w", encoding="utf-8").write(content)
print("FIXED indentation")
