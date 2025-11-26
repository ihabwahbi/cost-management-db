import { varchar, text } from 'drizzle-orm/pg-core';
import { devV3Schema } from './_schema';

export const wbsDetails = devV3Schema.table('wbs_details', {
  wbsNumber: varchar('wbs_number').primaryKey(),
  clientName: text('client_name'),
  subBusinessLine: text('sub_business_line'),
});

export type WbsDetail = typeof wbsDetails.$inferSelect;
export type NewWbsDetail = typeof wbsDetails.$inferInsert;
