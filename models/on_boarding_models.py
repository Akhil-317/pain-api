from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import func

from models.on_boarding_enums import (
    AddressTypeEnum,
    ApprovalTypeEnum,
    ApproverStatusEnum,
    AutoDecisionStatusEnum,
    AutoDollarLimitExceedOptionEnum,
    ControlTotalDuplicateDataEnum,
    ControlTotalDuplicateFilenameEnum,
    EntityTypeEnum,
    FileFormatEnum,
    FileOperationEnum,
    FileUploadFrequencyEnum,
    ManualDecisionStatusEnum,
    MultiPrimaryEscalationEnum,
    MultiSecondaryEscalationEnum,
    NotificationPriorityEnum,
    NotificationTypeEnum,
    OwnershipEnum,
    OnboardingStatusEnum,
    FileTransmissionMethodEnum,
    ContactTypeEnum,
    AuthenticationMethodEnum,
    CredentialDeliveryMethodEnum,
    APIAuthenticationTypeEnum,
    RestrictionOptionEnum,
    RoleTypeEnum,
    SingleApproverEscalationEnum,
    XMLValidationOptionEnum,
    enum_column
)

from utils.validators import (
    is_valid_company_name,
    is_valid_ip,
    is_valid_url,
    is_valid_tax_id,
    is_valid_naics,
    is_valid_zipcode,
    is_valid_state,
    is_valid_country,
    is_valid_email,
    is_valid_phone,
    is_valid_hostname_or_ip,
    is_valid_port
)

Base = declarative_base(metadata=MetaData(schema="ip_main"))

# ---------- 🔁 Common Audit Fields ----------
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declared_attr

class AuditMixin:
    @declared_attr
    def created_by(cls):
        return Column(Integer, ForeignKey("ip_main.user.id"), nullable=True)

    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def updated_by(cls):
        return Column(Integer, ForeignKey("ip_main.user.id"), nullable=True)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ---------- 🏢 Company ----------
class Company(Base, AuditMixin):
    __tablename__ = "company"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    company_url = Column(String(512), nullable=True)
    tax_id_number = Column(String(20), nullable=False)

    entity_type = enum_column(EntityTypeEnum, "entity_type_enum", nullable=False)
    entity_type_other = Column(String(255), nullable=True)

    ownership = enum_column(OwnershipEnum, "ownership_enum", nullable=True)
    ownership_other = Column(String(255), nullable=True)

    naics_code = Column(String(6), nullable=True)
    naics_description = Column(String(1024), nullable=True)

    onboarding_status = enum_column(
        OnboardingStatusEnum,
        "onboarding_status_enum",
        nullable=False,
        default=OnboardingStatusEnum.to_be_onboarded
    )

    step_in_progress = Column(Integer, default=0)

    # --- Validators ---
    @validates("company_name")
    def validate_company_name(self, key, value):
        if not is_valid_company_name(value):
            raise ValueError("Company name must not be empty or whitespace.")
        return value

    @validates("company_url")
    def validate_company_url(self, key, value):
        if value and not is_valid_url(value):
            raise ValueError("Invalid URL provided for company_url.")
        return value

    @validates("tax_id_number")
    def validate_tax_id(self, key, value):
        if not is_valid_tax_id(value):
            raise ValueError("Invalid Tax ID format. Use 'NN-NNNNNNN' or 9-digit format.")
        return value

    @validates("naics_code")
    def validate_naics_code(self, key, value):
        if value and not is_valid_naics(value):
            raise ValueError("NAICS code must be a 6-digit number.")
        return value

    @validates("entity_type")
    def validate_entity_type(self, key, value):
        if not isinstance(value, EntityTypeEnum):
            try:
                value = EntityTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid entity_type: {value}")
        return value

    @validates("ownership")
    def validate_ownership(self, key, value):
        if value is not None and not isinstance(value, OwnershipEnum):
            try:
                value = OwnershipEnum(value)
            except ValueError:
                raise ValueError(f"Invalid ownership: {value}")
        return value

    @validates("onboarding_status")
    def validate_onboarding_status(self, key, value):
        if not isinstance(value, OnboardingStatusEnum):
            try:
                value = OnboardingStatusEnum(value)
            except ValueError:
                raise ValueError(f"Invalid onboarding_status: {value}")
        return value

