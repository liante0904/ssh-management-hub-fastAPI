# Security baseline

- Telegram authentication always verifies the Telegram HMAC; an unverified `id_token` is never accepted as an authenticator.
- Telegram authentication rejects missing, stale, or future-dated `auth_date` values.
- Emergency/admin JWTs include an 8-hour expiry and invalid secrets are compared without logging secret prefixes.
- CORS is allowlist-based through `CORS_ALLOW_ORIGINS`; wildcard origins are not permitted with credentials.
- Admin API access requires both `status=active` and `is_admin=true`; emergency login is limited to 5 attempts per IP per minute.
- Responses include baseline browser security headers and local `.env` files must remain mode `600` and untracked.

Set the production frontend origin explicitly in the generated environment before deployment.
