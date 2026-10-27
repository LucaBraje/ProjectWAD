"""Extracted routes from the original app.py."""
from flask import request, flash, redirect, url_for, render_template
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User


def register():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check that all fields are filled in
        if not username or not email or not password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("register"))

        # Check field lengths
        if len(username) > 50 or len(email) > 120:
            flash("Username or email is too long.", "danger")
            return redirect(url_for("register"))

        # Check that passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        # Basic password length requirement
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("register"))

        # Check whether the username already exists
        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:
            flash("This username is already taken.", "danger")
            return redirect(url_for("register"))

        # Check whether the email already exists
        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("register"))

        # Create the account
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="user"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


def login():

    # Already logged-in users don't need to log in again
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":

        username_or_email = request.form.get(
            "username_or_email", ""
        ).strip()

        password = request.form.get("password", "")

        # Find the user by username or email
        user = User.query.filter(
            (User.username == username_or_email) |
            (User.email == username_or_email.lower())
        ).first()

        # Verify credentials
        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            flash(
                f"Welcome back, {user.username}!",
                "success"
            )

            return redirect(url_for("home"))

        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@login_required
def logout():
    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("home"))

