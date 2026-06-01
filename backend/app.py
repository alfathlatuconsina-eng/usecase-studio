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
import uuid
import datetime as dt
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
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

# E-Library file storage (not publicly listable; served only via authed endpoint)
ELIB_UPLOAD_DIR = os.environ.get(
    "ELIBRARY_UPLOAD_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "elibrary"))
os.makedirs(ELIB_UPLOAD_DIR, exist_ok=True)
ELIB_MAX_BYTES = 25 * 1024 * 1024  # 25 MB per file
ELIB_ALLOWED_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
                    "txt", "csv", "png", "jpg", "jpeg", "gif", "zip"}
ELIBRARY_ROLES = ("super_admin", "admin", "user")

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


# ---------------------------------------------------------------------------
# People Development — DB models
# ---------------------------------------------------------------------------
class PeopleTraining(Base):
    __tablename__ = "people_training"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="")
    method: Mapped[str] = mapped_column(String(80), default="")
    organizer: Mapped[str] = mapped_column(String(255), default="")
    date_start: Mapped[str] = mapped_column(String(20), default="")
    date_end: Mapped[str] = mapped_column(String(20), default="")
    target_pax: Mapped[int] = mapped_column(Integer, nullable=True)
    actual_pax: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Planned")
    budget: Mapped[float] = mapped_column(Numeric, nullable=True)
    realization: Mapped[float] = mapped_column(Numeric, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "method": self.method, "organizer": self.organizer,
            "date_start": self.date_start, "date_end": self.date_end,
            "target_pax": self.target_pax, "actual_pax": self.actual_pax,
            "status": self.status,
            "budget": None if self.budget is None else float(self.budget),
            "realization": None if self.realization is None else float(self.realization),
            "notes": self.notes,
        }


class PeopleEvaluation(Base):
    __tablename__ = "people_evaluation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("people_training.id", ondelete="CASCADE"), nullable=False)
    reaction_score: Mapped[float] = mapped_column(Numeric, nullable=True)  # 1–5 Kirkpatrick L1
    learning_score: Mapped[float] = mapped_column(Numeric, nullable=True)  # 0–100 Kirkpatrick L2
    respondents: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "training_id": self.training_id,
            "reaction_score": None if self.reaction_score is None else float(self.reaction_score),
            "learning_score": None if self.learning_score is None else float(self.learning_score),
            "respondents": self.respondents, "notes": self.notes,
        }


class PeopleCertification(Base):
    __tablename__ = "people_certifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    holder: Mapped[str] = mapped_column(String(255), default="")
    cert_type: Mapped[str] = mapped_column(String(80), default="Certification")
    issue_date: Mapped[str] = mapped_column(String(20), default="")
    expiry_date: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(50), default="Active")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "holder": self.holder,
            "cert_type": self.cert_type, "issue_date": self.issue_date,
            "expiry_date": self.expiry_date, "status": self.status,
            "notes": self.notes,
        }


class PeopleUser(Base):
    """Separate credential table for the People Development dashboard.
    Mirrors User but is a completely independent set of accounts."""
    __tablename__ = "people_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "role": self.role,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class QualityUser(Base):
    """Separate credential table for the Service Quality dashboard."""
    __tablename__ = "quality_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "role": self.role,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class QualityBranch(Base):
    """One branch's Service Survey (Survei Layanan) result for a period.
    Scores are 0–100. Intangible = CS/Teller/Security; Tangible = facilities."""
    __tablename__ = "quality_branches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(40), default="")          # e.g. "Period 35"
    period_label: Mapped[str] = mapped_column(String(60), default="")    # e.g. "Mar–Apr 2026"
    branch: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str] = mapped_column(String(80), default="")
    cs_score: Mapped[float] = mapped_column(Numeric, nullable=True)        # Customer Service
    teller_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    security_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    intangible_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    tangible_score: Mapped[float] = mapped_column(Numeric, nullable=True)  # facilities
    overall_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="")            # Excellent/Good/Needs Improvement
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        def f(v): return None if v is None else float(v)
        return {
            "id": self.id, "period": self.period, "period_label": self.period_label,
            "branch": self.branch, "region": self.region,
            "cs_score": f(self.cs_score), "teller_score": f(self.teller_score),
            "security_score": f(self.security_score),
            "intangible_score": f(self.intangible_score),
            "tangible_score": f(self.tangible_score),
            "overall_score": f(self.overall_score),
            "status": self.status, "notes": self.notes,
        }


