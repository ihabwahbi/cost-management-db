/**
 * PR Pre-Mapping Matching Logic
 *
 * This module is called after PO line item imports to automatically create
 * pending confirmation mappings when PRs match active pre-mappings.
 *
 * Flow:
 * 1. Find ACTIVE pre-mappings only (not closed, not expired)
 * 2. Find unmapped PO line items with matching PR
 * 3. Create po_mappings with requiresConfirmation = true
 * 4. Update pre-mapping counts
 * 5. Expire old pre-mappings
 */

import { db } from '../client';
import { prPreMappings, poLineItems, poMappings } from '../schema';
import { eq, and, isNull, lt, sql } from 'drizzle-orm';

export interface MatchResult {
  preMappingId: string;
  prNumber: string;
  matchedCount: number;
}

export interface MatchPRPreMappingsResult {
  matches: MatchResult[];
  totalMatched: number;
  expiredCount: number;
}

/**
 * Match active PR pre-mappings against PO line items and create pending confirmations.
 *
 * This function should be called after PO line item import completes.
 * It creates po_mappings with requiresConfirmation=true for user verification.
 *
 * Key behaviors:
 * - Only matches ACTIVE pre-mappings (ignores CLOSED, EXPIRED, CANCELLED)
 * - Creates mappings with requiresConfirmation = true (goes to inbox)
 * - Skips line items that already have any mapping
 * - Updates pending count on pre-mapping
 * - Expires pre-mappings past their expiry date
 */
export async function matchPRPreMappings(): Promise<MatchPRPreMappingsResult> {
  const matches: MatchResult[] = [];
  let totalMatched = 0;

  // Step 1: Find ACTIVE pre-mappings only (not closed, not expired)
  const activeMappings = await db
    .select()
    .from(prPreMappings)
    .where(eq(prPreMappings.status, 'active'));

  console.log(`  Found ${activeMappings.length} active pre-mappings`);

  // Step 2: For each pre-mapping, find and match unmapped PO line items
  for (const preMapping of activeMappings) {
    // Build where clause based on whether prLine is specified
    // If prLine is null, match ALL lines for that PR number
    // If prLine is specified, match only that specific line
    const lineCondition = preMapping.prLine !== null
      ? eq(poLineItems.prLine, preMapping.prLine)
      : sql`1=1`; // Match all lines when prLine is null

    // Find unmapped PO line items with matching PR
    // Use a subquery to check for existing mappings
    const unmappedLineItems = await db
      .select({
        id: poLineItems.id,
        poLineId: poLineItems.poLineId,
        poNumber: poLineItems.poNumber,
        prLine: poLineItems.prLine,
        poValueUsd: poLineItems.poValueUsd,
      })
      .from(poLineItems)
      .leftJoin(poMappings, eq(poMappings.poLineItemId, poLineItems.id))
      .where(
        and(
          eq(poLineItems.prNumber, preMapping.prNumber),
          lineCondition,
          eq(poLineItems.isActive, true),
          isNull(poMappings.id) // No existing mapping
        )
      );

    if (unmappedLineItems.length === 0) {
      continue;
    }

    console.log(`  PR ${preMapping.prNumber}: ${unmappedLineItems.length} unmapped line items`);

    // Step 3: Create pending-confirmation mappings
    const newMappings = unmappedLineItems.map((item) => ({
      poLineItemId: item.id,
      costBreakdownId: preMapping.costBreakdownId,
      mappedAmount: item.poValueUsd || '0',
      mappingNotes: `Auto-matched from PR ${preMapping.prNumber}`,
      mappedBy: 'system',
      mappingSource: 'pre-mapping' as const,
      sourcePrPreMappingId: preMapping.id,
      requiresConfirmation: true, // Goes to inbox
      mappedAt: new Date(),
    }));

    await db.insert(poMappings).values(newMappings);

    // Step 4: Update pre-mapping counts
    // Get current confirmed count (mappings from this pre-mapping with requiresConfirmation=false)
    const [confirmedResult] = await db
      .select({ count: sql<number>`count(*)::int` })
      .from(poMappings)
      .where(
        and(
          eq(poMappings.sourcePrPreMappingId, preMapping.id),
          eq(poMappings.requiresConfirmation, false)
        )
      );

    // Get current pending count (mappings from this pre-mapping with requiresConfirmation=true)
    const [pendingResult] = await db
      .select({ count: sql<number>`count(*)::int` })
      .from(poMappings)
      .where(
        and(
          eq(poMappings.sourcePrPreMappingId, preMapping.id),
          eq(poMappings.requiresConfirmation, true)
        )
      );

    await db
      .update(prPreMappings)
      .set({
        pendingConfirmationCount: pendingResult.count,
        confirmedCount: confirmedResult.count,
        updatedAt: new Date(),
      })
      .where(eq(prPreMappings.id, preMapping.id));

    matches.push({
      preMappingId: preMapping.id,
      prNumber: preMapping.prNumber,
      matchedCount: newMappings.length,
    });
    totalMatched += newMappings.length;
  }

  // Step 5: Expire old pre-mappings
  const expireResult = await db
    .update(prPreMappings)
    .set({
      status: 'expired',
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(prPreMappings.status, 'active'),
        lt(prPreMappings.expiresAt, new Date())
      )
    )
    .returning({ id: prPreMappings.id });

  const expiredCount = expireResult.length;
  if (expiredCount > 0) {
    console.log(`  Expired ${expiredCount} pre-mappings past their expiry date`);
  }

  return {
    matches,
    totalMatched,
    expiredCount,
  };
}
