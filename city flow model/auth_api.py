"""
auth_api.py - Server-side team sign-in.

Accounts come from the TEAM_MEMBERS environment variable (a JSON list), so no credentials are stored in the
source code or shipped to the browser. Each account gives "password_sha256" (recommended) or "password".
Without TEAM_MEMBERS a single public demo account is enabled so a fresh deployment still works.
"""

import hashlib
import hmac
import json
import os
import threading
import time

from flask import jsonify, request

DEMO_ACCOUNT = {
    "email": "demo@velociti.dev",
    "password": "velociti-demo",
    "name": "Demo Operator",
    "role": "System Operator",
    "badge": "",
    "department": "Traffic Operations",
}

MAX_FAILURES = 8        # failed attempts per client within WINDOW_SECONDS lock that client out
WINDOW_SECONDS = 300
_failures = {}
_lock = threading.Lock()


def _load_accounts():
    raw = os.environ.get("TEAM_MEMBERS", "").strip()
    if not raw:
        return [DEMO_ACCOUNT]
    try:
        accounts = [a for a in json.loads(raw) if isinstance(a, dict) and a.get("email")]
    except (ValueError, TypeError):
        print("[Auth] TEAM_MEMBERS is not valid JSON; falling back to the demo account.")
        return [DEMO_ACCOUNT]
    return accounts or [DEMO_ACCOUNT]


def _normalize_email(email):
    e = (email or "").strip().lower()
    if e.endswith("@kiit.acin"):  # common typo: missing dot
        e = e.replace("@kiit.acin", "@kiit.ac.in")
    elif "@" not in e and len(e) >= 6:  # roll number only
        e = f"{e}@kiit.ac.in"
    return e


def _password_ok(account, supplied):
    supplied = (supplied or "").strip()
    if account.get("password_sha256"):
        digest = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, str(account["password_sha256"]).strip().lower())
    stored = str(account.get("password", ""))
    return bool(stored) and hmac.compare_digest(supplied.encode("utf-8"), stored.encode("utf-8"))


def _client_key():
    # Behind a proxy the last X-Forwarded-For entry is the one the proxy itself appended.
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[-1].strip() if forwarded else request.remote_addr) or "unknown"


def _locked_out(key, now):
    with _lock:
        recent = [t for t in _failures.get(key, []) if now - t < WINDOW_SECONDS]
        _failures[key] = recent
        return len(recent) >= MAX_FAILURES


def register_auth_routes(app):
    @app.route("/api/auth/login", methods=["POST"])
    def team_login():
        data = request.get_json(silent=True) or {}
        email, password = data.get("email"), data.get("password")
        if not (str(email or "").strip() and str(password or "").strip()):
            return jsonify({"success": False,
                            "error": "Please provide both authorized email and security passcode."}), 400

        key, now = _client_key(), time.time()
        if _locked_out(key, now):
            return jsonify({"success": False, "error": "Too many failed attempts. Try again in a few minutes."}), 429

        wanted = _normalize_email(email)
        for account in _load_accounts():
            member = str(account["email"]).strip().lower()
            if wanted in (member, member.replace(".ac.in", ".acin")) and _password_ok(account, password):
                return jsonify({"success": True, "user": {
                    "email": account["email"],
                    "name": account.get("name", ""),
                    "role": account.get("role", "System Operator"),
                    "badge": account.get("badge", ""),
                    "department": account.get("department", "Traffic Operations"),
                    "loginTime": int(now * 1000),
                }})

        with _lock:
            _failures.setdefault(key, []).append(now)
        return jsonify({"success": False,
                        "error": "Access Denied: Unrecognized email or incorrect security passcode."}), 401
