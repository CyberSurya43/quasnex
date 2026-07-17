# Skill: Plan

Use this before writing any code for a new feature or app.

1. Restate the goal in your own words in 1-3 sentences. If requirements are ambiguous,
   pick the most reasonable default and state the assumption explicitly instead of stalling.
2. Use `project_tree` and `read_file` to understand what already exists before proposing
   anything new. Never assume an empty project — check first. For an existing/unfamiliar
   codebase, call `build_knowledge_graph()` once, then `resolve_issue(...)` with the feature
   description to find the modules it will touch before you start reading files one by one.
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
