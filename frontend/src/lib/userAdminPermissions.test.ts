import { describe, expect, it } from 'vitest';
import { userAdminPermissions } from './userAdminPermissions';
import type { AppUserRow } from '../types/auth';

function row(overrides: Partial<AppUserRow>): AppUserRow {
  return {
    id: 2,
    username: 'secary',
    role: 'admin',
    is_active: true,
    created_at: '',
    ...overrides,
  };
}

describe('userAdminPermissions', () => {
  it('allows a role-root current user to manage administrator status', () => {
    const permissions = userAdminPermissions({
      row: row({ role: 'admin' }),
      active: true,
      busy: false,
      currentUserId: 4,
      currentUserIsRoot: true,
    });

    expect(permissions.canToggleActive).toBe(true);
    expect(permissions.canManageRole).toBe(true);
  });

  it('blocks non-root administrators from toggling administrator status', () => {
    const permissions = userAdminPermissions({
      row: row({ role: 'admin' }),
      active: true,
      busy: false,
      currentUserId: 4,
      currentUserIsRoot: false,
    });

    expect(permissions.canToggleActive).toBe(false);
    expect(permissions.canManageRole).toBe(false);
  });

  it('treats root role rows as immutable root accounts', () => {
    const permissions = userAdminPermissions({
      row: row({ username: 'root_user', role: 'root' }),
      active: true,
      busy: false,
      currentUserId: 4,
      currentUserIsRoot: true,
    });

    expect(permissions.targetIsRoot).toBe(true);
    expect(permissions.canToggleActive).toBe(false);
    expect(permissions.canManageRole).toBe(false);
  });
});
