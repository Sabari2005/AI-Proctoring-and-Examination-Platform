from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    organization: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SuperAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterOrganizationRequest(BaseModel):
    organization_name: str
    organization_type: str
    primary_email: EmailStr
    password: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EditUserRequest(BaseModel):
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class EditOrganizationRequest(BaseModel):
    organization_name: str | None = None
    organization_type: str | None = None
    primary_email: EmailStr | None = None
    is_active: bool | None = None


class AdminGeneralSettingsUpdateRequest(BaseModel):
    organization_name: str
    support_email: EmailStr