# Skill: Deploy

Use this when preparing or shipping a build for production.

1. Confirm tests pass first (see the Test skill) — never package a build that hasn't
   been run.
2. Call `resolve_issue(...)` for deployment/config packaging before reading files.
   Inspect KG-ranked config/build files first, then use `glob_files` for Dockerfile/
   docker-compose.yml only if KG is empty or incomplete.
3. List every environment variable the app needs by resolving config/env usage first,
   then use scoped `search_code` for `os.environ`/`process.env` only as a fallback.
   Make sure each variable is documented — write or update a `.env.example` covering
   all of them, with no real secrets in it.
4. Add or confirm a health-check endpoint/command exists so a deploy can be verified
   automatically, not just "it started".
5. Write a short rollback note: what the previous known-good state was (a git ref via
   `git_status`/`git_diff`) and the exact command to revert to it.
6. Only run deploy commands (`docker build`, `docker push`, cloud CLI commands, etc.)
   via `run_shell` — these always require explicit user confirmation, which is
   intentional for anything touching a live environment.
