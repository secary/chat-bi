import type { AppUserRow } from '../types/auth';

export type UserAdminPermissions = {
  canManageRole: boolean;
  canResetPassword: boolean;
  canToggleActive: boolean;
  targetIsRoot: boolean;
};

type PermissionInput = {
  row: AppUserRow;
  active: boolean;
  busy: boolean;
  currentUserId: number;
  currentUserIsRoot: boolean;
};

export function userAdminPermissions({
  row,
  active,
  busy,
  currentUserId,
  currentUserIsRoot,
}: PermissionInput): UserAdminPermissions {
  const self = row.id === currentUserId;
  const targetIsRoot = row.username === 'root' || row.role === 'root';
  const adminRow = row.role === 'admin';

  return {
    canManageRole: currentUserIsRoot && !targetIsRoot,
    canResetPassword: !busy && (!adminRow || currentUserIsRoot || self) && (!targetIsRoot || self),
    canToggleActive:
      !busy && !targetIsRoot && !(self && active) && (!adminRow || currentUserIsRoot),
    targetIsRoot,
  };
}
