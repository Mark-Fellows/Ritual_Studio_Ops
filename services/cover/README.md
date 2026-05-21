# services/cover

This directory will contain the Cover Management Python pipeline (stages 1–7), relocated here as part of Phase 3 of the merger plan.

## STATUS: PENDING (Phase 3)

Source location: `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\`

Phase 3 tasks:
- Move stages 1–7 Python scripts here
- Update to read from merged `.env`
- Replace `sys.path.insert` hack in stage 1 with `from services.momence.momence_api_client import MomenceAPIClient`
- Refactor stage 1 to use `disciplines` and `studios` reference tables (Phase 1 schema)
- Add `--insert-new` option to `momence_teacher_sync.py`
