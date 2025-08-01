from pydantic import BaseModel
from typing import Dict, Optional
import re

# class CountryOut(BaseModel):
#     id: int
#     name: str
#     official_name: Optional[str]
#     iso2: str
#     iso3: str
#     capital: Optional[str]
#     region: Optional[str]
#     flag_url: Optional[str]

#     class Config:
#         orm_mode = True
# class StateOut(BaseModel):
#     id: int
#     name: str

#     class Config:
#         orm_mode = True

from pydantic import BaseModel, EmailStr, Field, validator
from models.on_boarding_enums import UserTypeEnum
from utils.validators import (
    is_valid_password,
    is_valid_email,
    is_valid_phone,
)

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    emailid: EmailStr
    phonenumber: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8)
    user_type: UserTypeEnum
    role_id: int

    @validator("emailid")
    def validate_emailid(cls, value):
        if not is_valid_email(value):
            raise ValueError("Invalid email format.")
        return value

    @validator("phonenumber")
    def validate_phonenumber(cls, value):
        if not is_valid_phone(value):
            raise ValueError("Invalid phone number format.")
        return value

    @validator("password")
    def validate_password(cls, value):
        if not is_valid_password(value):
            raise ValueError(
                "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
            )
        return value

from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator
from typing import Optional, List
from models.on_boarding_enums import EntityTypeEnum, OwnershipEnum, ContactTypeEnum, XMLValidationOptionEnum

class AddressSchema(BaseModel):
    address_line_1: str
    address_line_2: Optional[str] = None
    address_line_3: Optional[str] = None
    city: str
    state: str
    zipcode: str
    country: str

    @validator("zipcode")
    def validate_zipcode(cls, v):
        import re
        if not re.match(r"^\d{5}(-\d{4})?$", v):
            raise ValueError("ZIP code must be 5 digits or ZIP+4 format (e.g., 12345 or 12345-6789).")
        return v


class ContactSchema(BaseModel):
    contact_type: ContactTypeEnum
    name: str
    email: EmailStr
    phone: Optional[str] = None

class CompanyCreateRequest(BaseModel):
    company_name: str
    company_url: Optional[str] = None
    entity_type: EntityTypeEnum
    entity_type_other: Optional[str] = None
    ownership: Optional[OwnershipEnum] = None
    ownership_other: Optional[str] = None
    tax_id: str
    naics_code: Optional[str] = None
    naics_description: Optional[str] = None

    mailing_address_same: bool
    physical_address: AddressSchema
    mailing_address: Optional[AddressSchema] = None
    contacts: List[ContactSchema]

    @validator("entity_type_other", always=True)
    def set_entity_type_other(cls, v, values):
        if values.get("entity_type") != EntityTypeEnum.other:
            return None
        return v

    @validator("tax_id")
    def validate_tax_id(cls, v):
        if not re.match(r"^\d{2}-\d{7}$|^\d{9}$", v.strip()):
            raise ValueError("Invalid Tax ID. Use format: NN-NNNNNNN or 9 digits.")
        return v.strip()

    @validator("naics_code")
    def validate_naics(cls, v):
        if v and (not v.isdigit() or len(v) != 6):
            raise ValueError("NAICS code must be a 6-digit number.")
        return v

    @validator("company_url", pre=True, always=True)
    def validate_company_url(cls, v):
        if not v or v.strip() == "":
            return None
        if not re.match(r"^https?://", v.strip()):
            raise ValueError("Invalid URL provided for company_url.")
        return v.strip()
    
class CompanyCreateResponse(BaseModel):
    company_id: int
    message: str

from pydantic import BaseModel, EmailStr, IPvAnyAddress, validator
from typing import List, Optional
from models.on_boarding_enums import RestrictionOptionEnum  # Replace with your actual enum path

class SecuritySettingsRequest(BaseModel):
    company_id: int
    access_control_preference: RestrictionOptionEnum
    otp_email_enabled: bool
    otp_phone_enabled: bool
    verification_email: EmailStr
    verification_phone: str
    authorized_ips: List[IPvAnyAddress]

    @validator("verification_phone")
    def validate_phone(cls, v):
        import re
        if not re.match(r"^\+?\d{10,15}$", v):
            raise ValueError("Phone number must be 10 to 15 digits with optional + prefix.")
        return v


