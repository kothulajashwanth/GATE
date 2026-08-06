import { describe, it, expect } from 'vitest';
import { ApiError } from './client';

describe('ApiError', () => {
  it('should instantiate correctly with status, code, and message', () => {
    const error = new ApiError(404, 'not_found', 'Resource not found');
    assertErrorProperties(error);
  });
});

function assertErrorProperties(error: ApiError) {
  expect(error.status).toBe(404);
  expect(error.code).toBe('not_found');
  expect(error.message).toBe('Resource not found');
}
