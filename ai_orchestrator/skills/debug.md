# Skill: Debug

Use this when something is broken and the cause isn't already obvious.

1. Reproduce first: run the failing command/test with `run_shell`/`run_tests` and
   read the actual error/traceback rather than guessing from the symptom description.
2. Call `resolve_issue(description)` with the bug report or error text before
   manually exploring — it checks the project's knowledge graph (functions,
   classes, import relationships) and points at the files most likely involved.
   If it's your first time in this project, call `build_knowledge_graph()` once first.
   Then use `search_code`/`glob_files`/`read_file` on the files it points at to
   confirm — the resolver narrows candidates, it doesn't replace reading the code.
3. If resolve_issue comes back empty or unconvincing, fall back to `search_code`/
   `glob_files` across the whole project — find every place the failing behavior
   could originate from, don't patch the first line you see.
4. If the error involves a library or API you're not fully certain about (version
   drift, unfamiliar error message, recent framework change), use `web_search` and
   `fetch_url` to check current documentation before guessing — your training data
   may be stale for fast-moving libraries.
5. Form a hypothesis, make the smallest change that tests it, and re-run the
   failing case immediately — don't stack multiple speculative fixes at once.
6. Once fixed, run the full test suite (`run_tests`), not just the one failing case,
   to catch regressions the fix might have introduced.
