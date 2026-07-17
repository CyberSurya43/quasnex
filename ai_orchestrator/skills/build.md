# Skill: Build

Use this to implement a planned change.

1. Work in the smallest coherent increment that leaves the project in a working state —
   don't try to write an entire app in one shot.
2. Before creating a file, use `glob_files`/`project_tree` to check whether something
   equivalent already exists. Prefer editing over duplicating.
3. Use `read_file` on any file before `edit_file`-ing it, so `old_text` matches exactly.
4. Use `write_file` for new files, `edit_file` for surgical changes to existing ones.
   Never paste an entire large file back through `edit_file` when a targeted change
   would do — it wastes context and increases the chance of an unwanted diff.
5. Follow the existing code style, naming, and file layout you observe in the project —
   do not introduce a new pattern for something already established.
6. No secrets, API keys, or credentials in source files — use environment variables
   and note them in the completion summary.
7. After making changes, briefly re-read the changed files with `read_file` to sanity
   check them, then move to the Test skill before declaring the work done.
