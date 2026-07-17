# Skill: Deploy

Use this when preparing or shipping a build for production.

1. Confirm tests pass first (see the Test skill) — never package a build that hasn't
   been run.
2. Check for a Dockerfile/docker-compose.yml with `glob_files`; if missing and the
   project needs one, write one: multi-stage build, non-root user, pinned base image
   version (never `:latest`), and a health-check.
3. List every environment variable the app needs (grep for `os.environ`/`process.env`/
   config reads with `search_code`) and make sure each one is documented — write or
   update a `.env.example` covering all of them, with no real secrets in it.
4. Add or confirm a health-check endpoint/command exists so a deploy can be verified
   automatically, not just "it started".
5. Write a short rollback note: what the previous known-good state was (a git ref via
   `git_status`/`git_diff`) and the exact command to revert to it.
6. Only run deploy commands (`docker build`, `docker push`, cloud CLI commands, etc.)
   via `run_shell` — these always require explicit user confirmation, which is
   intentional for anything touching a live environment.