class SFTPTestRequest(BaseModel):
    host: str
    port: int
    username: str
    auth_method: str  # 'password' or 'key'
    password: str = None  # required for password auth


class APITestRequest(BaseModel):
    url: HttpUrl
    auth_type: str  # "OAuth2", "API Key", "Other"
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_header_name: Optional[str] = "x-api-key"
    custom_headers: Optional[Dict[str, str]] = None
    ssl_enabled: Optional[bool] = True

from models.on_boarding_enums import FileTransmissionMethodEnum, AuthenticationMethodEnum, CredentialDeliveryMethodEnum, FileUploadFrequencyEnum, FileFormatEnum, APIAuthenticationTypeEnum


class SFTPSettingsRequest(BaseModel):
    host: str
    port: int
    username: str
    auth_method: AuthenticationMethodEnum
    credential_delivery_method: CredentialDeliveryMethodEnum


class APISettingsRequest(BaseModel):
    url: HttpUrl
    auth_type: APIAuthenticationTypeEnum
    ssl_enabled: bool


class IntegrationSaveRequest(BaseModel):
    company_id: int
    file_transmission_method: FileTransmissionMethodEnum
    sftp_details: Optional[SFTPSettingsRequest]
    api_details: Optional[APISettingsRequest]
    file_frequency: FileUploadFrequencyEnum
    file_format: FileFormatEnum


class XMLValidationPreferenceRequest(BaseModel):
    company_id: int
    xml_validation: XMLValidationOptionEnum


from pydantic import BaseModel, Field
from typing import Optional
from models.on_boarding_enums import (
    ApprovalTypeEnum,
    AutoDollarLimitExceedOptionEnum,
    FileFormatEnum,
    ControlTotalDuplicateFilenameEnum,
    ControlTotalDuplicateDataEnum,
    SingleApproverEscalationEnum,
    MultiPrimaryEscalationEnum,
    MultiSecondaryEscalationEnum
)

# ---- Sub-sections ----

class AutoApprovalConfig(BaseModel):
    max_dollar_limit: Optional[int] = Field(None, ge=0)
    enable_update_dollar_limit: bool
    exceed_limit_behavior: AutoDollarLimitExceedOptionEnum


class ControlTotalConfig(BaseModel):
    file_format: FileFormatEnum
    prefix: Optional[str] = None
    timezone: Optional[str] = None
    duplicate_file: ControlTotalDuplicateFilenameEnum
    duplicate_file_data: ControlTotalDuplicateDataEnum


class ManualSingleConfig(BaseModel):
    wait_time_before_moving_to_backup: int = Field(..., ge=0)
    wait_time_before_escalation: int = Field(..., ge=0)
    escalation_option: SingleApproverEscalationEnum


class ManualMultiConfig(BaseModel):
    wait_time_primary_approver: int = Field(..., ge=0)
    wait_time_primary_backup_approver: int = Field(..., ge=0)
    wait_time_secondary_approver: int = Field(..., ge=0)
    wait_time_secondary_backup_approver: int = Field(..., ge=0)

    escalation_option_for_primary_approver: MultiPrimaryEscalationEnum
    escalation_option_for_primary_backup_approver: MultiPrimaryEscalationEnum
    escalation_option_for_secondary_approver: MultiSecondaryEscalationEnum
    escalation_option_for_secondary_backup_approver: MultiSecondaryEscalationEnum


# ---- Main Request ----

class ApprovalSettingsRequest(BaseModel):
    company_id: int
    approval_type_config: ApprovalTypeEnum

    auto: Optional[AutoApprovalConfig] = None
    control_total: Optional[ControlTotalConfig] = None
    manual_single: Optional[ManualSingleConfig] = None
    manual_multi: Optional[ManualMultiConfig] = None

from pydantic import BaseModel

class OFACCertificationRequest(BaseModel):
    company_id: int
    is_certified: bool