# ---------- 🏠 Address ----------
class Address(Base, AuditMixin):
    __tablename__ = "address"
    __table_args__ = (
        UniqueConstraint("company_id", "address_type", name="uq_company_address_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255), nullable=True)
    address_line_3 = Column(String(255), nullable=True)

    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    zipcode = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)

    mailing_same = Column(Boolean, default=False)
    address_type = enum_column(AddressTypeEnum, "address_type_enum", nullable=False)

    company = relationship("Company", backref="addresses", foreign_keys=[company_id])

    @validates("city")
    def validate_city(self, key, value):
        if not value.strip():
            raise ValueError("City cannot be empty.")
        return value.strip()

    @validates("state")
    def validate_state(self, key, value):
        if not is_valid_state(value):
            raise ValueError("Invalid state value.")
        return value.strip()

    @validates("zipcode")
    def validate_zipcode(self, key, value):
        if not is_valid_zipcode(value):
            raise ValueError("Invalid ZIP code format.")
        return value.strip()

    @validates("country")
    def validate_country(self, key, value):
        if not is_valid_country(value):
            raise ValueError("Invalid country name.")
        return value.strip()

    @validates("address_type")
    def validate_address_type(self, key, value):
        if not isinstance(value, AddressTypeEnum):
            try:
                value = AddressTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid address_type: {value}")
        return value
    
    
# ---------- 📇 Contact ----------
class Contact(Base, AuditMixin):
    __tablename__ = "contact"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_type = enum_column(ContactTypeEnum, "contact_type_enum", nullable=False)

    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    company = relationship("Company", backref="contacts", foreign_keys=[company_id])

    @validates("name")
    def validate_name(self, key, value):
        if not value.strip():
            raise ValueError("Contact name cannot be empty.")
        return value.strip()

    @validates("email")
    def validate_email(self, key, value):
        if not is_valid_email(value):
            raise ValueError("Invalid email address format.")
        return value.strip()

    @validates("phone")
    def validate_phone(self, key, value):
        if value and not is_valid_phone(value):
            raise ValueError("Invalid phone number format.")
        return value.strip() if value else None

    @validates("contact_type")
    def validate_contact_type(self, key, value):
        if not isinstance(value, ContactTypeEnum):
            try:
                value = ContactTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid contact_type: {value}")
        return value

# ---------- 🔄 System Integration ----------
class SystemIntegration(Base, AuditMixin):
    __tablename__ = "system_integration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    transmission_method = enum_column(FileTransmissionMethodEnum, "transmission_method_enum", nullable=False)
    file_upload_frequency = enum_column(FileUploadFrequencyEnum, "file_upload_frequency_enum", nullable=False)
    file_format = enum_column(FileFormatEnum, "file_format_enum", nullable=False)

    company = relationship("Company", backref="system_integrations",foreign_keys=[company_id])

    @validates("transmission_method")
    def validate_transmission_method(self, key, value):
        if not isinstance(value, FileTransmissionMethodEnum):
            try:
                value = FileTransmissionMethodEnum(value)
            except ValueError:
                raise ValueError(f"Invalid transmission_method: {value}")
        return value

    @validates("file_upload_frequency")
    def validate_file_upload_frequency(self, key, value):
        if not isinstance(value, FileUploadFrequencyEnum):
            try:
                value = FileUploadFrequencyEnum(value)
            except ValueError:
                raise ValueError(f"Invalid file_upload_frequency: {value}")
        return value

    @validates("file_format")
    def validate_file_format(self, key, value):
        if not isinstance(value, FileFormatEnum):
            try:
                value = FileFormatEnum(value)
            except ValueError:
                raise ValueError(f"Invalid file_format: {value}")
        return value

# ---------- 🔐 SFTP Details ----------
class SFTPDetails(Base, AuditMixin):
    __tablename__ = "sftp_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    hostname_or_ip = Column(String(255), nullable=False)
    sftp_port = Column(Integer, default=22)
    username = Column(String(255), nullable=False)

    authentication_method = enum_column(AuthenticationMethodEnum, "auth_method_enum", nullable=False)
    ssh_key = Column(String(2048), nullable=True)

    credential_delivery_method = enum_column(CredentialDeliveryMethodEnum, "cred_delivery_enum", nullable=False)

    company = relationship("Company", backref="sftp_details",foreign_keys=[company_id])

    @validates("hostname_or_ip")
    def validate_hostname_or_ip(self, key, value):
        if not is_valid_hostname_or_ip(value):
            raise ValueError("Invalid hostname or IP address.")
        return value.strip()

    @validates("sftp_port")
    def validate_port(self, key, value):
        if not is_valid_port(value):
            raise ValueError("Invalid SFTP port. Must be between 1 and 65535.")
        return value

    @validates("username")
    def validate_username(self, key, value):
        if not value.strip():
            raise ValueError("Username cannot be empty.")
        return value.strip()

    @validates("authentication_method")
    def validate_auth_method(self, key, value):
        if not isinstance(value, AuthenticationMethodEnum):
            try:
                value = AuthenticationMethodEnum(value)
            except ValueError:
                raise ValueError(f"Invalid authentication method: {value}")
        return value

    @validates("ssh_key")
    def validate_ssh_key(self, key, value):
        if self.authentication_method == AuthenticationMethodEnum.ssh_key:
            if not value or not value.strip():
                raise ValueError("SSH key is required for SSH Key authentication.")
        return value.strip() if value else None

    @validates("credential_delivery_method")
    def validate_cred_method(self, key, value):
        if not isinstance(value, CredentialDeliveryMethodEnum):
            try:
                value = CredentialDeliveryMethodEnum(value)
            except ValueError:
                raise ValueError(f"Invalid credential delivery method: {value}")
        return value

# ---------- 🌐 API Details ----------
class APIDetails(Base, AuditMixin):
    __tablename__ = "api_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    api_endpoint_url = Column(String(512), nullable=False)
    authentication_type = enum_column(APIAuthenticationTypeEnum, "api_auth_type_enum", nullable=False)
    ssl_enabled = Column(Boolean, nullable=False, default=True)

    company = relationship("Company", backref="api_details",foreign_keys=[company_id])

    @validates("api_endpoint_url")
    def validate_url(self, key, value):
        if not is_valid_url(value):
            raise ValueError("Invalid API endpoint URL.")
        return value.strip()

    @validates("authentication_type")
    def validate_auth_type(self, key, value):
        if not isinstance(value, APIAuthenticationTypeEnum):
            try:
                value = APIAuthenticationTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid authentication type: {value}")
        return value

class SecuritySettings(Base, AuditMixin):
    __tablename__ = "security_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    restriction_configuration = enum_column(RestrictionOptionEnum, "restriction_option_enum", nullable=False)

    email_otp_enable = Column(Boolean, default=False)
    email_for_verification = Column(String(255), nullable=True)

    sms_otp_enable = Column(Boolean, default=False)
    mobile_number_otp_for_verification = Column(String(20), nullable=True)

    company = relationship("Company", backref="security_settings",foreign_keys=[company_id])

    # --- Validators ---
    @validates("restriction_configuration")
    def validate_restriction(self, key, value):
        if not isinstance(value, RestrictionOptionEnum):
            try:
                value = RestrictionOptionEnum(value)
            except ValueError:
                raise ValueError(f"Invalid restriction configuration: {value}")
        return value

    @validates("email_for_verification")
    def validate_email_verification(self, key, value):
        if self.email_otp_enable and not value:
            raise ValueError("Email for verification is required when email OTP is enabled.")
        if value and not is_valid_email(value):
            raise ValueError("Invalid email format for verification.")
        return value.strip() if value else None

    @validates("mobile_number_otp_for_verification")
    def validate_mobile_verification(self, key, value):
        if self.sms_otp_enable and not value:
            raise ValueError("Mobile number is required when SMS OTP is enabled.")
        if value and not is_valid_phone(value):
            raise ValueError("Invalid phone number format for OTP verification.")
        return value.strip() if value else None

class AuthorizedIP(Base, AuditMixin):
    __tablename__ = "authorized_ip"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    ip_address = Column(String(45), nullable=False)  # IPv6 max length is 45
    label = Column(String(255), nullable=True)

    company = relationship("Company", backref="authorized_ips",foreign_keys=[company_id])

    # --- Validators ---
    @validates("ip_address")
    def validate_ip(self, key, value):
        if not is_valid_ip(value):
            raise ValueError("Invalid IP address format.")
        return value.strip()

    @validates("label")
    def validate_label(self, key, value):
        return value.strip() if value else None

class ValidationPreferences(Base, AuditMixin):
    __tablename__ = "validation_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    validation_option = enum_column(XMLValidationOptionEnum, "xml_validation_option_enum", nullable=False)

    company = relationship("Company", backref="validation_preferences",foreign_keys=[company_id])

    # --- Validators ---
    @validates("validation_option")
    def validate_validation_option(self, key, value):
        if not isinstance(value, XMLValidationOptionEnum):
            try:
                value = XMLValidationOptionEnum(value)
            except ValueError:
                raise ValueError(f"Invalid validation option: {value}")
        return value
    
class ApprovalConfig(Base, AuditMixin):
    __tablename__ = "approval_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    approval_type_config = enum_column(ApprovalTypeEnum, "approval_type_enum", nullable=False)

    company = relationship("Company", backref="approval_config",foreign_keys=[company_id])

    # --- Validators ---
    @validates("approval_type_config")
    def validate_approval_type_config(self, key, value):
        if not isinstance(value, ApprovalTypeEnum):
            try:
                value = ApprovalTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid approval type: {value}")
        return value

class AutoApprovalSettings(Base, AuditMixin):
    __tablename__ = "auto_approval_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    max_auto_approval_amount = Column(Integer, nullable=True)
    enable_update_dollar_limit = Column(Boolean, default=False)

    exceed_limit_behavior = enum_column(
        AutoDollarLimitExceedOptionEnum,
        "auto_dollar_exceed_enum",
        nullable=False
    )

    company = relationship("Company", backref="auto_approval_settings",foreign_keys=[company_id])

    # --- Validators ---
    @validates("max_auto_approval_amount")
    def validate_amount(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Maximum auto approval amount must be non-negative.")
        return value

    @validates("exceed_limit_behavior")
    def validate_behavior(self, key, value):
        if not isinstance(value, AutoDollarLimitExceedOptionEnum):
            try:
                value = AutoDollarLimitExceedOptionEnum(value)
            except ValueError:
                raise ValueError(f"Invalid exceed limit behavior: {value}")
        return value

class ControlTotalApprovalSettings(Base, AuditMixin):
    __tablename__ = "control_total_approval_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    file_format = enum_column(FileFormatEnum, "control_file_format_enum", nullable=False)
    prefix = Column(String(255), nullable=True)
    timezone = Column(String(100), nullable=True)

    duplicate_file = enum_column(ControlTotalDuplicateFilenameEnum, "control_duplicate_file_enum", nullable=False)
    duplicate_file_data = enum_column(ControlTotalDuplicateDataEnum, "control_duplicate_data_enum", nullable=False)

    company = relationship("Company", backref="control_total_approval_settings",foreign_keys=[company_id])

    # --- Validators ---
    @validates("file_format")
    def validate_file_format(self, key, value):
        if not isinstance(value, FileFormatEnum):
            try:
                value = FileFormatEnum(value)
            except ValueError:
                raise ValueError(f"Invalid file format: {value}")
        return value

    @validates("prefix")
    def validate_prefix(self, key, value):
        return value.strip() if value else None

    @validates("timezone")
    def validate_timezone(self, key, value):
        return value.strip() if value else None

    @validates("duplicate_file")
    def validate_duplicate_file(self, key, value):
        if not isinstance(value, ControlTotalDuplicateFilenameEnum):
            try:
                value = ControlTotalDuplicateFilenameEnum(value)
            except ValueError:
                raise ValueError(f"Invalid duplicate file handling option: {value}")
        return value

    @validates("duplicate_file_data")
    def validate_duplicate_data(self, key, value):
        if not isinstance(value, ControlTotalDuplicateDataEnum):
            try:
                value = ControlTotalDuplicateDataEnum(value)
            except ValueError:
                raise ValueError(f"Invalid duplicate file data handling option: {value}")
        return value

class ManualApprovalSingleSettings(Base, AuditMixin):
    __tablename__ = "manual_approval_single_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    wait_time_before_moving_to_backup = Column(Integer, nullable=False)  # in minutes
    wait_time_before_escalation = Column(Integer, nullable=False)        # in minutes

    escalation_option = enum_column(SingleApproverEscalationEnum, "single_escalation_enum", nullable=False)

    company = relationship("Company", backref="manual_approval_single_settings",foreign_keys=[company_id])

    # --- Validators ---
    @validates("wait_time_before_moving_to_backup", "wait_time_before_escalation")
    def validate_wait_times(self, key, value):
        if value is None or value < 0:
            raise ValueError(f"{key} must be a non-negative number of minutes.")
        return value

    @validates("escalation_option")
    def validate_escalation_option(self, key, value):
        if not isinstance(value, SingleApproverEscalationEnum):
            try:
                value = SingleApproverEscalationEnum(value)
            except ValueError:
                raise ValueError(f"Invalid escalation option: {value}")
        return value


class ManualApprovalMultiSettings(Base, AuditMixin):
    __tablename__ = "manual_approval_multi_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    wait_time_primary_approver = Column(Integer, nullable=False)
    wait_time_primary_backup_approver = Column(Integer, nullable=False)
    wait_time_secondary_approver = Column(Integer, nullable=False)
    wait_time_secondary_backup_approver = Column(Integer, nullable=False)

    escalation_option_for_primary_approver = enum_column(MultiPrimaryEscalationEnum, "multi_primary_approver_escalation", nullable=False)
    escalation_option_for_primary_backup_approver = enum_column(MultiPrimaryEscalationEnum, "multi_primary_backup_escalation", nullable=False)

    escalation_option_for_secondary_approver = enum_column(MultiSecondaryEscalationEnum, "multi_secondary_approver_escalation", nullable=False)
    escalation_option_for_secondary_backup_approver = enum_column(MultiSecondaryEscalationEnum, "multi_secondary_backup_escalation", nullable=False)

    company = relationship("Company", backref="manual_approval_multi_settings",foreign_keys=[company_id])

    # --- Validators ---
    @validates(
        "wait_time_primary_approver",
        "wait_time_primary_backup_approver",
        "wait_time_secondary_approver",
        "wait_time_secondary_backup_approver"
    )
    def validate_wait_times(self, key, value):
        if value is None or value < 0:
            raise ValueError(f"{key} must be a non-negative number of minutes.")
        return value

    @validates(
        "escalation_option_for_primary_approver",
        "escalation_option_for_primary_backup_approver"
    )
    def validate_primary_escalation(self, key, value):
        if not isinstance(value, MultiPrimaryEscalationEnum):
            try:
                value = MultiPrimaryEscalationEnum(value)
            except ValueError:
                raise ValueError(f"Invalid primary escalation option for {key}: {value}")
        return value

    @validates(
        "escalation_option_for_secondary_approver",
        "escalation_option_for_secondary_backup_approver"
    )
    def validate_secondary_escalation(self, key, value):
        if not isinstance(value, MultiSecondaryEscalationEnum):
            try:
                value = MultiSecondaryEscalationEnum(value)
            except ValueError:
                raise ValueError(f"Invalid secondary escalation option for {key}: {value}")
        return value

class OFACCertification(Base, AuditMixin):
    __tablename__ = "ofac_certification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), unique=True, nullable=False)

    is_certified = Column(Boolean, nullable=False, default=False)

    company = relationship("Company", backref="ofac_certification",foreign_keys=[company_id])

    # --- Validators ---
    @validates("is_certified")
    def validate_is_certified(self, key, value):
        if not isinstance(value, bool):
            raise ValueError("is_certified must be a boolean.")
        return value

class Role(Base, AuditMixin):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(100), nullable=False, unique=True)
    role_description = Column(String(512), nullable=True)

    role_type = enum_column(RoleTypeEnum, "role_type_enum", nullable=False)

    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    priority_level = Column(Integer, nullable=True)

    # --- Validators ---
    @validates("role_name")
    def validate_role_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("Role name cannot be empty.")
        return value.strip()

    @validates("priority_level")
    def validate_priority(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Priority level must be a non-negative integer.")
        return value

    @validates("role_type")
    def validate_role_type(self, key, value):
        if not isinstance(value, RoleTypeEnum):
            try:
                value = RoleTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid role_type: {value}")
        return value
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models.on_boarding_enums import UserTypeEnum, enum_column
from utils.validators import is_valid_email, is_valid_phone

class User(Base, AuditMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)

    username = Column(String(100), nullable=False, unique=True)
    emailid = Column(String(255), nullable=False, unique=True)
    phonenumber = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    sms_mfa = Column(Boolean, default=False)
    email_mfa = Column(Boolean, default=False)

    user_type = enum_column(UserTypeEnum, "user_type_enum", nullable=False)
    role_id = Column(Integer, ForeignKey("ip_main.role.id"), nullable=False)

    profile_picture = Column(String(1024), nullable=True)
    is_active = Column(Boolean, default=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)

    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)

    role = relationship("Role", backref="users", foreign_keys=[role_id])
    
    # One-to-one relationship to Address (if each user has one address)
    address_id = Column(Integer, ForeignKey("ip_main.address.id"), nullable=True)
    address = relationship("Address", backref="user", uselist=False)

    # --- Validators ---
    @validates("emailid")
    def validate_email(self, key, value):
        if not is_valid_email(value):
            raise ValueError("Invalid email address format.")
        return value.strip()

    @validates("phonenumber")
    def validate_phone(self, key, value):
        if value and not is_valid_phone(value):
            raise ValueError("Invalid phone number format.")
        return value.strip() if value else None

    @validates("username")
    def validate_username(self, key, value):
        if not value.strip():
            raise ValueError("Username cannot be empty.")
        return value.strip()

    @validates("user_type")
    def validate_user_type(self, key, value):
        if not isinstance(value, UserTypeEnum):
            try:
                value = UserTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid user_type: {value}")
        return value


from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models.on_boarding_enums import enum_column
from utils.validators import is_valid_url  # optional if using link_url



class Notification(Base, AuditMixin):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), nullable=False)

    notification_title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    type = enum_column(NotificationTypeEnum, "notification_type_enum", nullable=False)
    priority = enum_column(NotificationPriorityEnum, "notification_priority_enum", nullable=True)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications",foreign_keys=[user_id])

    # --- Validators ---
    @validates("notification_title")
    def validate_title(self, key, value):
        if not value or not value.strip():
            raise ValueError("Notification title cannot be empty.")
        return value.strip()

    @validates("message")
    def validate_message(self, key, value):
        if not value or not value.strip():
            raise ValueError("Notification message cannot be empty.")
        return value.strip()

    @validates("type")
    def validate_type(self, key, value):
        if not isinstance(value, NotificationTypeEnum):
            try:
                value = NotificationTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid notification type: {value}")
        return value

    @validates("priority")
    def validate_priority(self, key, value):
        if value is not None and not isinstance(value, NotificationPriorityEnum):
            try:
                value = NotificationPriorityEnum(value)
            except ValueError:
                raise ValueError(f"Invalid priority: {value}")
        return value

