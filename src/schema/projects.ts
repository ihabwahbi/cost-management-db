import { uuid, text, timestamp, numeric } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

export const projects = devV3Schema.table('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: text('name').notNull(),
  subBusinessLine: text('sub_business_line').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
  
  // Auto-amortisation threshold (USD). When set, POs mapped to this project
  // with total value exceeding this amount are automatically flagged as amortised.
  // NULL = no auto-amortisation for this project.
  autoAmortiseThreshold: numeric('auto_amortise_threshold'),
});

export type Project = typeof projects.$inferSelect;
export type NewProject = typeof projects.$inferInsert;
