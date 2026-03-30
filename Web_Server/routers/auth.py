from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.hash import bcrypt
import os

from app.database import SessionLocal
from app.models import (
    User,
    Candidate,
    CandidateIdentity,
    Education,
    Skill,
    CandidateDocument,
    CandidateLink,
    Vendor,
    Notification,
    Drive,
    ExamSection,
    Question,
    CodingQuestion,
    TestCase,
    DriveRegistration,
    ExamLaunchCode,
    ExamAttempt,
    Answer,
    JitSectionSession,
    JitAnswerEvent,
    Offer,
    ExamResult,
    CodeSubmission,
)
from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    SuperAdminLoginRequest,
    RegisterOrganizationRequest,
    AdminLoginRequest,
    EditUserRequest,
    EditOrganizationRequest,
    AdminGeneralSettingsUpdateRequest,
)
from app.security import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()
SUPERADMIN_EMAIL = os.getenv("SUPERADMIN_EMAIL", "root@observe.platform")
SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "superadmin123")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == data.email).first()

    # If user already exists
    if existing_user:

        candidate = db.query(Candidate).filter(
            Candidate.user_id == existing_user.user_id
        ).first()

        # If candidate record doesn't exist create it
        if not candidate:
            candidate = Candidate(
                user_id=existing_user.user_id,
                full_name=data.full_name,
                onboarding_step=0
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)

        access_token = create_access_token({
            "sub": str(existing_user.user_id),
            "candidate_id": candidate.candidate_id,
            "role": existing_user.role
        })

        return {
            "message": "User already exists",
            "candidate_id": candidate.candidate_id,
            "onboarding_step": candidate.onboarding_step,
            "access_token": access_token,
            "token_type": "bearer"
        }

    # Create new user
    password_hash = bcrypt.hash(data.password)

    user = User(
        email=data.email,
        password_hash=password_hash,
        role="candidate"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create candidate profile
    candidate = Candidate(
        user_id=user.user_id,
        full_name=data.full_name,
        onboarding_step=0
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    access_token = create_access_token({
        "sub": str(user.user_id),
        "candidate_id": candidate.candidate_id,
        "role": user.role
    })

    return {
        "message": "User registered successfully",
        "candidate_id": candidate.candidate_id,
        "onboarding_step": 0,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login")
def login_user(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()
    password_hash = str(user.password_hash) if user else ""

    if not user or not bcrypt.verify(data.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    candidate = db.query(Candidate).filter(Candidate.user_id == user.user_id).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found"
        )

    access_token = create_access_token({
        "sub": str(user.user_id),
        "candidate_id": candidate.candidate_id,
        "role": user.role
    })

    return {
        "message": "Login successful",
        "candidate_id": candidate.candidate_id,
        "onboarding_step": candidate.onboarding_step,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = int(payload.get("sub", 0))
    candidate_id = int(payload.get("candidate_id", 0))

    user = db.query(User).filter(User.user_id == user_id).first()
    candidate = db.query(Candidate).filter(
        Candidate.candidate_id == candidate_id,
        Candidate.user_id == user_id
    ).first()

    if not user or not candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    return {
        "user_id": user.user_id,
        "candidate_id": candidate.candidate_id,
        "onboarding_step": candidate.onboarding_step,
        "role": user.role,
        "email": user.email
    }


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not bcrypt.verify(data.current_password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    if len(data.new_password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )

    setattr(user, "password_hash", bcrypt.hash(data.new_password.strip()))
    db.commit()

    return {"message": "Password changed successfully"}


def _get_superadmin_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    if payload.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )

    return payload


def _get_admin_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return payload


@router.post("/superadmin/login")
def superadmin_login(data: SuperAdminLoginRequest):
    if data.email.lower().strip() != SUPERADMIN_EMAIL.lower().strip() or data.password != SUPERADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid superadmin credentials"
        )

    access_token = create_access_token({
        "sub": data.email,
        "role": "superadmin"
    })

    return {
        "message": "Superadmin login successful",
        "email": data.email,
        "role": "superadmin",
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/superadmin/register-organization")
def register_organization(
    data: RegisterOrganizationRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    normalized_email = data.primary_email.lower().strip()

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary email already exists"
        )

    user = User(
        email=normalized_email,
        password_hash=bcrypt.hash(data.password),
        role="admin",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    vendor = Vendor(
        user_id=user.user_id,
        company_name=data.organization_name.strip(),
        organization_type=data.organization_type.strip(),
        organization_email=normalized_email,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    return {
        "message": "Organization registered successfully",
        "organization": {
            "vendor_id": vendor.vendor_id,
            "organization_name": vendor.company_name,
            "organization_type": vendor.organization_type,
            "primary_email": user.email,
            "admin_user_id": user.user_id,
            "status": "Active",
            "created_at": vendor.created_at,
        }
    }


@router.get("/superadmin/organizations")
def list_organizations(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    query = (
        db.query(Vendor, User)
        .join(User, Vendor.user_id == User.user_id)
        .order_by(Vendor.created_at.desc())
    )

    if not include_inactive:
        query = query.filter(User.is_active == True)

    orgs = query.all()

    return {
        "organizations": [
            {
                "vendor_id": vendor.vendor_id,
                "organization_name": vendor.company_name,
                "organization_type": vendor.organization_type,
                "primary_email": user.email,
                "status": "Active" if user.is_active else "Inactive",
                "created_at": vendor.created_at,
            }
            for vendor, user in orgs
        ]
    }


@router.get("/superadmin/users")
def list_users(
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    vendors = db.query(Vendor).all()
    candidates = db.query(Candidate).all()

    orgs_by_user_id: dict[int, list[str]] = {}
    for vendor in vendors:
        uid = int(vendor.user_id)
        orgs_by_user_id.setdefault(uid, []).append(str(vendor.company_name or ""))

    candidate_by_user_id: dict[int, str] = {}
    for candidate in candidates:
        candidate_by_user_id[int(candidate.user_id)] = str(candidate.full_name or "")

    user_rows = []
    for user in users:
        organization_names = [name for name in orgs_by_user_id.get(int(user.user_id), []) if name]
        candidate_name = candidate_by_user_id.get(int(user.user_id))

        user_rows.append(
            {
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at,
                "organization_name": organization_names[0] if organization_names else None,
                "organization_names": organization_names,
                "candidate_name": candidate_name,
            }
        )

    return {"users": user_rows}


@router.post("/admin/login")
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    normalized_email = data.email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()

    password_hash = str(user.password_hash) if user else ""
    user_role = str(getattr(user, "role", "")) if user else ""

    if (user is None) or (user_role != "admin") or (not bcrypt.verify(data.password, password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    if not bool(getattr(user, "is_active", True)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization account is deactivated"
        )

    vendor = db.query(Vendor).filter(Vendor.user_id == user.user_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found for this admin"
        )

    access_token = create_access_token({
        "sub": str(user.user_id),
        "vendor_id": vendor.vendor_id,
        "role": "admin"
    })

    return {
        "message": "Admin login successful",
        "admin_user_id": user.user_id,
        "vendor_id": vendor.vendor_id,
        "organization_name": vendor.company_name,
        "organization_type": vendor.organization_type,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/admin/me")
def get_admin_profile(
    db: Session = Depends(get_db),
    payload: dict = Depends(_get_admin_payload),
):
    user_id = int(payload.get("sub", 0))
    vendor_id = int(payload.get("vendor_id", 0))

    user = db.query(User).filter(User.user_id == user_id, User.role == "admin").first()
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id, Vendor.user_id == user_id).first()

    if not user or not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin profile not found"
        )

    return {
        "admin_user_id": user.user_id,
        "vendor_id": vendor.vendor_id,
        "organization_name": vendor.company_name,
        "organization_type": vendor.organization_type,
        "support_email": user.email,
        "is_active": bool(user.is_active),
    }


@router.patch("/admin/general-settings")
def update_admin_general_settings(
    data: AdminGeneralSettingsUpdateRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(_get_admin_payload),
):
    user_id = int(payload.get("sub", 0))
    vendor_id = int(payload.get("vendor_id", 0))

    user = db.query(User).filter(User.user_id == user_id, User.role == "admin").first()
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id, Vendor.user_id == user_id).first()

    if not user or not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin profile not found"
        )

    new_email = data.support_email.lower().strip()
    email_conflict = db.query(User).filter(User.email == new_email, User.user_id != user_id).first()
    if email_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Support email already in use"
        )

    setattr(vendor, "company_name", data.organization_name.strip())
    setattr(vendor, "organization_email", new_email)
    setattr(user, "email", new_email)

    db.commit()

    return {
        "message": "General settings updated",
        "organization_name": vendor.company_name,
        "support_email": user.email,
    }


def _create_notification(db: Session, user_id: int, title: str, body: str):
    notif = Notification(user_id=user_id, title=title, body=body)
    db.add(notif)


@router.patch("/superadmin/users/{user_id}")
def edit_user(
    user_id: int,
    data: EditUserRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(getattr(user, "role", "")) == "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit superadmin")

    changes = []

    if data.email is not None:
        new_email = data.email.lower().strip()
        conflict = db.query(User).filter(User.email == new_email, User.user_id != user_id).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        if str(getattr(user, "email", "")) != new_email:
            changes.append(f"email changed to {new_email}")
            setattr(user, "email", new_email)

    if data.role is not None:
        allowed_roles = {"candidate", "admin"}
        if data.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        if str(getattr(user, "role", "")) != data.role:
            changes.append(f"role changed to {data.role}")
            setattr(user, "role", data.role)

    if data.is_active is not None:
        if bool(user.is_active) != data.is_active:
            status_str = "activated" if data.is_active else "deactivated"
            changes.append(f"account {status_str}")
            setattr(user, "is_active", data.is_active)

    if changes:
        summary = "; ".join(changes)
        _create_notification(
            db,
            user_id,
            "Account Updated by Administrator",
            f"Your account has been updated: {summary}.",
        )
        db.commit()

    return {"message": "User updated", "user_id": user_id}


@router.delete("/superadmin/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(getattr(user, "role", "")) == "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete superadmin")

    linked_vendor = db.query(Vendor).filter(Vendor.user_id == user_id).first()
    if linked_vendor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is linked to an organization. Delete the organization instead."
        )

    try:
        candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()

        if candidate:
            candidate_id = int(candidate.candidate_id)

            registration_ids = [
                row[0]
                for row in db.query(DriveRegistration.registration_id)
                .filter(DriveRegistration.candidate_id == candidate_id)
                .all()
            ]

            attempt_ids = [
                row[0]
                for row in db.query(ExamAttempt.attempt_id)
                .filter(ExamAttempt.candidate_id == candidate_id)
                .all()
            ]

            jit_session_ids = []
            if attempt_ids:
                jit_session_ids = [
                    row[0]
                    for row in db.query(JitSectionSession.jit_section_session_id)
                    .filter(JitSectionSession.attempt_id.in_(attempt_ids))
                    .all()
                ]

            if jit_session_ids:
                db.query(JitAnswerEvent).filter(
                    JitAnswerEvent.jit_section_session_id.in_(jit_session_ids)
                ).delete(synchronize_session=False)

            if attempt_ids:
                db.query(JitAnswerEvent).filter(
                    JitAnswerEvent.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)
                db.query(JitSectionSession).filter(
                    JitSectionSession.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)
                db.query(Answer).filter(Answer.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)
                db.query(CodeSubmission).filter(
                    CodeSubmission.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)
                db.query(ExamResult).filter(ExamResult.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

            db.query(CodeSubmission).filter(CodeSubmission.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(ExamResult).filter(ExamResult.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(Offer).filter(Offer.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(ExamLaunchCode).filter(ExamLaunchCode.candidate_id == candidate_id).delete(synchronize_session=False)

            if registration_ids:
                db.query(ExamLaunchCode).filter(
                    ExamLaunchCode.registration_id.in_(registration_ids)
                ).delete(synchronize_session=False)

            db.query(DriveRegistration).filter(DriveRegistration.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(ExamAttempt).filter(ExamAttempt.candidate_id == candidate_id).delete(synchronize_session=False)

            db.query(CandidateIdentity).filter(CandidateIdentity.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(Education).filter(Education.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(Skill).filter(Skill.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).delete(synchronize_session=False)
            db.query(CandidateLink).filter(CandidateLink.candidate_id == candidate_id).delete(synchronize_session=False)
            db.delete(candidate)

        db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        db_err = str(getattr(exc, "orig", exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete user because related records exist: {db_err}"
        )

    return {"message": "User deleted", "user_id": user_id}


@router.patch("/superadmin/organizations/{vendor_id}")
def edit_organization(
    vendor_id: int,
    data: EditOrganizationRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    admin_user = db.query(User).filter(User.user_id == vendor.user_id).first()
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary admin user not found")

    changes = []

    if data.organization_name is not None:
        new_name = data.organization_name.strip()
        if not new_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization name cannot be empty")
        if str(getattr(vendor, "company_name", "")) != new_name:
            changes.append(f"organization name changed to '{new_name}'")
            setattr(vendor, "company_name", new_name)

    if data.organization_type is not None:
        new_type = data.organization_type.strip()
        if not new_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization type cannot be empty")
        if str(getattr(vendor, "organization_type", "")) != new_type:
            changes.append(f"organization type changed to '{new_type}'")
            setattr(vendor, "organization_type", new_type)

    if data.primary_email is not None:
        new_email = data.primary_email.lower().strip()
        conflict = db.query(User).filter(User.email == new_email, User.user_id != admin_user.user_id).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Primary email already in use")
        if str(getattr(admin_user, "email", "")) != new_email:
            changes.append(f"primary email changed to {new_email}")
            setattr(admin_user, "email", new_email)
            setattr(vendor, "organization_email", new_email)

    if data.is_active is not None:
        if bool(admin_user.is_active) != data.is_active:
            status_label = "activated" if data.is_active else "deactivated"
            changes.append(f"organization {status_label}")
            setattr(admin_user, "is_active", data.is_active)

    if changes:
        summary = "; ".join(changes)
        _create_notification(
            db,
            int(getattr(admin_user, "user_id", 0)),
            "Organization Updated by Administrator",
            f"Your organization details have been updated: {summary}.",
        )
        db.commit()

    return {"message": "Organization updated", "vendor_id": vendor_id}


@router.delete("/superadmin/organizations/{vendor_id}")
def delete_organization(
    vendor_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(_get_superadmin_payload),
):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    admin_user_id = int(vendor.user_id)
    admin_user = db.query(User).filter(User.user_id == admin_user_id).first()

    try:
        drive_ids = [row[0] for row in db.query(Drive.drive_id).filter(Drive.vendor_id == vendor_id).all()]

        if drive_ids:
            section_ids = [
                row[0]
                for row in db.query(ExamSection.section_id)
                .filter(ExamSection.drive_id.in_(drive_ids))
                .all()
            ]

            question_ids = [
                row[0]
                for row in db.query(Question.question_id)
                .filter(Question.drive_id.in_(drive_ids))
                .all()
            ]

            registration_ids = [
                row[0]
                for row in db.query(DriveRegistration.registration_id)
                .filter(DriveRegistration.drive_id.in_(drive_ids))
                .all()
            ]

            attempt_ids = [
                row[0]
                for row in db.query(ExamAttempt.attempt_id)
                .filter(ExamAttempt.drive_id.in_(drive_ids))
                .all()
            ]

            jit_session_ids = []
            if attempt_ids:
                jit_session_ids = [
                    row[0]
                    for row in db.query(JitSectionSession.jit_section_session_id)
                    .filter(JitSectionSession.attempt_id.in_(attempt_ids))
                    .all()
                ]

            coding_question_ids = []
            if question_ids:
                coding_question_ids = [
                    row[0]
                    for row in db.query(CodingQuestion.coding_question_id)
                    .filter(CodingQuestion.question_id.in_(question_ids))
                    .all()
                ]

            if jit_session_ids:
                db.query(JitAnswerEvent).filter(
                    JitAnswerEvent.jit_section_session_id.in_(jit_session_ids)
                ).delete(synchronize_session=False)

            if attempt_ids:
                db.query(JitAnswerEvent).filter(
                    JitAnswerEvent.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)

            if attempt_ids:
                db.query(JitSectionSession).filter(
                    JitSectionSession.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)

            if attempt_ids:
                db.query(Answer).filter(Answer.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

            if question_ids:
                db.query(Answer).filter(Answer.question_id.in_(question_ids)).delete(synchronize_session=False)

            if attempt_ids:
                db.query(CodeSubmission).filter(
                    CodeSubmission.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)

            if question_ids:
                db.query(CodeSubmission).filter(
                    CodeSubmission.question_id.in_(question_ids)
                ).delete(synchronize_session=False)

            if attempt_ids:
                db.query(ExamResult).filter(ExamResult.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

            db.query(ExamResult).filter(ExamResult.drive_id.in_(drive_ids)).delete(synchronize_session=False)
            db.query(Offer).filter(Offer.drive_id.in_(drive_ids)).delete(synchronize_session=False)
            db.query(ExamLaunchCode).filter(ExamLaunchCode.drive_id.in_(drive_ids)).delete(synchronize_session=False)

            if registration_ids:
                db.query(ExamLaunchCode).filter(
                    ExamLaunchCode.registration_id.in_(registration_ids)
                ).delete(synchronize_session=False)

            db.query(DriveRegistration).filter(DriveRegistration.drive_id.in_(drive_ids)).delete(synchronize_session=False)

            if coding_question_ids:
                db.query(TestCase).filter(TestCase.coding_question_id.in_(coding_question_ids)).delete(synchronize_session=False)
                db.query(CodingQuestion).filter(CodingQuestion.coding_question_id.in_(coding_question_ids)).delete(synchronize_session=False)

            if question_ids:
                db.query(Question).filter(Question.question_id.in_(question_ids)).delete(synchronize_session=False)

            db.query(ExamSection).filter(ExamSection.drive_id.in_(drive_ids)).delete(synchronize_session=False)

            if attempt_ids:
                db.query(ExamAttempt).filter(ExamAttempt.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

            db.query(Drive).filter(Drive.drive_id.in_(drive_ids)).delete(synchronize_session=False)

        db.delete(vendor)
        db.flush()

        remaining_vendor_count = db.query(Vendor).filter(Vendor.user_id == admin_user_id).count()

        if admin_user and remaining_vendor_count == 0:
            db.query(Notification).filter(
                Notification.user_id == admin_user_id
            ).delete(synchronize_session=False)
            db.delete(admin_user)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        db_err = str(getattr(exc, "orig", exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete organization because related records still exist: {db_err}"
        )

    return {"message": "Organization deleted", "vendor_id": vendor_id}


@router.get("/notifications/me")
def get_my_notifications(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "notifications": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "body": n.body,
                "is_read": bool(n.is_read),
                "created_at": n.created_at,
            }
            for n in notifications
        ]
    }


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == user_id,
    ).first()

    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    setattr(notif, "is_read", True)
    db.commit()
    return {"message": "Marked as read"}