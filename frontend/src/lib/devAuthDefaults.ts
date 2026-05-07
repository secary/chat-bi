import type { AppUser } from '../types/auth';

/** 免登录开发模式下 `/auth/me` 失败时的占位用户（与 database/init.sql 种子 admin id 一致） */
export const devAuthFallbackAdmin: AppUser = {
  id: 1,
  username: 'admin',
  role: 'admin',
};
