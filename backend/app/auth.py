"""Local research identity. No claim of production identity/security certification."""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select, update
from .db import (
    Session,
    User,
    AccessSession,
    LoginThrottle,
    DatasetGrant,
    Audit,
    Dataset,
)

router = APIRouter(prefix="/auth", tags=["Local identity"])
security = HTTPBearer(auto_error=False)
ROLES = {"admin", "researcher", "viewer"}
ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class Principal:
    id: str | None
    role: str
    username: str
    session_hash: str | None = None


def auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
):
    if not credentials:
        raise HTTPException(401, "Valid research access required")
    supplied = credentials.credentials
    bootstrap = os.getenv("DERMA_API_TOKEN", "")
    if len(bootstrap) >= 24 and hmac.compare_digest(
        supplied.encode(), bootstrap.encode()
    ):
        return Principal(None, "admin", "local-workspace-owner")
    digest = hashlib.sha256(supplied.encode()).hexdigest()
    with Session() as s:
        access = s.get(AccessSession, digest)
        user = s.get(User, access.user_id) if access else None
        if (
            not access
            or access.revoked
            or access.expires_at <= int(time.time())
            or not user
            or not user.active
            or user.role not in ROLES
        ):
            raise HTTPException(401, "Valid research access required")
        return Principal(user.id, user.role, user.username, digest)


Protected = Annotated[Principal, Depends(auth)]


def require_write(user):
    if user.role not in {"admin", "researcher"}:
        raise HTTPException(403, "Researcher or administrator access required")


def require_admin(user):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")


def can_read_dataset(user, item):
    if user.role == "admin" or user.id is not None and item.owner_id == user.id:
        return True
    if user.id is None:
        return False
    with Session() as s:
        return s.get(DatasetGrant, (item.id, user.id)) is not None


def can_read_run(user, item):
    if user.role == "admin":
        return True
    if user.id is None or item.owner_id != user.id:
        return False
    ids = [item.dataset_id] if item.dataset_id else []
    if item.kind == "relationship":
        ids.append(item.parameters.get("parent_dataset_id"))
    with Session() as s:
        for id in ids:
            dataset = s.get(Dataset, id) if id else None
            if (
                not dataset
                or dataset.owner_id != user.id
                and s.get(DatasetGrant, (dataset.id, user.id)) is None
            ):
                return False
    return True


def event(action, user_id, resource):
    with Session() as s:
        s.add(
            Audit(
                id=str(uuid4()), action=action, actor_id=user_id, resource_id=resource
            )
        )
        s.commit()


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: SecretStr = Field(min_length=1, max_length=1024)


class NewUser(Login):
    password: SecretStr = Field(min_length=12, max_length=1024)
    role: Literal["admin", "researcher", "viewer"] = "researcher"


class UserChange(BaseModel):
    active: bool


@router.post("/login")
def login(body: Login, request: Request):
    username = body.username.lower()
    now = int(time.time())
    peer = request.client.host if request.client else "unknown"
    key = hashlib.sha256((username + "|" + peer).encode()).hexdigest()
    with Session() as s:
        attempt = s.get(LoginThrottle, key)
        if attempt and attempt.blocked_until > now:
            raise HTTPException(
                429,
                "Too many failed sign-in attempts; retry after the cooldown",
                headers={"Retry-After": str(attempt.blocked_until - now)},
            )
        user = s.scalar(select(User).where(User.username == username))
        valid = verify_password(
            body.password.get_secret_value(), user.password_hash if user else DUMMY_HASH
        )
        if not valid or not user or not user.active:
            if not attempt:
                attempt = LoginThrottle(
                    key=key, failures=0, window_start=now, blocked_until=0
                )
                s.add(attempt)
            if now - attempt.window_start >= 900:
                attempt.failures = 0
                attempt.window_start = now
            attempt.failures += 1
            if attempt.failures >= 5:
                attempt.blocked_until = now + 900
            s.commit()
            event("login_failed", None, "local-identity")
            raise HTTPException(401, "Invalid username or password")
        if attempt:
            s.delete(attempt)
        hours = int(os.getenv("DERMA_SESSION_HOURS", "8"))
        if not 1 <= hours <= 168:
            raise HTTPException(
                503, "Session lifetime configuration must be 1–168 hours"
            )
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        expires = now + hours * 3600
        s.add(
            AccessSession(
                token_hash=digest, user_id=user.id, expires_at=expires, revoked=False
            )
        )
        s.commit()
        event("login_success", user.id, user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires,
            "user": {"id": user.id, "username": user.username, "role": user.role},
        }


@router.get("/me")
def me(user: Protected):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "bootstrap": user.session_hash is None,
    }


@router.post("/logout")
def logout(user: Protected):
    if user.session_hash:
        with Session() as s:
            access = s.get(AccessSession, user.session_hash)
            access.revoked = True
            s.commit()
    event("logout", user.id, user.id or "bootstrap")
    return {
        "session_revoked": user.session_hash is not None,
        "bootstrap_note": "Environment token must be rotated in server configuration"
        if user.session_hash is None
        else None,
    }


@router.post("/users", status_code=201)
def create_user(body: NewUser, user: Protected):
    require_admin(user)
    username = body.username.lower()
    with Session() as s:
        if s.scalar(select(User).where(User.username == username)):
            raise HTTPException(409, "Username unavailable")
        item = User(
            id=str(uuid4()),
            username=username,
            password_hash=hash_password(body.password.get_secret_value()),
            role=body.role,
            active=True,
        )
        s.add(item)
        from sqlalchemy.exc import IntegrityError

        try:
            s.commit()
        except IntegrityError as error:
            s.rollback()
            raise HTTPException(409, "Username unavailable") from error
    event("user_created", user.id, item.id)
    return {
        "id": item.id,
        "username": item.username,
        "role": item.role,
        "active": item.active,
    }


@router.get("/users")
def users(user: Protected):
    require_admin(user)
    with Session() as s:
        return [
            {"id": v.id, "username": v.username, "role": v.role, "active": v.active}
            for v in s.scalars(select(User).order_by(User.username))
        ]


@router.patch("/users/{id}")
def change_user(id: str, body: UserChange, user: Protected):
    require_admin(user)
    if id == user.id and not body.active:
        raise HTTPException(
            409, "Use a different administrator to disable your own account"
        )
    with Session() as s:
        item = s.get(User, id)
        if not item:
            raise HTTPException(404, "User not found")
        item.active = body.active
        if not body.active:
            s.execute(
                update(AccessSession)
                .where(AccessSession.user_id == id)
                .values(revoked=True)
            )
        s.commit()
    event("user_enabled" if body.active else "user_disabled", user.id, id)
    return {"id": id, "active": body.active}
