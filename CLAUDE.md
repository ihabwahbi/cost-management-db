# Cost Management Database - Claude Code Guide

Data pipeline and schema definitions for the `dev_v3` PostgreSQL schema.

**For complete documentation, see `AGENTS.md`** - this file is a quick reference only.

## Quick Reference

```bash
npm run db:push       # Push schema changes to database
npm run db:generate   # Generate migration files
npm run db:studio     # Open Drizzle Studio GUI
npm run type-check    # TypeScript validation
npm test             # Run tests

# Data Pipeline
python3 scripts/pipeline.py           # Run full pipeline
python3 scripts/pipeline.py --stage1  # Run only stage 1

# Cross-Project Schema Sync (this project owns data schemas)
python3 scripts/validators/cross_project_schema.py --check  # Verify sync
python3 scripts/validators/cross_project_schema.py --sync   # Sync to webapp
```

## Key Points

- **Our Schema**: `dev_v3` (isolated, safe to modify)
- **Production Schema**: `public` (NEVER TOUCH)
- **This project owns data schemas** - syncs to webapp via pre-commit hook

## Schema Changes Workflow

1. Edit `src/schema/*.ts`
2. Run `python3 scripts/validators/cross_project_schema.py --sync`
3. Run `cd ../cost-management && npm run db:push`

## Resources

- **Full documentation**: See `AGENTS.md`
- Drizzle Docs: https://orm.drizzle.team/
