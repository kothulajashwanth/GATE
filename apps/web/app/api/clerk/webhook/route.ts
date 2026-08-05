import { Webhook } from 'svix';
import { headers } from 'next/headers';
import { NextResponse, type NextRequest } from 'next/server';
import type { WebhookEvent } from '@clerk/nextjs/server';

/**
 * Clerk webhook receiver. Verifies the Svix signature, then forwards the
 * event to the API so the identity provider (Clerk) stays the source of
 * truth while the API mirrors users into Postgres.
 */
export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const WEBHOOK_SECRET = process.env.CLERK_WEBHOOK_SECRET;
  if (!WEBHOOK_SECRET) {
    return NextResponse.json({ error: 'Webhook secret not configured' }, { status: 500 });
  }

  const headerPayload = await headers();
  const svixId = headerPayload.get('svix-id');
  const svixTimestamp = headerPayload.get('svix-timestamp');
  const svixSignature = headerPayload.get('svix-signature');
  if (!svixId || !svixTimestamp || !svixSignature) {
    return NextResponse.json({ error: 'Missing svix headers' }, { status: 400 });
  }

  const payload = await req.text();
  const wh = new Webhook(WEBHOOK_SECRET);
  let evt: WebhookEvent;
  try {
    evt = wh.verify(payload, { 'svix-id': svixId, 'svix-timestamp': svixTimestamp, 'svix-signature': svixSignature }) as WebhookEvent;
  } catch {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const apiKey = process.env.API_INTERNAL_KEY;

  const forward = await fetch(`${apiUrl}/v1/webhooks/clerk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'X-Internal-Key': apiKey } : {}),
    },
    body: JSON.stringify({ event: evt.type, data: evt.data }),
  });

  if (!forward.ok) {
    return NextResponse.json({ error: 'Failed to sync user' }, { status: 502 });
  }

  return NextResponse.json({ received: true });
}
