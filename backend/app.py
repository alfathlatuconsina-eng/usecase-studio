#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 PMO Dashboard - Backend API  (Option B, v2: roles + users + audit trail)
==============================================================================
  * PostgreSQL via SQLAlchemy
  * JWT auth; token carries user id, email, role
  * Roles: admin (all), editor (edit projects), viewer (read-only)
  * Admin-only user management endpoints
  * Audit log: every project create/update/delete records who/what/when
  * Serves the frontend so one process runs everything locally

  Run:  python app.py   ->  http://localhost:8000
==============================================================================
"""
import os
import json
import datetime as dt
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import (create_engine, Integer, String, Numeric, Text,
                        DateTime, ForeignKey, select, func)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            sessionmaker)
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL",
                        "postgresql+psycopg2://postgres@localhost:5432/pmo")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_HOURS = 12
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

engine = create_engine(DB_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

ROLES = ("admin", "editor", "viewer")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "role": self.role,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    group: Mapped[str] = mapped_column(String(50), default="Business")
    status: Mapped[str] = mapped_column(String(50), default="In-Progress")
    nature: Mapped[str] = mapped_column(String(120), default="")
    real: Mapped[float] = mapped_column(Numeric, nullable=True)
    tl: Mapped[float] = mapped_column(Numeric, nullable=True)
    bo: Mapped[float] = mapped_column(Numeric, nullable=True)
    br: Mapped[float] = mapped_column(Numeric, nullable=True)
    target: Mapped[str] = mapped_column(String(120), default="")
    orig: Mapped[str] = mapped_column(String(120), default="")
    owner: Mapped[str] = mapped_column(Text, default="")
    pm: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str] = mapped_column(Text, default="")
    next: Mapped[str] = mapped_column("next_act", Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    stop: Mapped[str] = mapped_column(Text, default="")
    reco: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "sort": self.sort, "name": self.name,
            "group": self.group, "status": self.status, "nature": self.nature,
            "real": None if self.real is None else float(self.real),
            "tl": None if self.tl is None else float(self.tl),
            "bo": None if self.bo is None else float(self.bo),
            "br": None if self.br is None else float(self.br),
            "target": self.target, "orig": self.orig, "owner": self.owner,
            "pm": self.pm, "phase": self.phase, "next": self.next,
            "risk": self.risk, "stop": self.stop, "reco": self.reco,
        }


class Audit(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    user_email: Mapped[str] = mapped_column(String(255), default="")
    action: Mapped[str] = mapped_column(String(20), default="")          # create/update/delete
    project_id: Mapped[int] = mapped_column(Integer, nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), default="")
    changes: Mapped[str] = mapped_column(Text, default="")               # JSON: {field:[old,new]}

    def to_dict(self):
        try:
            ch = json.loads(self.changes) if self.changes else {}
        except Exception:
            ch = {}
        return {"id": self.id, "ts": self.ts.isoformat() if self.ts else None,
                "user": self.user_email, "action": self.action,
                "project_id": self.project_id, "project_name": self.project_name,
                "changes": ch}


app = Flask(__name__, static_folder=None)
CORS(app)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def make_token(user):
    payload = {"uid": user.id, "email": user.email, "role": user.role,
               "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode():
    hdr = request.headers.get("Authorization", "")
    if not hdr.startswith("Bearer "):
        return None, ("Missing token", 401)
    try:
        return jwt.decode(hdr.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, ("Token expired, please sign in again", 401)
    except jwt.InvalidTokenError:
        return None, ("Invalid token", 401)


def require(*allowed_roles):
    """Decorator: valid token required; if roles given, user.role must match."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            claims, err = _decode()
            if err:
                return jsonify({"error": err[0]}), err[1]
            if allowed_roles and claims.get("role") not in allowed_roles:
                return jsonify({"error": "You don't have permission for this action"}), 403
            request.user = claims
            return fn(*a, **k)
        return wrapper
    return deco


def _clean(v):
    """Make a value JSON-safe (Postgres returns Decimal for numerics)."""
    from decimal import Decimal
    if isinstance(v, Decimal):
        f = float(v)
        return int(f) if f == int(f) else f
    return v


