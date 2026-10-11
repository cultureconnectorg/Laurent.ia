"""C1 end-to-end: FREK-ID passkey through Laurent.ia and the real FREKCORE, in a real browser.

Chromium with a virtual WebAuthn authenticator (DevTools protocol) uses the real UI:
  1. a FREK-ID other than the principal is refused;
  2. register the principal's passkey (FREKCORE verifies and notarizes it), then sign in;
  3. a protected route answers with the session, and FREKCORE's proof is retrievable;
  4. sign out, then sign in again with the same passkey;
  5. no request leaves the stack.
  6. FREKCORE revokes the FREK-ID: the open session is closed and sign-in is refused;
  7. FREKCORE deactivates the cvl-brain client: Laurent.ia can no longer call FREKCORE.
  Enrollment (security review fix): without the one-time code, or with a wrong one, the
  first passkey cannot be registered; once bound, registration is closed even with the code.
Usage (from deploy/): python verify/passkey_check.py <base> <principal FREK-ID> <enrollment code> [chromium]
"""
import json
import subprocess
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE, FREK_ID, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
CHROMIUM = (sys.argv[4] or None) if len(sys.argv) > 4 else None
origin = urlparse(BASE).netloc
foreign, results = [], {}


def step(name, ok, detail=""):
    results[name] = bool(ok)
    print(f"{'OK  ' if ok else 'FAIL'} {name} {detail}")


def api(page, method, path, body=None):
    return page.evaluate(
        """async ([m, p, b]) => { const r = await fetch(p, {method: m, credentials: 'include',
             headers: b ? {'Content-Type': 'application/json'} : {}, body: b ? JSON.stringify(b) : undefined});
           let j = null; try { j = await r.json(); } catch (_) {} return {status: r.status, body: j}; }""",
        [method, path, body])


def wait_signed_in(page, seconds=30):
    for _ in range(seconds * 2):
        if api(page, "GET", "/api/auth/me")["status"] == 200:
            return True
        page.wait_for_timeout(500)
    return False


def use_menu(page, frek_id, test_id, code=None):
    page.get_by_test_id("header-menu-btn").click()
    page.get_by_test_id("menu-frek-input").fill(frek_id)
    if code is not None:
        page.get_by_test_id("menu-enroll-code").fill(code)
    page.get_by_test_id(test_id).click()


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
    ctx = browser.new_context(locale="fr-FR")
    page = ctx.new_page()
    page.on("request", lambda r: foreign.append(r.url)
            if r.url.startswith(("http://", "https://")) and urlparse(r.url).netloc != origin else None)
    cdp = ctx.new_cdp_session(page)
    cdp.send("WebAuthn.enable")
    cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
        "protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
        "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}})
    page.goto(f"{BASE}/laurentia", wait_until="networkidle")

    # 0. enrollment protection (the principal's FREK-ID is known to the attacker here)
    r = api(page, "POST", "/api/auth/passkey/register/begin", {"frek_id": FREK_ID})
    step("first passkey refused without the enrollment code", r["status"] == 403, str(r["status"]))
    use_menu(page, FREK_ID, "menu-passkey-register", code="wrong-code-0000")
    err = page.get_by_test_id("menu-frek-error")
    err.wait_for(timeout=20000)
    step("first passkey refused with a wrong code", "code d'inscription" in err.inner_text().lower(), err.inner_text())
    page.keyboard.press("Escape")

    # 1. intruder
    use_menu(page, "FREK-INTRUDER-0000", "menu-passkey-register", code=CODE)
    err = page.get_by_test_id("menu-frek-error")
    err.wait_for(timeout=20000)
    step("intruder FREK-ID refused", "pas autorisé" in err.inner_text().lower(), err.inner_text())
    page.keyboard.press("Escape")

    # 2. register (with the one-time code) + sign in
    use_menu(page, FREK_ID, "menu-passkey-register", code=CODE)
    wait_signed_in(page)
    me = api(page, "GET", "/api/auth/me")
    step("registered then signed in", me["status"] == 200 and me["body"]["frek_id"] == FREK_ID, str(me["status"]))

    r = api(page, "POST", "/api/auth/passkey/register/begin", {"frek_id": FREK_ID, "enrollment_token": CODE})
    step("registration closed once bound, even with the code", r["status"] == 403, str(r["status"]))

    # 3. protected route + proof
    s = api(page, "GET", "/api/laurentia/sessions/list")
    step("protected route with the session", s["status"] == 200, str(s["status"]))
    pr = api(page, "GET", "/api/auth/passkey/proof")
    ok = pr["status"] == 200 and pr["body"]["proof"] and pr["body"]["chain"]
    step("FREKCORE proof of holder verification", ok, json.dumps(pr["body"])[:300])

    # 4. sign out, sign in again
    api(page, "POST", "/api/auth/logout")
    step("signed out", api(page, "GET", "/api/laurentia/sessions/list")["status"] == 401)
    page.reload(wait_until="networkidle")
    use_menu(page, FREK_ID, "menu-frek-submit")
    wait_signed_in(page)
    step("signed in again with the passkey", api(page, "GET", "/api/laurentia/sessions/list")["status"] == 200)

    # 6. revocation in FREKCORE (through Laurent.ia's API client, with FREKCORE's permission)
    out = subprocess.run(["docker", "compose", "exec", "-T", "-e", f"FID={FREK_ID}", "backend", "python", "-c",
                          "import asyncio, os; from services import frekcore_client as f; "
                          "print(asyncio.run(f.revoke_identity(os.environ['FID'], 'test de revocation C1')))"],
                         capture_output=True, text=True)
    step("FREKCORE revoked the FREK-ID", out.returncode == 0 and "revoked" in out.stdout, out.stdout[-200:] + out.stderr[-200:])
    page.wait_for_timeout(3000)
    r = api(page, "GET", "/api/laurentia/sessions/list")
    step("open session closed after revocation", r["status"] == 401, json.dumps(r["body"]))
    page.reload(wait_until="networkidle")
    use_menu(page, FREK_ID, "menu-frek-submit")
    err = page.get_by_test_id("menu-frek-error")
    err.wait_for(timeout=20000)
    step("sign-in refused after revocation", not wait_signed_in(page, 3), err.inner_text())
    page.keyboard.press("Escape")

    # 7. FREKCORE deactivates the client: every token of cvl-brain is revoked
    out = subprocess.run(["sh", "-c", ". ./.env && docker compose exec -T -e ADMIN_KEY=\"$FREK_SECRET_KEY\" backend sh -c "
                          "'curl -sf -X PATCH http://frekcore:8001/api/v1/admin/clients/cvl-brain -H \"X-Admin-Key: $ADMIN_KEY\" "
                          "-H \"Content-Type: application/json\" -d \"{\\\"active\\\": false}\"'"],
                         capture_output=True, text=True)
    st = subprocess.run(["docker", "compose", "exec", "-T", "backend", "python", "-c",
                         "import asyncio; from services import frekcore_client as f\n"
                         "try:\n  asyncio.run(f.emit_identity('x@example.invalid')); print('ALLOWED')\n"
                         "except f.FrekcoreError as e: print('REFUSED', e.status)"],
                        capture_output=True, text=True)
    step("deactivated client refused by FREKCORE", "REFUSED 401" in st.stdout, out.stdout[-120:] + " | " + st.stdout.strip())
    browser.close()

step("no request outside the stack", not foreign, "; ".join(foreign[:5]))
sys.exit(0 if all(results.values()) else 1)
