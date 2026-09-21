# Security baseline

- Telegram authentication always verifies the Telegram HMAC; an unverified `id_token` is never accepted as an authenticator.
- Telegram authentication rejects missing, stale, or future-dated `auth_date` values.
- Telegram-authenticated admin JWTs include an 8-hour expiry; JWT signing keys are never accepted as login credentials.
- CORS is allowlist-based through `CORS_ALLOW_ORIGINS`; wildcard origins are not permitted with credentials.
- Admin API access requires both `status=active` and `is_admin=true`; authentication is available through Telegram only.
- Responses include baseline browser security headers and local `.env` files must remain mode `600` and untracked.

Set the production frontend origin explicitly in the generated environment before deployment.