class ElibraryUser(Base):
    """Separate credential table for the E-Library module.
    Roles: super_admin (manage users), admin (subjects/categories/files), user (view)."""
    __tablename__ = "elibrary_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "role": self.role,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class ElibrarySubject(Base):
    __tablename__ = "elibrary_subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class ElibraryCategory(Base):
    __tablename__ = "elibrary_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elibrary_subjects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "subject_id": self.subject_id, "name": self.name}


class ElibraryDocument(Base):
    __tablename__ = "elibrary_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elibrary_subjects.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("elibrary_categories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)   # uuid on disk
    original_name: Mapped[str] = mapped_column(String(255), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "subject_id": self.subject_id, "category_id": self.category_id,
            "title": self.title, "original_name": self.original_name,
            "size_bytes": self.size_bytes, "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = ELIB_MAX_BYTES
CORS(app)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def make_token(user, module):
    """module is 'pmo' or 'people' — a token is only valid for its own module."""
    payload = {"uid": user.id, "email": user.email, "role": user.role,
               "module": module,
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
    """Decorator: valid token required; if roles given, user.role must match.

    The token is also module-scoped: requests to /api/people/* require a token
    issued for the People dashboard, everything else requires a PMO token.
    This keeps the two user sets fully separated."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            claims, err = _decode()
            if err:
                return jsonify({"error": err[0]}), err[1]
            if request.path.startswith("/api/people/"):
                expected_module = "people"
            elif request.path.startswith("/api/quality/"):
                expected_module = "quality"
            elif request.path.startswith("/api/elibrary/"):
                expected_module = "elibrary"
            else:
                expected_module = "pmo"
            if claims.get("module") != expected_module:
                return jsonify({"error": "Please sign in to this dashboard"}), 403
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
def _do_login(model, module):
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    with Session() as s:
        user = s.scalar(select(model).where(model.email == email))
        if not user or not bcrypt.checkpw(pw.encode(), user.pw_hash.encode()):
            return jsonify({"error": "Incorrect email or password"}), 401
        return jsonify({"token": make_token(user, module),
                        "email": user.email, "role": user.role})


@app.post("/api/pmo/login")
def pmo_login_api():
    return _do_login(User, "pmo")


@app.post("/api/people/login")
def people_login_api():
    return _do_login(PeopleUser, "people")


@app.post("/api/quality/login")
def quality_login_api():
    return _do_login(QualityUser, "quality")


@app.post("/api/elibrary/login")
def elibrary_login_api():
    return _do_login(ElibraryUser, "elibrary")


# legacy alias — old PMO clients posted here
@app.post("/api/login")
def login():
    return _do_login(User, "pmo")


@app.get("/api/pmo/me")
@require()
def pmo_me():
    return jsonify({"email": request.user["email"], "role": request.user["role"]})


@app.get("/api/people/me")
@require()
def people_me():
    return jsonify({"email": request.user["email"], "role": request.user["role"]})


@app.get("/api/quality/me")
@require()
def quality_me():
    return jsonify({"email": request.user["email"], "role": request.user["role"]})


@app.get("/api/elibrary/me")
@require()
def elibrary_me():
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
# People Development — API
# ---------------------------------------------------------------------------
PEOPLE_TR_FIELDS = ["name", "category", "method", "organizer", "date_start",
                    "date_end", "target_pax", "actual_pax", "status",
                    "budget", "realization", "notes"]
PEOPLE_EV_FIELDS = ["training_id", "reaction_score", "learning_score", "respondents", "notes"]
PEOPLE_CE_FIELDS = ["name", "holder", "cert_type", "issue_date", "expiry_date", "status", "notes"]


@app.get("/api/people/summary")
@require()
def people_summary():
    today = dt.date.today()
    soon30 = (today + dt.timedelta(days=30)).isoformat()
    today_s = today.isoformat()
    this_year = str(today.year)
    with Session() as s:
        trainings = s.scalars(select(PeopleTraining)).all()
        year_tr = [t for t in trainings if (t.date_start or "").startswith(this_year)]
        completed = [t for t in year_tr if t.status == "Completed"]
        rate = round(len(completed) / len(year_tr) * 100) if year_tr else 0

        evals = s.scalars(select(PeopleEvaluation)).all()
        scores = [float(e.reaction_score) for e in evals if e.reaction_score is not None]
        avg_score = round(sum(scores) / len(scores), 2) if scores else None

        certs = s.scalars(select(PeopleCertification)).all()
        exp_soon = [c for c in certs
                    if c.expiry_date and today_s <= c.expiry_date <= soon30
                    and c.status != "Renewed"]

        return jsonify({
            "total_trainings_year": len(year_tr),
            "completion_rate": rate,
            "avg_reaction_score": avg_score,
            "expiring_certs_30d": len(exp_soon),
        })


@app.get("/api/people/reminders")
@require()
def people_reminders():
    today = dt.date.today()
    cutoff = (today + dt.timedelta(days=60)).isoformat()
    today_s = today.isoformat()
    with Session() as s:
        certs = s.scalars(
            select(PeopleCertification)
            .where(PeopleCertification.expiry_date != "")
            .order_by(PeopleCertification.expiry_date)
        ).all()
        result = []
        for c in certs:
            if c.expiry_date <= cutoff or c.status in ("Expiring", "Expired"):
                try:
                    days_left = (dt.date.fromisoformat(c.expiry_date) - today).days
                except ValueError:
                    days_left = None
                row = c.to_dict()
                row["days_left"] = days_left
                result.append(row)
        return jsonify(result)


@app.get("/api/people/trainings")
@require()
def list_people_trainings():
    with Session() as s:
        rows = s.scalars(
            select(PeopleTraining).order_by(PeopleTraining.date_start.desc(), PeopleTraining.id.desc())
        ).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/people/trainings")
@require("admin", "editor")
def create_people_training():
    data = request.get_json(force=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    with Session() as s:
        t = PeopleTraining()
        for f in PEOPLE_TR_FIELDS:
            if f in data:
                setattr(t, f, data[f])
        s.add(t); s.commit()
        return jsonify(t.to_dict()), 201


@app.put("/api/people/trainings/<int:tid>")
@require("admin", "editor")
def update_people_training(tid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        t = s.get(PeopleTraining, tid)
        if not t:
            return jsonify({"error": "not found"}), 404
        for f in PEOPLE_TR_FIELDS:
            if f in data:
                setattr(t, f, data[f])
        s.commit()
        return jsonify(t.to_dict())


@app.delete("/api/people/trainings/<int:tid>")
@require("admin", "editor")
def delete_people_training(tid):
    with Session() as s:
        t = s.get(PeopleTraining, tid)
        if not t:
            return jsonify({"error": "not found"}), 404
        s.delete(t); s.commit()
        return jsonify({"ok": True})


@app.get("/api/people/evaluations")
@require()
def list_people_evaluations():
    with Session() as s:
        rows = s.scalars(select(PeopleEvaluation).order_by(PeopleEvaluation.id)).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/people/evaluations")
@require("admin", "editor")
def create_people_evaluation():
    data = request.get_json(force=True) or {}
    if not data.get("training_id"):
        return jsonify({"error": "training_id is required"}), 400
    with Session() as s:
        e = PeopleEvaluation()
        for f in PEOPLE_EV_FIELDS:
            if f in data:
                setattr(e, f, data[f])
        s.add(e); s.commit()
        return jsonify(e.to_dict()), 201


@app.put("/api/people/evaluations/<int:eid>")
@require("admin", "editor")
def update_people_evaluation(eid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        e = s.get(PeopleEvaluation, eid)
        if not e:
            return jsonify({"error": "not found"}), 404
        for f in PEOPLE_EV_FIELDS:
            if f in data:
                setattr(e, f, data[f])
        s.commit()
        return jsonify(e.to_dict())


@app.delete("/api/people/evaluations/<int:eid>")
@require("admin", "editor")
def delete_people_evaluation(eid):
    with Session() as s:
        e = s.get(PeopleEvaluation, eid)
        if not e:
            return jsonify({"error": "not found"}), 404
        s.delete(e); s.commit()
        return jsonify({"ok": True})


@app.get("/api/people/certifications")
@require()
def list_people_certifications():
    with Session() as s:
        rows = s.scalars(
            select(PeopleCertification).order_by(PeopleCertification.expiry_date)
        ).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/people/certifications")
@require("admin", "editor")
def create_people_certification():
    data = request.get_json(force=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    if not (data.get("expiry_date") or "").strip():
        return jsonify({"error": "expiry_date is required"}), 400
    with Session() as s:
        c = PeopleCertification()
        for f in PEOPLE_CE_FIELDS:
            if f in data:
                setattr(c, f, data[f])
        s.add(c); s.commit()
        return jsonify(c.to_dict()), 201


@app.put("/api/people/certifications/<int:cid>")
@require("admin", "editor")
def update_people_certification(cid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        c = s.get(PeopleCertification, cid)
        if not c:
            return jsonify({"error": "not found"}), 404
        for f in PEOPLE_CE_FIELDS:
            if f in data:
                setattr(c, f, data[f])
        s.commit()
        return jsonify(c.to_dict())


@app.delete("/api/people/certifications/<int:cid>")
@require("admin", "editor")
def delete_people_certification(cid):
    with Session() as s:
        c = s.get(PeopleCertification, cid)
        if not c:
            return jsonify({"error": "not found"}), 404
        s.delete(c); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# People Development — Users  (People admin only; separate from PMO users)
# ---------------------------------------------------------------------------
@app.get("/api/people/users")
@require("admin")
def list_people_users():
    with Session() as s:
        rows = s.scalars(select(PeopleUser).order_by(PeopleUser.id)).all()
        return jsonify([u.to_dict() for u in rows])


@app.post("/api/people/users")
@require("admin")
def create_people_user():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    role = data.get("role") or "viewer"
    if not email or not pw:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ROLES:
        return jsonify({"error": "role must be admin, editor, or viewer"}), 400
    with Session() as s:
        if s.scalar(select(PeopleUser).where(PeopleUser.email == email)):
            return jsonify({"error": "a user with that email already exists"}), 409
        u = PeopleUser(email=email, role=role,
                       pw_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        s.add(u); s.commit()
        return jsonify(u.to_dict()), 201


@app.put("/api/people/users/<int:uid>")
@require("admin")
def update_people_user(uid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        u = s.get(PeopleUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if "role" in data:
            if data["role"] not in ROLES:
                return jsonify({"error": "invalid role"}), 400
            if u.role == "admin" and data["role"] != "admin":
                admins = s.scalar(select(func.count(PeopleUser.id)).where(PeopleUser.role == "admin"))
                if admins <= 1:
                    return jsonify({"error": "cannot demote the last admin"}), 400
            u.role = data["role"]
        if data.get("password"):
            u.pw_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        s.commit()
        return jsonify(u.to_dict())


@app.delete("/api/people/users/<int:uid>")
@require("admin")
def delete_people_user(uid):
    with Session() as s:
        u = s.get(PeopleUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if u.email == request.user["email"]:
            return jsonify({"error": "you cannot delete your own account"}), 400
        if u.role == "admin":
            admins = s.scalar(select(func.count(PeopleUser.id)).where(PeopleUser.role == "admin"))
            if admins <= 1:
                return jsonify({"error": "cannot delete the last admin"}), 400
        s.delete(u); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Service Quality — API  (Survei Layanan / branch service survey)
# ---------------------------------------------------------------------------
QUALITY_FIELDS = ["period", "period_label", "branch", "region", "cs_score",
                  "teller_score", "security_score", "intangible_score",
                  "tangible_score", "overall_score", "status", "notes"]


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


@app.get("/api/quality/summary")
@require()
def quality_summary():
    with Session() as s:
        rows = s.scalars(select(QualityBranch)).all()
        if not rows:
            return jsonify({"overall_avg": None, "cs_avg": None, "teller_avg": None,
                            "tangible_avg": None, "branches_count": 0,
                            "top": None, "bottom": None})
        overall = [float(r.overall_score) for r in rows if r.overall_score is not None]
        ranked = sorted([r for r in rows if r.overall_score is not None],
                        key=lambda r: float(r.overall_score), reverse=True)
        return jsonify({
            "overall_avg": _avg([float(r.overall_score) for r in rows if r.overall_score is not None]),
            "cs_avg":      _avg([float(r.cs_score) for r in rows if r.cs_score is not None]),
            "teller_avg":  _avg([float(r.teller_score) for r in rows if r.teller_score is not None]),
            "tangible_avg":_avg([float(r.tangible_score) for r in rows if r.tangible_score is not None]),
            "branches_count": len(rows),
            "top":    ({"branch": ranked[0].branch, "score": float(ranked[0].overall_score)} if ranked else None),
            "bottom": ({"branch": ranked[-1].branch, "score": float(ranked[-1].overall_score)} if ranked else None),
        })


@app.get("/api/quality/branches")
@require()
def list_quality_branches():
    with Session() as s:
        rows = s.scalars(
            select(QualityBranch).order_by(QualityBranch.overall_score.desc(), QualityBranch.id)
        ).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/quality/branches")
@require("admin", "editor")
def create_quality_branch():
    data = request.get_json(force=True) or {}
    if not (data.get("branch") or "").strip():
        return jsonify({"error": "branch is required"}), 400
    with Session() as s:
        b = QualityBranch()
        for f in QUALITY_FIELDS:
            if f in data:
                setattr(b, f, data[f])
        s.add(b); s.commit()
        return jsonify(b.to_dict()), 201


@app.put("/api/quality/branches/<int:bid>")
@require("admin", "editor")
def update_quality_branch(bid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        b = s.get(QualityBranch, bid)
        if not b:
            return jsonify({"error": "not found"}), 404
        for f in QUALITY_FIELDS:
            if f in data:
                setattr(b, f, data[f])
        s.commit()
        return jsonify(b.to_dict())


@app.delete("/api/quality/branches/<int:bid>")
@require("admin", "editor")
def delete_quality_branch(bid):
    with Session() as s:
        b = s.get(QualityBranch, bid)
        if not b:
            return jsonify({"error": "not found"}), 404
        s.delete(b); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Service Quality — Users  (Quality admin only; separate from PMO/People)
# ---------------------------------------------------------------------------
@app.get("/api/quality/users")
@require("admin")
def list_quality_users():
    with Session() as s:
        rows = s.scalars(select(QualityUser).order_by(QualityUser.id)).all()
        return jsonify([u.to_dict() for u in rows])


@app.post("/api/quality/users")
@require("admin")
def create_quality_user():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    role = data.get("role") or "viewer"
    if not email or not pw:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ROLES:
        return jsonify({"error": "role must be admin, editor, or viewer"}), 400
    with Session() as s:
        if s.scalar(select(QualityUser).where(QualityUser.email == email)):
            return jsonify({"error": "a user with that email already exists"}), 409
        u = QualityUser(email=email, role=role,
                        pw_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        s.add(u); s.commit()
        return jsonify(u.to_dict()), 201


@app.put("/api/quality/users/<int:uid>")
@require("admin")
def update_quality_user(uid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        u = s.get(QualityUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if "role" in data:
            if data["role"] not in ROLES:
                return jsonify({"error": "invalid role"}), 400
            if u.role == "admin" and data["role"] != "admin":
                admins = s.scalar(select(func.count(QualityUser.id)).where(QualityUser.role == "admin"))
                if admins <= 1:
                    return jsonify({"error": "cannot demote the last admin"}), 400
            u.role = data["role"]
        if data.get("password"):
            u.pw_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        s.commit()
        return jsonify(u.to_dict())


@app.delete("/api/quality/users/<int:uid>")
@require("admin")
def delete_quality_user(uid):
    with Session() as s:
        u = s.get(QualityUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if u.email == request.user["email"]:
            return jsonify({"error": "you cannot delete your own account"}), 400
        if u.role == "admin":
            admins = s.scalar(select(func.count(QualityUser.id)).where(QualityUser.role == "admin"))
            if admins <= 1:
                return jsonify({"error": "cannot delete the last admin"}), 400
        s.delete(u); s.commit()
        return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# E-Library — Subjects, Categories, Documents (with file upload)
# ---------------------------------------------------------------------------
def _elib_ext_ok(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ELIB_ALLOWED_EXT


@app.get("/api/elibrary/summary")
@require()
def elibrary_summary():
    with Session() as s:
        subs = s.scalar(select(func.count(ElibrarySubject.id))) or 0
        cats = s.scalar(select(func.count(ElibraryCategory.id))) or 0
        docs = s.scalar(select(func.count(ElibraryDocument.id))) or 0
        total = s.scalar(select(func.coalesce(func.sum(ElibraryDocument.size_bytes), 0))) or 0
        return jsonify({"subjects": subs, "categories": cats, "documents": docs,
                        "total_bytes": int(total)})


# ----- Subjects -----
@app.get("/api/elibrary/subjects")
@require()
def list_elib_subjects():
    with Session() as s:
        rows = s.scalars(select(ElibrarySubject).order_by(ElibrarySubject.name)).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/elibrary/subjects")
@require("admin", "super_admin")
def create_elib_subject():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "subject name is required"}), 400
    with Session() as s:
        sub = ElibrarySubject(name=name)
        s.add(sub); s.commit()
        return jsonify(sub.to_dict()), 201


@app.put("/api/elibrary/subjects/<int:sid>")
@require("admin", "super_admin")
def update_elib_subject(sid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        sub = s.get(ElibrarySubject, sid)
        if not sub:
            return jsonify({"error": "not found"}), 404
        if "name" in data:
            sub.name = (data["name"] or "").strip()
        s.commit()
        return jsonify(sub.to_dict())


@app.delete("/api/elibrary/subjects/<int:sid>")
@require("admin", "super_admin")
def delete_elib_subject(sid):
    with Session() as s:
        sub = s.get(ElibrarySubject, sid)
        if not sub:
            return jsonify({"error": "not found"}), 404
        # remove files on disk for documents under this subject
        docs = s.scalars(select(ElibraryDocument).where(ElibraryDocument.subject_id == sid)).all()
        for d in docs:
            _elib_delete_file(d.stored_name)
        s.delete(sub); s.commit()
        return jsonify({"ok": True})


# ----- Categories -----
@app.get("/api/elibrary/categories")
@require()
def list_elib_categories():
    with Session() as s:
        q = select(ElibraryCategory)
        sid = request.args.get("subject_id")
        if sid:
            q = q.where(ElibraryCategory.subject_id == int(sid))
        rows = s.scalars(q.order_by(ElibraryCategory.name)).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/elibrary/categories")
@require("admin", "super_admin")
def create_elib_category():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    sid = data.get("subject_id")
    if not name or not sid:
        return jsonify({"error": "subject_id and name are required"}), 400
    with Session() as s:
        if not s.get(ElibrarySubject, int(sid)):
            return jsonify({"error": "subject not found"}), 404
        cat = ElibraryCategory(subject_id=int(sid), name=name)
        s.add(cat); s.commit()
        return jsonify(cat.to_dict()), 201


@app.put("/api/elibrary/categories/<int:cid>")
@require("admin", "super_admin")
def update_elib_category(cid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        cat = s.get(ElibraryCategory, cid)
        if not cat:
            return jsonify({"error": "not found"}), 404
        if "name" in data:
            cat.name = (data["name"] or "").strip()
        s.commit()
        return jsonify(cat.to_dict())


@app.delete("/api/elibrary/categories/<int:cid>")
@require("admin", "super_admin")
def delete_elib_category(cid):
    with Session() as s:
        cat = s.get(ElibraryCategory, cid)
        if not cat:
            return jsonify({"error": "not found"}), 404
        docs = s.scalars(select(ElibraryDocument).where(ElibraryDocument.category_id == cid)).all()
        for d in docs:
            _elib_delete_file(d.stored_name)
        s.delete(cat); s.commit()
        return jsonify({"ok": True})


# ----- Documents -----
def _elib_delete_file(stored_name):
    try:
        if stored_name:
            os.remove(os.path.join(ELIB_UPLOAD_DIR, stored_name))
    except OSError:
        pass


@app.get("/api/elibrary/documents")
@require()
def list_elib_documents():
    with Session() as s:
        q = select(ElibraryDocument)
        if request.args.get("subject_id"):
            q = q.where(ElibraryDocument.subject_id == int(request.args["subject_id"]))
        if request.args.get("category_id"):
            q = q.where(ElibraryDocument.category_id == int(request.args["category_id"]))
        rows = s.scalars(q.order_by(ElibraryDocument.created_at.desc())).all()
        return jsonify([r.to_dict() for r in rows])


@app.post("/api/elibrary/documents")
@require("admin", "super_admin")
def upload_elib_document():
    # multipart/form-data: file + subject_id + category_id + title
    f = request.files.get("file")
    subject_id = request.form.get("subject_id")
    category_id = request.form.get("category_id")
    title = (request.form.get("title") or "").strip()
    if not f or not f.filename:
        return jsonify({"error": "a file is required"}), 400
    if not subject_id or not category_id:
        return jsonify({"error": "subject_id and category_id are required"}), 400
    if not _elib_ext_ok(f.filename):
        return jsonify({"error": "file type not allowed"}), 400
    orig = secure_filename(f.filename)
    ext = orig.rsplit(".", 1)[1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(ELIB_UPLOAD_DIR, stored)
    f.save(path)
    size = os.path.getsize(path)
    with Session() as s:
        d = ElibraryDocument(
            subject_id=int(subject_id), category_id=int(category_id),
            title=title or orig, stored_name=stored, original_name=orig,
            size_bytes=size, uploaded_by=request.user.get("email", "?"))
        s.add(d); s.commit()
        return jsonify(d.to_dict()), 201


@app.put("/api/elibrary/documents/<int:did>")
@require("admin", "super_admin")
def replace_elib_document(did):
    """Replace the file (and/or title) of an existing document."""
    with Session() as s:
        d = s.get(ElibraryDocument, did)
        if not d:
            return jsonify({"error": "not found"}), 404
        title = request.form.get("title")
        if title is not None:
            d.title = title.strip() or d.title
        f = request.files.get("file")
        if f and f.filename:
            if not _elib_ext_ok(f.filename):
                return jsonify({"error": "file type not allowed"}), 400
            _elib_delete_file(d.stored_name)
            orig = secure_filename(f.filename)
            ext = orig.rsplit(".", 1)[1].lower()
            stored = f"{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(ELIB_UPLOAD_DIR, stored))
            d.stored_name = stored
            d.original_name = orig
            d.size_bytes = os.path.getsize(os.path.join(ELIB_UPLOAD_DIR, stored))
            d.uploaded_by = request.user.get("email", "?")
        d.updated_at = dt.datetime.utcnow()
        s.commit()
        return jsonify(d.to_dict())


@app.delete("/api/elibrary/documents/<int:did>")
@require("admin", "super_admin")
def delete_elib_document(did):
    with Session() as s:
        d = s.get(ElibraryDocument, did)
        if not d:
            return jsonify({"error": "not found"}), 404
        _elib_delete_file(d.stored_name)
        s.delete(d); s.commit()
        return jsonify({"ok": True})


@app.get("/api/elibrary/documents/<int:did>/file")
@require()
def download_elib_document(did):
    with Session() as s:
        d = s.get(ElibraryDocument, did)
        if not d:
            return jsonify({"error": "not found"}), 404
        return send_from_directory(ELIB_UPLOAD_DIR, d.stored_name,
                                   as_attachment=True, download_name=d.original_name)


# ----- E-Library Users (super_admin only) -----
@app.get("/api/elibrary/users")
@require("super_admin")
def list_elib_users():
    with Session() as s:
        rows = s.scalars(select(ElibraryUser).order_by(ElibraryUser.id)).all()
        return jsonify([u.to_dict() for u in rows])


@app.post("/api/elibrary/users")
@require("super_admin")
def create_elib_user():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw = data.get("password") or ""
    role = data.get("role") or "user"
    if not email or not pw:
        return jsonify({"error": "email and password are required"}), 400
    if role not in ELIBRARY_ROLES:
        return jsonify({"error": "role must be super_admin, admin, or user"}), 400
    with Session() as s:
        if s.scalar(select(ElibraryUser).where(ElibraryUser.email == email)):
            return jsonify({"error": "a user with that email already exists"}), 409
        u = ElibraryUser(email=email, role=role,
                         pw_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        s.add(u); s.commit()
        return jsonify(u.to_dict()), 201


@app.put("/api/elibrary/users/<int:uid>")
@require("super_admin")
def update_elib_user(uid):
    data = request.get_json(force=True) or {}
    with Session() as s:
        u = s.get(ElibraryUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if "role" in data:
            if data["role"] not in ELIBRARY_ROLES:
                return jsonify({"error": "invalid role"}), 400
            if u.role == "super_admin" and data["role"] != "super_admin":
                supers = s.scalar(select(func.count(ElibraryUser.id)).where(ElibraryUser.role == "super_admin"))
                if supers <= 1:
                    return jsonify({"error": "cannot demote the last super admin"}), 400
            u.role = data["role"]
        if data.get("password"):
            u.pw_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        s.commit()
        return jsonify(u.to_dict())


@app.delete("/api/elibrary/users/<int:uid>")
@require("super_admin")
def delete_elib_user(uid):
    with Session() as s:
        u = s.get(ElibraryUser, uid)
        if not u:
            return jsonify({"error": "not found"}), 404
        if u.email == request.user["email"]:
            return jsonify({"error": "you cannot delete your own account"}), 400
        if u.role == "super_admin":
            supers = s.scalar(select(func.count(ElibraryUser.id)).where(ElibraryUser.role == "super_admin"))
            if supers <= 1:
                return jsonify({"error": "cannot delete the last super admin"}), 400
        s.delete(u); s.commit()
        return jsonify({"ok": True})


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large (max 25 MB)."}), 413


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
@app.get("/")
def landing():
    return send_from_directory(FRONTEND_DIR, "landing.html")


@app.get("/pmo")
def pmo():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/pmo/login")
def pmo_login():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.get("/people")
def people():
    return send_from_directory(FRONTEND_DIR, "people.html")


@app.get("/people/login")
def people_login():
    return send_from_directory(FRONTEND_DIR, "people-login.html")


@app.get("/quality")
def quality():
    return send_from_directory(FRONTEND_DIR, "quality.html")


@app.get("/quality/login")
def quality_login():
    return send_from_directory(FRONTEND_DIR, "quality-login.html")


@app.get("/elibrary")
def elibrary():
    return send_from_directory(FRONTEND_DIR, "elibrary.html")


@app.get("/elibrary/login")
def elibrary_login():
    return send_from_directory(FRONTEND_DIR, "elibrary-login.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    print(f"DB: {DB_URL}")
    print("Open http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
