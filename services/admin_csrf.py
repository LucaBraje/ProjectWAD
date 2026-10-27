"""Admin form CSRF helpers, shared by the Flask app and admin routes."""
import hmac
import secrets
from flask import request, session


def admin_form_token():
    if "admin_form_token" not in session:
        session["admin_form_token"] = secrets.token_urlsafe(32)
    return session["admin_form_token"]


def valid_admin_form_token():
    expected = session.get("admin_form_token")
    submitted = request.form.get("csrf_token", "")
    return bool(expected and hmac.compare_digest(expected, submitted))
