/** App-wide constants. */

export const APP_NAME = 'GATE IGNITE';

export const ROUTES = {
  home: '/',
  login: '/login',
  adminLogin: '/portal/admin/login',
  signIn: '/sign-in',
  signUp: '/sign-up',
  accessDenied: '/access-denied',
  admin: '/admin',
  student: '/student',
  exam: '/exam',
} as const;

/** Route prefixes a role may access. Keys are Clerk publicMetadata roles. */
export const ROLE_ROUTES: Record<string, string[]> = {
  super_admin: ['/admin'],
  admin: ['/admin'],
  student: ['/student', '/exam'],
} as const;

/** Redirect target after sign-in per role. */
export const ROLE_HOME: Record<string, string> = {
  super_admin: '/admin',
  admin: '/admin',
  student: '/student',
} as const;

export const DEFAULT_HOME = '/student';

/** Relative timestamp from the server used to offset client clocks (exam timer safety). */
export const VIOLATION_THRESHOLDS = {
  maxWarnings: 3,
} as const;
