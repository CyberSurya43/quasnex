# Skill: Plan

Use this before writing any code for a new feature or app.

1. Restate the goal in your own words in 1-3 sentences. If requirements are ambiguous,
   pick the most reasonable default and state the assumption explicitly instead of stalling.
2. Call `resolve_issue(...)` with the feature description before using `project_tree`,
   `list_dir`, `glob_files`, `search_code`, or `read_file`. Read the KG-ranked files first.
   If KG results are empty or clearly wrong, then fall back to tree/glob/search tools.
3. Produce a short written plan (use `write_file` to `docs/plan.md` if this is a
   multi-file feature, otherwise just state it in your reply) covering:
   - Files to create or change, one line each, with why.
   - Any new dependency and why it's needed.
   - Data model / API contract changes, if any.
   - Order of operations (what must happen before what).
4. Call out risk areas: anything that touches auth, payments, data migrations, or
   deletes data gets flagged explicitly, even if the user didn't ask about risk.
5. Stop and ask the user only when a decision would be expensive to reverse
   (e.g. choice of database, breaking API change). Otherwise, pick a sensible
   default, note it, and keep moving — don't block on every small decision.
6. Once the plan is stated, move directly into the Build skill for the first step.
