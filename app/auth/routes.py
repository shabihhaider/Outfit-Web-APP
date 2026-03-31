"""
app/auth/routes.py
Authentication endpoints: register, login, refresh.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from app.extensions import db, bcrypt
from app.models_db import User

auth_bp = Blueprint("auth", __name__)

VALID_GENDERS = {"men", "women", "unisex"}


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /auth/register
    Body: {name, email, password, gender}
    Returns 201 on success, 400 if email taken, 422 if validation fails.
    """
    data = request.get_json(silent=True) or {}

    # Validate required fields
    for field in ("name", "email", "password", "gender"):
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 422

    name     = str(data["name"]).strip()
    email    = str(data["email"]).strip().lower()
    password = str(data["password"])
    gender   = str(data["gender"]).strip().lower()

    if not name or len(name) > 80:
        return jsonify({"error": "Name must be 1–80 characters."}), 422
    if "@" not in email or len(email) > 120:
        return jsonify({"error": "Invalid email address."}), 422
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 422
    if gender not in VALID_GENDERS:
        return jsonify({"error": f"gender must be one of: {', '.join(VALID_GENDERS)}."}), 422

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(name=name, email=email, password_hash=password_hash, gender=gender)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created.", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /auth/login
    Body: {email, password}
    Returns JWT access token on success, 401 on bad credentials.
    """
    data = request.get_json(silent=True) or {}

    email    = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "email and password are required."}), 422

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "user_id":      user.id,
        "name":         user.name,
        "gender":       user.gender,
        "avatar_url":   f"/uploads/{user.avatar_filename}" if user.avatar_filename else None,
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh():
    """
    POST /auth/refresh
    Requires valid (non-expired) JWT in Authorization header.
    Returns a fresh access token.

    Note: This is a simple re-issue, not full refresh-token rotation.
    Suitable for FYP scope.
    """
    user_id = get_jwt_identity()  # str
    new_token = create_access_token(identity=user_id)
    return jsonify({"access_token": new_token}), 200
