# Auth-Gated App Testing Playbook (Laurent.ia)

## Setup
- Auth provider: **Emergent Managed Google Auth**
- DB: MongoDB `laurentia` (env `DB_NAME`)
- Collections: `users`, `user_sessions`, `laurentia_instances`
- Session cookie: `session_token` (httpOnly, 7-day expiry, samesite=None, secure=True)
- Backend endpoints:
  - `POST /api/auth/session` — body `{ session_id }` from Emergent OAuth redirect → exchanges with Emergent, stores user + session, sets cookie
  - `GET  /api/auth/me` — returns current user (or 401)
  - `POST /api/auth/logout` — clears cookie + DB session
- FREK-ID derivation: `FREK-G-{sha256(google_email)[:10]}` — stable across logins

## Step 1: Create Test User + Session manually (bypass OAuth for tests)
```bash
mongosh --eval "
use('laurentia');
var userId = 'user_' + Math.random().toString(16).slice(2,14);
var sessionToken = 'test_session_' + Date.now();
var email = 'test.user.' + Date.now() + '@example.com';
var frekId = 'FREK-G-' + Math.random().toString(16).slice(2,12);
db.users.insertOne({
  user_id: userId,
  email: email,
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  frek_id: frekId,
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
db.laurentia_instances.insertOne({
  frek_id: frekId,
  version: 'free',
  tokens_used_month: 0,
  tokens_limit_month: 10000,
  jcc_balance: 0,
  status: 'active',
  created_at: new Date().toISOString(),
  last_active: new Date().toISOString()
});
print('SESSION_TOKEN: ' + sessionToken);
print('USER_ID: ' + userId);
print('FREK_ID: ' + frekId);
print('EMAIL: ' + email);
"
```

## Step 2: Backend curl tests
```bash
SESSION_TOKEN="<paste from step 1>"
API="$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)"

# Auth-aware /me — via cookie
curl -i "$API/api/auth/me" -H "Cookie: session_token=$SESSION_TOKEN"

# Auth-aware /me — via Authorization header
curl -i "$API/api/auth/me" -H "Authorization: Bearer $SESSION_TOKEN"

# Laurentia gateway (authenticated, FREK-ID auto-resolved server-side)
curl -i -X POST "$API/api/laurentia/query" \
  -H "Cookie: session_token=$SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"frek_id":"FREK-G-xxxxxxxxxx","input":"Salut.","context":{"app":"direct"}}'

# Sessions list (history menu)
curl -i "$API/api/laurentia/sessions/list" -H "Cookie: session_token=$SESSION_TOKEN"

# Logout
curl -i -X POST "$API/api/auth/logout" -H "Cookie: session_token=$SESSION_TOKEN"
```

## Step 3: Browser playwright tests
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "<SESSION_TOKEN from step 1>",
    "domain": "<your-frontend-domain>",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://<your-frontend-domain>/")
# Expect: NOT redirected to /login; header should show user avatar (initials)
# Click hamburger menu → drawer opens → user name + email visible + sessions list + Logout button
```

## Checklist
- [ ] User stored with `user_id` (UUID) and `frek_id` derived
- [ ] `session_token` cookie set with httpOnly + samesite=None + secure
- [ ] `/api/auth/me` returns user via cookie OR Authorization Bearer
- [ ] After login, frontend resolves FREK-ID automatically (no longer DEMO-SAYD)
- [ ] Hamburger menu opens drawer with profil + history + logout
- [ ] Logout clears cookie + redirects to landing
- [ ] Expired sessions return 401

## Success indicators
- ✅ `/api/auth/me` 200 with user data
- ✅ Dashboard loads without redirect when valid cookie present
- ✅ Conversations list under menu shows past sessions

## Failure indicators
- ❌ `/api/auth/me` 401 with valid token → check expires_at tz-awareness
- ❌ Cookie not set after `/auth/session` → check samesite/secure flags
- ❌ FREK-ID `null` after login → check derivation hash function

## Notes
- Demo mode is preserved: a guest visiting `/?frek_id=DEMO-SAYD` still works without login (graceful fallback).
- Emergent OAuth only manages identity; FREK-ID is OUR app-level identifier.
