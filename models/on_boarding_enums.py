from enum import Enum
from sqlalchemy import Column, Enum as SQLEnum

def enum_column(enum_cls, name, nullable=False, default=None, schema="ip_main"):
    return Column(
        SQLEnum(
            enum_cls,
            values_callable=lambda obj: [e.value for e in obj],
            name=f"{schema}_{name}",
            schema=schema,  # <-- attach schema here
            native_enum=True,
            create_type=True
        ),
        nullable=nullable,
        default=default
    )


class EntityTypeEnum(str, Enum):
    limited_liability_company = "Limited Liability Company (LLC)"
    c_corporation = "C Corporation"
    s_corporation = "S Corporation"
    non_profit_organization = "Non-profit Organization"
    trust_estate = "Trust/Estate"
    government_entity = "Government Entity"
    foreign_entity = "Foreign Entity (Non-U.S.)"
    other = "Other"
    def __str__(self): return self.value

class OwnershipEnum(str, Enum):
    privately_owned = "Privately Owned"
    publicly_traded = "Publicly Traded"
    government_owned = "Government-Owned"
    non_profit = "Non-Profit"
    woman_owned = "Woman-Owned"
    minority_owned = "Minority-Owned"
    veteran_owned = "Veteran-Owned"
    joint_venture = "Joint Venture"
    family_owned = "Family-Owned"
    other = "Other"
    def __str__(self): return self.value

class FileTransmissionMethodEnum(str, Enum):
    sftp = "SFTP"
    api = "API"
    manual_upload = "Manual Upload"
    def __str__(self): return self.value

class FileUploadFrequencyEnum(str, Enum):
    daily = "Daily"
    weekly = "Weekly"
    bi_weekly = "Bi-weekly"
    monthly = "Monthly"
    on_demand = "On-Demand"
    as_needed = "As Needed"
    def __str__(self): return self.value

class FileFormatEnum(str, Enum):
    xml = "XML"
    csv = "CSV"
    excel_xlsx = "Excel (.xlsx)"
    json = "JSON"
    fixed_width_text = "Fixed Width Text File"
    other = "Other"
    def __str__(self): return self.value

class RestrictionOptionEnum(str, Enum):
    restrict_by_region = "Restrict by country or region"
    allow_known_devices = "Allow only managed/known devices"
    no_restrictions = "No Restrictions"
    def __str__(self): return self.value

class XMLValidationOptionEnum(str, Enum):
    standard = "Standard"
    custom_xsd = "Custom XSD"
    def __str__(self): return self.value

class ApprovalTypeEnum(str, Enum):
    auto = "Auto"
    control_total = "Control Total"
    manual_single = "Manual-Single"
    manual_multi = "Manual-Multi"
    def __str__(self): return self.value

class AutoDollarLimitExceedOptionEnum(str, Enum):
    cancel_transaction = "Cancel the transaction"
    notify_admin = "Notify the admin"
    def __str__(self): return self.value

class ControlTotalFileFormatEnum(str, Enum):
    xml = "XML"
    csv = "CSV"
    json = "JSON"
    def __str__(self): return self.value

class ControlTotalDuplicateFilenameEnum(str, Enum):
    reject = "Reject the duplicate"
    overwrite = "Overwrite the previous"
    flag_reprocessing = "Flag the reprocessing attempt"
    def __str__(self): return self.value

class ControlTotalDuplicateDataEnum(str, Enum):
    reject = "Reject the duplicate"
    overwrite = "Overwrite the previous"
    def __str__(self): return self.value

class SingleApproverEscalationEnum(str, Enum):
    reject_automatically = "Reject the file automatically"
    resend_once = "Resend approval request (once)"
    hold = "Put the file on hold"
    escalate_to_admin = "Escalate to Admin for manual review"
    def __str__(self): return self.value

class MultiPrimaryEscalationEnum(str, Enum):
    reject = "Reject the file"
    escalate_to_admin = "Escalate to the Admin"
    auto_approve = "Auto-approve the file"
    hold = "Put the file on hold"
    def __str__(self): return self.value

