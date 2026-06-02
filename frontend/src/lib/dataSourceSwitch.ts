import type { DbConnectionRow } from '../types/admin';

export type DataSourceSwitchMatch =
  | { status: 'none' }
  | { status: 'unique'; row: DbConnectionRow; matched: string }
  | { status: 'ambiguous'; rows: DbConnectionRow[] };

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function tokenCandidates(row: DbConnectionRow): string[] {
  return [
    row.name,
    row.database_name,
    `${row.host}:${row.port}/${row.database_name}`,
    `${row.host}:${row.port}`,
  ]
    .map(normalize)
    .filter((item) => item.length >= 2);
}

function containsToken(text: string, token: string): boolean {
  if (!token) return false;
  return text.includes(token);
}

export function resolveDataSourceSwitch(
  message: string,
  rows: DbConnectionRow[],
): DataSourceSwitchMatch {
  const text = normalize(message);
  if (!text || rows.length === 0) return { status: 'none' };

  const hits = rows
    .map((row) => {
      const matched = tokenCandidates(row).find((token) => containsToken(text, token));
      return matched ? { row, matched } : null;
    })
    .filter((item): item is { row: DbConnectionRow; matched: string } => Boolean(item));

  if (hits.length === 0) return { status: 'none' };
  if (hits.length === 1) {
    return { status: 'unique', row: hits[0].row, matched: hits[0].matched };
  }

  const uniqueRows = Array.from(new Map(hits.map((hit) => [hit.row.id, hit.row])).values());
  if (uniqueRows.length === 1) {
    return { status: 'unique', row: uniqueRows[0], matched: hits[0].matched };
  }
  return { status: 'ambiguous', rows: uniqueRows };
}
