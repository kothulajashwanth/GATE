/** App-wide constants. */

export const APP_NAME = 'ExamShield AI';

export const ROUTES = {
  home: '/',
  signIn: '/sign-in',
  signUp: '/sign-up',
  admin: '/admin',
  student: '/student',
  exam: '/exam',
} as const;

/** Route prefixes a role may access. Keys are Clerk publicMetadata roles. */
export const ROLE_ROUTES: Record<string, string[]> = {
  super_admin: ['/admin'],
  admin: ['/admin'],
  student: ['/student', '/exam'],
  faculty: ['/faculty'],
} as const;

/** Redirect target after sign-in per role. */
export const ROLE_HOME: Record<string, string> = {
  super_admin: '/admin',
  admin: '/admin',
  student: '/student',
  faculty: '/faculty',
} as const;

export const DEFAULT_HOME = '/student';

/** Relative timestamp from the server used to offset client clocks (exam timer safety). */
export const VIOLATION_THRESHOLDS = {
  maxWarnings: 3,
} as const;
