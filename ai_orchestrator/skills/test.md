# Skill: Test

Use this after implementing a change, before declaring it done.

1. Call `run_tests()` first with no arguments — it auto-detects the project's test
   command (pytest/Django/npm/go/cargo). Only pass an explicit command if detection
   fails or you need a narrower run (e.g. a single test file).
2. Read the output carefully. A non-zero exit code or any "FAILED"/"Error" line means
   the work is not done yet — go back to the Build skill and fix it, don't report success.
3. If no test suite exists for the code you touched, write a minimal one covering:
   - the happy path,
   - one realistic error/edge case.
   First call `resolve_issue(...)` for the touched behavior, then inspect KG-ranked
   files and nearby tests. Use `project_tree` only if KG does not reveal test locations;
   if there's no test directory yet, create one following the language's convention
   (`tests/` for Python, `__tests__/`/`*.test.ts` for JS, etc).
4. Use `git_diff` to review exactly what changed before considering the stage complete —
   catch accidental unrelated edits or leftover debug code.
5. Never claim tests pass without having actually run `run_tests` in this conversation.