from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import validates

class Permission(Base, AuditMixin):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # e.g., "Reports", "Users"
    is_active = Column(Boolean, default=True)

    # --- Validators ---
    @validates("name")
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("Permission name cannot be empty.")
        return value.strip()

    @validates("category")
    def validate_category(self, key, value):
        return value.strip() if value else value
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class RolePermission(Base, AuditMixin):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    role_id = Column(Integer, ForeignKey("ip_main.role.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("ip_main.permission.id"), nullable=False)

    role = relationship("Role", backref="role_permissions",foreign_keys=[role_id])
    permission = relationship("Permission", backref="permission_roles",foreign_keys=[permission_id])
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

class AuditLog(Base, AuditMixin):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Optional Validation ---
    @staticmethod
    def validate_field(value, field_name):
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty.")
        return value.strip()

    @validates("audit_title")
    def validate_title(self, key, value):
        return self.validate_field(value, "Audit title")

    @validates("message")
    def validate_message(self, key, value):
        return self.validate_field(value, "Audit message")


from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, DateTime
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models.on_boarding_enums import FileStatusEnum, enum_column

class ClientFile(Base, AuditMixin):
    __tablename__ = "client_file"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), nullable=False)

    filename = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_format = Column(String(20), nullable=False)  # e.g. ".csv", ".xml"
    file_size = Column(Float, nullable=False)         # in MB or bytes, depending on convention
    file_location = Column(String(1024), nullable=False)

    file_status = enum_column(FileStatusEnum, "file_status_enum", nullable=False, default=FileStatusEnum.uploaded)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", backref="client_files",foreign_keys=[company_id])
    user = relationship("User", backref="uploaded_files",foreign_keys=[user_id])

    # --- Validators ---
    @validates("filename")
    def validate_filename(self, key, value):
        if not value.strip():
            raise ValueError("Filename cannot be empty.")
        return value.strip()

    @validates("file_location")
    def validate_file_location(self, key, value):
        if not value.strip():
            raise ValueError("File location cannot be empty.")
        return value.strip()

    @validates("file_format")
    def validate_file_format(self, key, value):
        if not value.strip():
            raise ValueError("File format cannot be empty.")
        return value.strip()

    @validates("file_status")
    def validate_file_status(self, key, value):
        if not isinstance(value, FileStatusEnum):
            try:
                value = FileStatusEnum(value)
            except ValueError:
                raise ValueError(f"Invalid file status: {value}")
        return value

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

