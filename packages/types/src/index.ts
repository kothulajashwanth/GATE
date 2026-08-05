/** Shared domain types used across web and api. Keep dependency-free. */

export const ROLES = ['super_admin', 'admin', 'student', 'faculty'] as const;
export type Role = (typeof ROLES)[number];

export const QUESTION_TYPES = [
  'mcq',
  'true_false',
  'fill_blank',
  'paragraph',
  'coding',
  'image_based',
  'multi_select',
] as const;
export type QuestionType = (typeof QUESTION_TYPES)[number];

export const DIFFICULTY_LEVELS = ['easy', 'medium', 'hard'] as const;
export type DifficultyLevel = (typeof DIFFICULTY_LEVELS)[number];

export const BLOOM_LEVELS = [
  'remember',
  'understand',
  'apply',
  'analyze',
  'evaluate',
  'create',
] as const;
export type BloomLevel = (typeof BLOOM_LEVELS)[number];

export const EXAM_STATUSES = ['draft', 'published', 'in_progress', 'completed', 'cancelled'] as const;
export type ExamStatus = (typeof EXAM_STATUSES)[number];

export const EXAM_QUESTION_MODES = ['all_at_once', 'one_at_a_time'] as const;
export type ExamQuestionMode = (typeof EXAM_QUESTION_MODES)[number];

export const SESSION_STATUSES = ['active', 'submitted', 'terminated', 'expired'] as const;
export type SessionStatus = (typeof SESSION_STATUSES)[number];

export const VIOLATION_TYPES = [
  'fullscreen_exit',
  'tab_change',
  'visibility_change',
  'window_blur',
  'window_minimize',
  'refresh',
  'back_navigation',
  'right_click',
  'copy',
  'paste',
  'text_selection',
  'devtools',
  'keyboard_shortcut',
  'mouse_leave',
  'network_disconnect',
  'resize',
] as const;
export type ViolationType = (typeof VIOLATION_TYPES)[number];

export const NOTIFICATION_TYPES = [
  'exam_scheduled',
  'exam_cancelled',
  'result_published',
  'password_reset',
  'announcement',
] as const;
export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export interface User {
  id: string;
  clerkId: string | null;
  email: string;
  firstName: string | null;
  lastName: string | null;
  role: Role;
  avatarUrl: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
