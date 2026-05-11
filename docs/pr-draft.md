# PR Title
Add agent repository review workflow and expand agent control center

## Summary
- add a backend repository review endpoint under `/agents/repository/review`
- introduce rule-based repository analysis for GitHub repos, including language-aware scoring, security checks, semantic findings, and AI-assisted summaries
- extend the frontend agent page with a repository review form and result rendering
- expose the new repository review API through the shared frontend API client

## What Changed
- added `RepositoryReviewRequest` and a new `/agents/repository/review` route in the backend
- expanded `code_analyzer.py` to fetch repository contents from GitHub, analyze text files across multiple languages, score syntax/implementation/security quality, and summarize findings
- added `code_review_rules.py` to centralize file-extension, generated-file, ignore-path, score-policy, and `.gitignore` suggestion rules
- updated the agents UI so users can submit a repository URL, optional branch, optional token, and max file count for analysis
- updated the frontend API layer with `agentAPI.reviewRepository(...)`

## Why
This change turns the agent area into a broader operational tool. In addition to automation and prompt execution, users can now run repository-level reviews against GitHub projects and get structured findings, scores, and next-step guidance from the same interface.

## Testing
- not verified in this workspace because the repository git metadata is unavailable here
- recommended manual checks:
  - call `POST /api/v1/agents/repository/review` with a public GitHub repository URL
  - verify the agent page submits repository review requests and renders the JSON response
  - confirm private repository access works when a valid GitHub token is provided

## Notes
- the backend review flow depends on outbound GitHub access and `httpx` availability
- AI summaries fall back to plain-text output if the model response is not valid JSON