class MultiSecondaryEscalationEnum(str, Enum):
    escalate_to_admin = "Auto-Escalate to Admin for Review"
    auto_reject = "Auto-Reject the File"
    final_reminder_hold = "Send Final Reminder and Keep File On Hold (Stale File)"
    def __str__(self): return self.value


class OnboardingStatusEnum(str, Enum):
    to_be_onboarded = "to-be-onboarded"
    onboarding_in_progress = "on-boarding-in-progress"
    onboarding_done = "on-boarding-done"
    def __str__(self): return self.value

class AddressTypeEnum(str, Enum):
    mailing = "mailing"
    physical = "physical"

    def __str__(self):
        return self.value

class ContactTypeEnum(str, Enum):
    admin = "Admin"
    master_admin = "Master Admin"
    technical_contact = "Technical Contact"
    billing_finance_contact = "Billing/Finance Contact"
    compliance_contact = "Compliance Contact"
    legal_contact = "Legal Contact"

    def __str__(self): return self.value


class AuthenticationMethodEnum(str, Enum):
    password = "Password"
    ssh_key = "SSH Key"
    def __str__(self): return self.value

class CredentialDeliveryMethodEnum(str, Enum):
    secure_encrypted_email = "Secure Encrypted Email"
    secure_portal = "Secure Portal"
    def __str__(self): return self.value

class APIAuthenticationTypeEnum(str, Enum):
    oauth2 = "OAuth2"
    api_key = "API Key"
    
    def __str__(self): return self.value

class RoleTypeEnum(str, Enum):
    standard = "Standard"
    custom = "Custom"
    def __str__(self): return self.value
class UserTypeEnum(str, Enum):
    client = "client"
    sales_rep = "sales_rep"
    approver = "approver"
    def __str__(self): return self.value

class NotificationTypeEnum(str, Enum):
    info = "Info"
    alert = "Alert"
    warning = "Warning"
    request = "Request"
    other = "Other"
    def __str__(self): return self.value

class NotificationPriorityEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    def __str__(self): return self.value

from enum import Enum

class FileStatusEnum(str, Enum):
    uploaded = "Uploaded"
    validated = "Validated"
    approved = "Approved"
    rejected = "Rejected"
    on_hold = "On-Hold"

    def __str__(self):
        return self.value

class AutoDecisionStatusEnum(str, Enum):
    approved = "approved"
    rejected = "rejected"
    on_hold = "on-hold"
    def __str__(self): return self.value

class ApproverStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped = "skipped"
    def __str__(self): return self.value

class ManualDecisionStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    on_hold = "on-hold"
    def __str__(self): return self.value

class FileOperationEnum(str, Enum):
    uploaded = "uploaded"
    validated = "validated"
    auto_approved = "auto_approved"
    auto_rejected = "auto_rejected"
    manual_review_initiated = "manual_review_initiated"

    primary_approver_assigned = "primary_approver_assigned"
    primary_approver_approved = "primary_approver_approved"
    primary_approver_rejected = "primary_approver_rejected"
    primary_approver_escalated = "primary_approver_escalated"

    backup_approver_assigned = "backup_approver_assigned"
    backup_approver_approved = "backup_approver_approved"
    backup_approver_rejected = "backup_approver_rejected"
    backup_approver_escalated = "backup_approver_escalated"

    secondary_approver_assigned = "secondary_approver_assigned"
    secondary_approver_approved = "secondary_approver_approved"
    secondary_approver_rejected = "secondary_approver_rejected"
    secondary_approver_escalated = "secondary_approver_escalated"

    final_decision_approved = "final_decision_approved"
    final_decision_rejected = "final_decision_rejected"
    final_decision_on_hold = "final_decision_on_hold"

    comment_added = "comment_added"
    file_updated = "file_updated"
    file_deleted = "file_deleted"
    resubmitted_after_rejection = "resubmitted_after_rejection"

    def __str__(self): return self.value

from enum import Enum

class ApproverTypeEnum(str, Enum):
    primary = "Primary"
    primary_backup = "Primary Backup"
    secondary = "Secondary"
    secondary_backup = "Secondary Backup"

    def __str__(self): return self.value
