/**
 * Safely parse tags from API response.
 * asyncpg returns JSONB as string, so tags might be a string like '["tag1","tag2"]'
 * instead of an actual array.
 */
export function parseTags(tags: unknown): string[] {
  if (Array.isArray(tags)) return tags;
  if (typeof tags === 'string') {
    try {
      const parsed = JSON.parse(tags);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}
