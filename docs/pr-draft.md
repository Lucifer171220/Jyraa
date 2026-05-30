# PR Title
Replace Ollama with NVIDIA NIM and improve repository security reports

## Summary
- replace the Ollama integration with LangChain + NVIDIA NIM model support
- move runtime configuration to `.env` and keep committed examples safe
- make GitHub repository evaluation stricter with SAST-style findings, risk-weighted scoring, project-structure analysis, and dependency vulnerability checks
- improve the frontend agents page so repository reviews and agent responses render as readable reports instead of plain JSON

## What Changed
- Added a NIM service backed by `langchain_nvidia_ai_endpoints.ChatNVIDIA`.
- Updated agent status and automation flows to report NIM availability, selected model, LangChain availability, and LangGraph availability.
- Removed the old Ollama service and dependency.
- Updated backend settings to load required values from `backend/.env`.
- Sanitized `.env.example` so secrets are not committed.
- Expanded repository analysis with stricter vulnerability rules, .NET-aware checks, project-structure warnings, NuGet dependency parsing, OSV lookups, and weighted scoring that penalizes high-risk findings more heavily.
- Added repository-level `risk_summary` and `score_explanation` fields to make scan results easier to interpret.
- Updated the frontend agents UI with structured renderers for repository reviews, workflow responses, prompt automation output, metrics, findings tables, and collapsible raw JSON.
- Updated README/setup docs with the NIM configuration flow.

## Security Notes
- `backend/.env` should remain local and must not be committed.
- The committed env example now uses placeholders only.
- If any real NVIDIA/NIM API key was previously committed or shared, rotate it before merging.
- The repository evaluator is now intentionally stricter: scores are heuristic SAST-style risk indicators, not a compiler-grade proof of correctness.

## Verification
- `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` passed.
- `.\.venv\Scripts\python.exe -m compileall app` passed.
- `npm run type-check` passed.
- Live repository review against `https://github.com/Lucifer171220/LoginRegister` completed and now produces strict low scores with high/medium findings instead of inflated scores.

## Known Local Check Blockers
- `npm run build` could not complete locally because an existing Node process was locking `frontend\.next\trace`.
- Browser verification could not be completed because the in-app browser tool was unavailable in this session.

## Reviewer Notes
- Required backend env values:
  - `DATABASE_SERVER`
  - `SECRET_KEY`
  - `ALGORITHM`
  - `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `FRONTEND_URL`
  - `NVIDIA_API_KEY` or `NIM_API_KEY`
  - `NIM_MODEL`
- Optional backend env values:
  - `NIM_BASE_URL`
  - `NIM_EMBEDDING_MODEL`
  - SMTP settings for email features
