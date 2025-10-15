import { uuid, integer, text, timestamp } from 'drizzle-orm/pg-core';
import { projects } from './projects';
import { devV2Schema } from './_schema';

export const forecastVersions = devV2Schema.table('forecast_versions', {
  id: uuid('id').primaryKey().defaultRandom(),
  projectId: uuid('project_id')
    .notNull()
    .references(() => projects.id),
  versionNumber: integer('version_number').notNull(),
  reasonForChange: text('reason_for_change').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  createdBy: text('created_by').default('system'),
});

export type ForecastVersion = typeof forecastVersions.$inferSelect;
export type NewForecastVersion = typeof forecastVersions.$inferInsert;
