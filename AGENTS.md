# Repository instructions

## Testing and GitHub Actions

The owner explicitly requests local testing by default and no automatic GitHub-hosted tests.

- Run appropriate checks locally in the execution environment.
- Do not add GitHub Actions test steps or workflows, enable workflows, or dispatch hosted test runs unless the user explicitly requests GitHub-hosted testing.
- Keep workflows free of `push` and `pull_request` triggers. The existing test workflow is manual-only and disabled in repository settings.
- Creating or updating a PR does not authorize a GitHub Actions run.
- Preserve the local test suites and report local results in PR descriptions.
