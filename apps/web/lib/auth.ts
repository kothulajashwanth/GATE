function normalizeRole(role?: unknown): string {
  return typeof role === 'string' ? role.trim().toLowerCase() : '';
}

function getEmail(subject?: any): string {
  const email =
    (typeof subject?.email === 'string' && subject.email) ||
    (typeof subject?.email_address === 'string' && subject.email_address) ||
    (typeof subject?.primaryEmailAddress?.emailAddress === 'string' && subject.primaryEmailAddress.emailAddress) ||
    '';
  return email.toLowerCase();
}

function getUsername(subject?: any): string {
  return typeof subject?.username === 'string' ? subject.username.toLowerCase() : '';
}

export function getRoleFromUserOrClaims(subject?: any): string {
  const role =
    normalizeRole(subject?.publicMetadata?.role) ||
    normalizeRole(subject?.unsafeMetadata?.role) ||
    normalizeRole(subject?.metadata?.role) ||
    normalizeRole(subject?.public_metadata?.role) ||
    normalizeRole(subject?.role);

  if (role) {
    return role;
  }

  const email = getEmail(subject);
  const username = getUsername(subject);

  if (
    email === 'kothulajashwanth@gmail.com' ||
    email.startsWith('admin@') ||
    username === 'admin'
  ) {
    return 'admin';
  }

  return 'student';
}

export function isAdminRole(role: string): boolean {
  const normalized = normalizeRole(role);
  return normalized === 'admin' || normalized === 'super_admin';
}
