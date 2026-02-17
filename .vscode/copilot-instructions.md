# Log Doctor Backend AI Rules

## Architecture & Detailed Rules

This project uses a layered architecture. Refer to the specific instruction files in each directory for detailed rules:

- **Core (`app/core`)**: [See Core Rules](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/core/.ai-instructions.md)
- **API (`app/api`)**: [See API Rules](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/api/.ai-instructions.md)
- **Infra (`app/infra`)**: [See Infra Rules](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/infra/.ai-instructions.md)
- **Domain (`app/domains`)**: [See Domain Rules](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/.ai-instructions.md)
  - [Tenant Role](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/tenant/README.md)
  - [Subscription Role](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/subscription/README.md)
  - [Agent Role](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/agent/README.md)
  - [Report Role](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/report/README.md)
  - [License Role](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/domains/license/README.md)
- **Common (`app/common`)**: [See Common Rules](file:///Users/shin-yoonsik/Desktop/log-doctor/log-doctor-provider-back/app/common/.ai-instructions.md)

## Global Coding Standards

- **Sync**: Keep this file and `.agent/rules/.ai-instructions.md` in sync.
- **Managed Identity**: No hardcoded keys.
- **Async**: Use async/await for all I/O.
- **Pkg**: Use `uv`.

## Workflow

- Check `README.md` and this file first.
- Reference `app/domains/tenant/repository.py` for patterns.
- **Record changes in `docs/CHANGELOG.md`**:
  - Record changes immediately after completing a task.
  - Tasks within the same date must be numbered sequentially.
  - Separate entries by git user account.
  - Identify current git user using `git config user.name` and `git config user.email`.
  - Format: `## YYYY-MM-DD` -> `### <git user.name>` -> Numbered list.
  - If multiple accounts are used on the same day, create separate sections for each.
  - If git user identification fails, request the account name from the user.
- Record changes in `walkthrough.md`.
