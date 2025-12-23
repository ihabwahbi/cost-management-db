# Cost Management Database - Claude Code Guide

Data pipeline and schema definitions for the `dev_v3` PostgreSQL schema.

**For complete documentation, see `AGENTS.md`** - this file is a quick reference only.

## Quick Reference

```bash
npm run db:drift      # Detect schema drift (shows SQL, never applies)
npm run db:drift:sql  # Output raw SQL only (for review/piping)
npm run db:drift:json # Output JSON (for CI)
npm run db:generate   # Generate migration files
npm run db:studio     # Open Drizzle Studio GUI
npm run type-check    # TypeScript validation
npm test             # Run tests

# Data Pipeline
python3 scripts/pipeline.py           # Run full pipeline
python3 scripts/pipeline.py --stage1  # Run only stage 1

# Schema validation
bash ../cost-management/scripts/check-schema-symlinks.sh  # Verify all symlinks
```

## Key Points

- **Our Schema**: `dev_v3` (isolated, safe to modify)
- **Production Schema**: `public` (NEVER TOUCH)
- **No db:push** — schema changes are applied manually via SQL after reviewing drift
- **Bidirectional symlinks** — data schemas owned here, webapp schemas symlinked in

## Schema Changes Workflow

1. Edit `src/schema/*.ts`
2. Run `npm run db:drift` to see required SQL
3. Apply the SQL manually via psql or database MCP tool
4. Run `npm run type-check`

## Resources

- **Full documentation**: See `AGENTS.md`
- Drizzle Docs: https://orm.drizzle.team/