def log_audit(s, action, proj, changes=None):
    safe = {}
    for k, pair in (changes or {}).items():
        if isinstance(pair, list) and len(pair) == 2:
            safe[k] = [_clean(pair[0]), _clean(pair[1])]
        else:
            safe[k] = _clean(pair)
    s.add(Audit(user_email=request.user.get("email", "?"), action=action,
                project_id=proj.id, project_name=proj.name,
                changes=json.dumps(safe, ensure_ascii=False)))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.post("/api/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    with Session() as s:
        user = s.scalar(select(User).where(User.email == email))
        if not user or not bcrypt.checkpw(pw.encode(), user.pw_hash.encode()):
            return jsonify({"error": "Incorrect email or password"}), 401
        return jsonify({"token": make_token(user), "email": user.email, "role": user.role})


@app.get("/api/me")
@require()
def me():
    return jsonify({"email": request.user["email"], "role": request.user["role"]})


# ---------------------------------------------------------------------------
# Projects  (viewer can read; editor/admin can write)
# ---------------------------------------------------------------------------
FIELDS = ["sort", "name", "group", "status", "nature", "real", "tl", "bo", "br",
          "target", "orig", "owner", "pm", "phase", "next", "risk", "stop", "reco"]


@app.get("/api/projects")
@require()  # any logged-in role
def list_projects():
    with Session() as s:
        rows = s.scalars(select(Project).order_by(Project.sort, Project.id)).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/projects")
@require("admin", "editor")
def create_project():
    data = request.get_json(force=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    with Session() as s:
        p = Project()
        for f in FIELDS:
            if f in data:
                setattr(p, f, data[f])
        s.add(p); s.flush()
        log_audit(s, "create", p, {f: [None, data.get(f)] for f in FIELDS if data.get(f) not in (None, "")})
        s.commit()
        return jsonify(p.to_dict()), 201


@app.put("/api/projects/<int:pid>")
@require("admin", "editor")
def update_project(pid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        p = s.get(Project, pid)
        if not p:
            return jsonify({"error": "not found"}), 404
        changes = {}
        for f in FIELDS:
            if f in data:
                old = getattr(p, f)
                old_cmp = float(old) if isinstance(old, (int, float)) else old
                new = data[f]
                if str(old_cmp) != str(new):
                    changes[f] = [old_cmp, new]
                setattr(p, f, new)
        if changes:
            log_audit(s, "update", p, changes)
        s.commit()
        return jsonify(p.to_dict())


@app.delete("/api/projects/<int:pid>")
@require("admin", "editor")
def delete_project(pid):
    with Session() as s:
        p = s.get(Project, pid)
        if not p:
            return jsonify({"error": "not found"}), 404
        log_audit(s, "delete", p, {"name": [p.name, None]})
        s.delete(p); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Users  (admin only)
# ---------------------------------------------------------------------------
@app.get("/api/users")
@require("admin")
def list_users():
    with Session() as s:
        rows = s.scalars(select(User).order_by(User.id)).all()
        return jsonify([u.to_dict() for u in rows])


@app.post("/api/users")
@require("admin")
def create_user():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    role = data.get("role") or "viewer"
    if not email or not pw:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ROLES:
        return jsonify({"error": "role must be admin, editor, or viewer"}), 400
    with Session() as s:
        if s.scalar(select(User).where(User.email == email)):
            return jsonify({"error": "a user with that email already exists"}), 409
        u = User(email=email, role=role,
                 pw_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        s.add(u); s.commit()
        return jsonify(u.to_dict()), 201


@app.put("/api/users/<int:uid>")
@require("admin")
def update_user(uid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        u = s.get(User, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if "role" in data:
            if data["role"] not in ROLES:
                return jsonify({"error": "invalid role"}), 400
            # don't allow removing the last admin
            if u.role == "admin" and data["role"] != "admin":
                admins = s.scalar(select(func.count(User.id)).where(User.role == "admin"))
                if admins <= 1:
                    return jsonify({"error": "cannot demote the last admin"}), 400
            u.role = data["role"]
        if data.get("password"):
            u.pw_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        s.commit()
        return jsonify(u.to_dict())


@app.delete("/api/users/<int:uid>")
@require("admin")
def delete_user(uid):
    with Session() as s:
        u = s.get(User, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if u.email == request.user["email"]:
            return jsonify({"error": "you cannot delete your own account"}), 400
        if u.role == "admin":
            admins = s.scalar(select(func.count(User.id)).where(User.role == "admin"))
            if admins <= 1:
                return jsonify({"error": "cannot delete the last admin"}), 400
        s.delete(u); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Audit log  (admin only)
# ---------------------------------------------------------------------------
@app.get("/api/audit")
@require("admin")
def audit_log():
    limit = min(int(request.args.get("limit", 200)), 1000)
    with Session() as s:
        rows = s.scalars(select(Audit).order_by(Audit.ts.desc()).limit(limit)).all()
        return jsonify([a.to_dict() for a in rows])


@app.get("/api/health")
def health():
    try:
        with Session() as s:
            s.execute(select(func.count(Project.id)))
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "db-error", "detail": str(e)}), 500


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
@app.get("/")
def landing():
    return send_from_directory(FRONTEND_DIR, "landing.html")


@app.get("/pmo")
def pmo():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/people")
def people():
    return send_from_directory(FRONTEND_DIR, "people.html")


@app.get("/quality")
def quality():
    return send_from_directory(FRONTEND_DIR, "quality.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    print(f"DB: {DB_URL}")
    print("Open http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
