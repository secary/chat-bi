import { describe, expect, it } from 'vitest';
import { resolveDataSourceSwitch } from './dataSourceSwitch';
import type { DbConnectionRow } from '../types/admin';

const rows: DbConnectionRow[] = [
  {
    id: 1,
    name: 'data-governance',
    host: '10.2.10.80',
    port: 33062,
    username: 'snapshot',
    database_name: 'data_governance_test',
    is_default: false,
  },
  {
    id: 2,
    name: 'janus',
    host: 'host.docker.internal',
    port: 3306,
    username: 'janus',
    database_name: 'exchange',
    is_default: false,
  },
];

describe('resolveDataSourceSwitch', () => {
  it('matches data source name', () => {
    const out = resolveDataSourceSwitch('用 janus 看一下当前数据库有哪些表', rows);
    expect(out.status).toBe('unique');
    if (out.status === 'unique') expect(out.row.id).toBe(2);
  });

  it('matches database name', () => {
    const out = resolveDataSourceSwitch('查一下 data_governance_test 的表结构', rows);
    expect(out.status).toBe('unique');
    if (out.status === 'unique') expect(out.row.id).toBe(1);
  });

  it('matches connection string', () => {
    const out = resolveDataSourceSwitch('host.docker.internal:3306/exchange 里有什么', rows);
    expect(out.status).toBe('unique');
    if (out.status === 'unique') expect(out.row.id).toBe(2);
  });

  it('returns none when no source is mentioned', () => {
    expect(resolveDataSourceSwitch('当前数据库有哪些表', rows).status).toBe('none');
  });

  it('returns ambiguous when multiple sources are mentioned', () => {
    const out = resolveDataSourceSwitch('对比 janus 和 data-governance 的表', rows);
    expect(out.status).toBe('ambiguous');
    if (out.status === 'ambiguous') expect(out.rows).toHaveLength(2);
  });
});
