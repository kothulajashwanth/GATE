# Clerk JWT Template Setup

1. In Clerk Dashboard → JWT Templates → New Template
2. Name: `examshield`
3. Claims:
```json
{
  "sub": "{{user.id}}",
  "role": "{{user.public_metadata.role}}",
  "email": "{{user.primary_email_address.email_address}}",
  "name": "{{user.full_name}}",
  "iat": {{now}},
  "exp": {{now_plus_1h}}
}
```
4. Signing algorithm: RS256
5. Save and copy the Signing Key (JWKS URL auto: `https://<your-clerk-domain>/.well-known/jwks.json`)

6. Add to `.env`:
```bash
CLERK_ISSUER=https://<your-clerk-domain>
CLERK_JWKS_URL=https://<your-clerk-domain>/.well-known/jwks.json
```

7. In Clerk → User & Authentication → Sessions → set "Single session per user" ON (prevents concurrent logins)