class FileValidation(Base, AuditMixin):
    __tablename__ = "file_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("ip_main.client_file.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    validated_against_file_xsd = Column(String(255), nullable=True)
    is_valid = Column(Boolean, nullable=False)

    validated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("ClientFile", backref="validations", foreign_keys=[file_id])
    user = relationship("User", backref="file_validations", foreign_keys=[user_id])
    company = relationship("Company", backref="file_validations", foreign_keys=[company_id])


    # Validators
    @validates("validated_against_file_xsd")
    def validate_xsd(self, key, value):
        return value.strip() if value else value

from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship, validates

class FileError(Base, AuditMixin):
    __tablename__ = "file_error"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_validation_id = Column(Integer, ForeignKey("ip_main.file_validation.id"), nullable=False)

    error_type = Column(String(100), nullable=False)        # e.g. "Schema", "Data", "Business Rule"
    error_title = Column(String(255), nullable=False)       # Short summary
    error_message = Column(Text, nullable=False)            # Detailed message

    line_number = Column(Integer, nullable=True)            # Line number in the file (if applicable)
    field_name = Column(String(255), nullable=True)         # Field/column where error occurred
    severity = Column(String(50), nullable=True)            # "info", "warning", "critical"

    # Relationships
    file_validation = relationship("FileValidation", backref="errors", foreign_keys=[file_validation_id])


    # Validators
    @validates("error_type", "error_title", "error_message")
    def validate_required_fields(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').capitalize()} cannot be empty.")
        return value.strip()

    @validates("severity")
    def validate_severity(self, key, value):
        allowed = {"info", "warning", "critical"}
        if value and value.lower() not in allowed:
            raise ValueError("Severity must be one of: info, warning, critical.")
        return value.lower() if value else None

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from enum import Enum

class FileDecisionAuto(Base, AuditMixin):
    __tablename__ = "file_decision_auto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    file_id = Column(Integer, ForeignKey("ip_main.client_file.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    decision = Column(SQLEnum(AutoDecisionStatusEnum, name="auto_decision_status_enum"), nullable=False)
    decision_made_at = Column(DateTime(timezone=True), server_default=func.now())

    comments = Column(Text, nullable=True)

    # Relationships
    file = relationship("ClientFile", backref="auto_decisions", foreign_keys=[file_id])
    company = relationship("Company", backref="auto_decisions", foreign_keys=[company_id])

    

    # Validators
    @validates("decision")
    def validate_decision(self, key, value):
        if not isinstance(value, AutoDecisionStatusEnum):
            try:
                value = AutoDecisionStatusEnum(value)
            except ValueError:
                raise ValueError(f"Invalid decision status: {value}")
        return value

    @validates("comments")
    def validate_comments(self, key, value):
        return value.strip() if value else value


from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, DateTime, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from enum import Enum

class FileApproverAction(Base, AuditMixin):
    __tablename__ = "file_approver_action"

    id = Column(Integer, primary_key=True, autoincrement=True)

    file_decision_manual_id = Column(Integer, ForeignKey("ip_main.file_decision_manual.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), nullable=False)

    level = Column(String(50), nullable=False)  # e.g., primary, backup, secondary, etc.
    status = Column(SQLEnum(ApproverStatusEnum, name="approver_status_enum"), default=ApproverStatusEnum.pending, nullable=False)

    responded_at = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)

    # Relationships
    file_decision_manual = relationship("FileDecisionManual", backref="approver_actions", foreign_keys=[file_decision_manual_id])
    user = relationship("User", backref="approval_actions", foreign_keys=[user_id])

    

    # Validators
    @validates("status")
    def validate_status(self, key, value):
        if not isinstance(value, ApproverStatusEnum):
            try:
                value = ApproverStatusEnum(value)
            except ValueError:
                raise ValueError(f"Invalid approver status: {value}")
        return value

    @validates("level")
    def validate_level(self, key, value):
        if not value or not value.strip():
            raise ValueError("Level is required.")
        return value.strip()

from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from models.on_boarding_enums import ApprovalTypeEnum


class FileDecisionManual(Base, AuditMixin):
    __tablename__ = "file_decision_manual"

    id = Column(Integer, primary_key=True, autoincrement=True)

    file_id = Column(Integer, ForeignKey("ip_main.client_file.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    approval_type = Column(SQLEnum(ApprovalTypeEnum, name="approval_type_enum"), nullable=False)
    status = Column(SQLEnum(ManualDecisionStatusEnum, name="manual_decision_status_enum"), default=ManualDecisionStatusEnum.pending, nullable=False)

    current_level = Column(String(50), nullable=True)  # e.g., primary, backup, secondary, etc.

    decision_at = Column(DateTime(timezone=True), nullable=True)
    final_decision_by = Column(Integer, ForeignKey("ip_main.user.id"), nullable=True)
    final_decision_comments = Column(Text, nullable=True)

    # Relationships
    file = relationship("ClientFile", backref="manual_decision", foreign_keys=[file_id])
    company = relationship("Company", backref="manual_decisions", foreign_keys=[company_id])
    final_decision_user = relationship("User", backref="manual_decision_made", foreign_keys=[final_decision_by])

    
    # Validators
    @validates("approval_type")
    def validate_approval_type(self, key, value):
        if not isinstance(value, ApprovalTypeEnum):
            try:
                value = ApprovalTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid approval_type: {value}")
        return value

    @validates("status")
    def validate_status(self, key, value):
        if not isinstance(value, ManualDecisionStatusEnum):
            try:
                value = ManualDecisionStatusEnum(value)
            except ValueError:
                raise ValueError(f"Invalid decision status: {value}")
        return value


from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

class FileAudit(Base, AuditMixin):
    __tablename__ = "file_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("ip_main.client_file.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    operation = Column(SQLEnum(FileOperationEnum, name="file_operation_enum"), nullable=False)
    message = Column(Text, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("ClientFile", backref="file_audits", foreign_keys=[file_id])
    user = relationship("User", backref="file_audits", foreign_keys=[user_id])
    company = relationship("Company", backref="file_audits", foreign_keys=[company_id])


    # Validator
    @validates("operation")
    def validate_operation(self, key, value):
        if not isinstance(value, FileOperationEnum):
            try:
                value = FileOperationEnum(value)
            except ValueError:
                raise ValueError(f"Invalid file operation: {value}")
        return value

class SalesUser(Base, AuditMixin):
    __tablename__ = "sales_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), unique=True, nullable=False)
    
    feedback = Column(Text, nullable=True)
    assigned_region = Column(String(100), nullable=True)

    user = relationship("User", backref="sales_user", foreign_keys=[user_id])


class ClientUser(Base, AuditMixin):
    __tablename__ = "client_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    department = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    terms_agreed = Column(Boolean, default=False)

    user = relationship("User", backref="client_user", foreign_keys=[user_id])
    company = relationship("Company", backref="client_users", foreign_keys=[company_id])


from sqlalchemy import UniqueConstraint
from models.on_boarding_enums import ApproverTypeEnum, enum_column

class ApproverUser(Base, AuditMixin):
    __tablename__ = "approver_user"
    __table_args__ = (
        UniqueConstraint("company_id", "approver_type", name="uq_company_approver_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("ip_main.user.id"), unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("ip_main.company.id"), nullable=False)

    approver_type = enum_column(ApproverTypeEnum, "approver_type_enum", nullable=False)

    user = relationship("User", backref="approver_user", foreign_keys=[user_id])
    company = relationship("Company", backref="approver_users", foreign_keys=[company_id])


    @validates("approver_type")
    def validate_approver_type(self, key, value):
        if not isinstance(value, ApproverTypeEnum):
            try:
                value = ApproverTypeEnum(value)
            except ValueError:
                raise ValueError(f"Invalid approver_type: {value}")
        return value


# class Country(Base):
#     __tablename__ = "countries"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, nullable=False)
#     official_name = Column(String)
#     iso2 = Column(String(2), nullable=False, unique=True)
#     iso3 = Column(String(3), nullable=False, unique=True)
#     capital = Column(String)
#     region = Column(String)
#     flag_url = Column(String)
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# class State(Base):
#     __tablename__ = "states"
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)
#     country_id = Column(Integer, ForeignKey("countries.id", ondelete="CASCADE"))
#     country = relationship("Country", back_populates="states")


