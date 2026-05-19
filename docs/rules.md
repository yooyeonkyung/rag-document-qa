# 🤝 Collaboration & Git Rules

Please strictly follow these rules to maintain a clean and professional repository history.

---

## 🎫 1. Issue Title Convention
Before starting any task, create a GitHub Issue with the following title format:
- **Format**: `[TAG] Task summary in English`
- **Examples**:
    - `[FE] Implement login page UI and Kakao button`
    - `[BE] Implement JWT generation and Security Filter`
    - `[AI] Implement PDF text extraction and chunking logic`

---

## 🎨 2. GitHub Issue Labels
Use the following 5 standard labels to categorize your tasks:
- `feat` : New feature implementation (API, UI, Logic)
- `fix` : Bug fixes
- `chore` : Library installation, config changes, build fixes
- `docs` : Documentation updates (README, API Spec)
- `refactor` : Code cleanup without changing behavior

---

## ✍️ 3. Commit Message Convention
Commit messages must follow the standard structure below. Always include the related issue number at the end.
- **Format**: `tag: lower-case verb-root content (#IssueNumber)`
- **Examples**:
    - `feat: add user entity and database mapping (#1)`
    - `fix: resolve jwt expiration time error (#3)`
    - `chore: install spring security dependencies (#4)`
    - `docs: update api specification v1.0 (#5)`

---

## 🤝 4. Pull Request (PR) & Code Review
1. All development must be done in a `feature/` branch branching off from `dev`.
2. Target branch for your PR must be **`dev`**, NOT `main`.
3. At least **1 Approval** from your teammate is required to merge the PR.
4. Include `Closes #IssueNumber` in the PR description to automatically close the resolved issue.