---
name: browser-automation-hitl
description: Safety contract and patterns for Playwright / browser-use application automation. Consult whenever writing any browser-automation code that navigates job portals or fills application forms.
---

# Browser Automation — Human-in-the-Loop Contract

HARD RULE: NEVER click the final Submit / Apply / Send control. Automation prepares the application and STOPS. A human approves in the review UI; only then does code perform the final submit as an explicit, separate, logged action.

Also never: solve CAPTCHAs automatically, bypass bot detection, or create accounts. Surface these to the human.

Preferences:
- Prefer official APIs / ATS feeds (Greenhouse, Lever, Ashby, Workday) over scraping gated sites.
- Respect robots.txt and platform ToS. Throttle politely; randomize human-like delays.
- Persist sessions; never log or store credentials in plaintext (env / secrets only).

Filling flow (per application):
- Navigate, detect form fields (text, dropdown, checkbox, radio, date, file upload).
- Upload tailored resume, cover letter, portfolio/GitHub/LinkedIn links.
- Handle multi-page forms and client-side validation; retry transient failures with tenacity.
- Capture a screenshot at each step and a final full-page screenshot.
- Save a structured record: every field, the value filled, and the source, for human review.
- Return a ReviewPacket (job, company, filled answers, file refs, screenshots) — then STOP.
