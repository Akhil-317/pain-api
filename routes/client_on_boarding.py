from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends

from models.on_boarding_enums import AddressTypeEnum, EntityTypeEnum, OnboardingStatusEnum
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.on_boarding_models import Address, AuditLog, Company, Contact, User
from schemas.on_boarding_schemas import APITestRequest, CompanyCreateRequest, CompanyCreateResponse, IntegrationSaveRequest, SFTPTestRequest
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.on_boarding_models import Company, SecuritySettings, AuthorizedIP
from schemas.on_boarding_schemas import SecuritySettingsRequest
from services.audit_service import log_audit
from services.auth_service import permission_required


router = APIRouter(prefix="/on-boarding", tags=["client-on-boarding"])

@router.get("/entity-types", summary="Get all entity types")
def get_entity_types(
    current_user: User = Depends(permission_required("view_entity_types"))
):
    """
    Returns a list of available entity types for onboarding.
    """
    return [{"key": e.name, "value": e.value} for e in EntityTypeEnum]

# @router.get("/entity-types", summary="Get all entity types")
# def get_entity_types():
#     """
#     Returns a list of available entity types for onboarding.
#     """
#     return [{"key": e.name, "value": e.value} for e in EntityTypeEnum]

# @router.get("/countries", response_model=List[CountryOut])
# def get_countries(db: Session = Depends(get_db)):
#     countries = db.query(Country).order_by(Country.name).all()
#     if not countries:
#         raise HTTPException(status_code=404, detail="No countries found.")
#     return countries

# @router.get("/countries/{country_id}/states", response_model=List[StateOut])
# def get_states_by_country(country_id: int, db: Session = Depends(get_db)):
#     states = db.query(State).filter(State.country_id == country_id).all()
#     if not states:
#         raise HTTPException(status_code=404, detail="No states found for this country.")
#     return states

from models.on_boarding_enums import OwnershipEnum

@router.get("/ownership-types", summary="Get all ownership types")
def get_ownership_types(
        current_user: User = Depends(permission_required("view_entity_types"))
):
    """
    Returns a list of available ownership types for onboarding.
    """
    return [{"key": o.name, "value": o.value} for o in OwnershipEnum]


@router.post("/company", response_model=CompanyCreateResponse, summary="Create company with addresses and contacts")
def create_company_with_details(payload: CompanyCreateRequest, db: Session = Depends(get_db)):
    try:
        now = datetime.utcnow()

        # 1️⃣ Create Company
        company = Company(
            company_name=payload.company_name.strip(),
            company_url=payload.company_url,
            entity_type=payload.entity_type,
            entity_type_other=payload.entity_type_other,
            ownership=payload.ownership,
            ownership_other=payload.ownership_other,
            tax_id_number=payload.tax_id.strip(),
            naics_code=payload.naics_code,
            naics_description=payload.naics_description,
            onboarding_status=OnboardingStatusEnum.onboarding_in_progress,
            step_in_progress=2,
            created_at=now,
            updated_at=now
        )
        db.add(company)
        db.flush()

        # 2️⃣ Create Physical Address
        db.add(Address(
            company_id=company.id,
            address_line_1=payload.physical_address.address_line_1,
            address_line_2=payload.physical_address.address_line_2,
            address_line_3=payload.physical_address.address_line_3,
            city=payload.physical_address.city,
            state=payload.physical_address.state,
            zipcode=payload.physical_address.zipcode,
            country=payload.physical_address.country,
            mailing_same=payload.mailing_address_same,
            address_type=AddressTypeEnum.physical
        ))

        # 3️⃣ Create Mailing Address (Derived or Provided)
        mailing_data = payload.physical_address if payload.mailing_address_same else payload.mailing_address
        db.add(Address(
            company_id=company.id,
            address_line_1=mailing_data.address_line_1,
            address_line_2=mailing_data.address_line_2,
            address_line_3=mailing_data.address_line_3,
            city=mailing_data.city,
            state=mailing_data.state,
            zipcode=mailing_data.zipcode,
            country=mailing_data.country,
            mailing_same=payload.mailing_address_same,
            address_type=AddressTypeEnum.mailing
        ))

        # 4️⃣ Create Contacts
        for contact in payload.contacts:
            db.add(Contact(
                company_id=company.id,
                contact_type=contact.contact_type,
                name=contact.name.strip(),
                email=contact.email.strip(),
                phone=contact.phone.strip() if contact.phone else None
            ))

        log_audit(
    db=db,
    audit_title="Company Onboarding Created",
    message=f"New company onboarding initiated for '{company.company_name}' (ID: {company.id})"
)


        return CompanyCreateResponse(
            company_id=company.id,
            message="Company onboarding created successfully."
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create onboarding: {str(e)}")



@router.post("/security-settings")
def save_security_settings(request: SecuritySettingsRequest, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 1. Create SecuritySettings
        security = SecuritySettings(
            company_id=request.company_id,
            restriction_configuration=request.access_control_preference,
            email_otp_enable=request.otp_email_enabled,
            sms_otp_enable=request.otp_phone_enabled,
            email_for_verification=request.verification_email,
            mobile_number_otp_for_verification=request.verification_phone
        )
        db.add(security)

        # 2. Add Authorized IPs
        for ip in request.authorized_ips:
            db.add(AuthorizedIP(company_id=request.company_id, ip_address=str(ip)))

        # 3. Update Company.step_in_progress
        company.step_in_progress = 3
        db.commit()

        # 4. Audit
        log_audit(
    db=db,
    audit_title="Security Settings Saved",
    message=f"Security settings saved for Company ID {company.id}"
)

        return {"message": "Security settings saved", "company_id": company.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save security settings: {str(e)}")



# In-memory placeholder – clear on server restart
TEMP_SSH_KEYS = {}
sftp_connection_successful = False

from fastapi import UploadFile, File, HTTPException, APIRouter


@router.post("/upload-ssh-key")
def upload_ssh_key(file: UploadFile = File(...)):
    """
    Upload an SSH private key to use for SFTP authentication later.
    Temporarily stores the content in memory.
    """
    try:
        if not file.filename.endswith(".pem"):
            raise HTTPException(status_code=400, detail="Only .pem private keys are allowed.")

        content = file.file.read().decode("utf-8")
        TEMP_SSH_KEYS["ssh_key"] = content
       
        return {"message": "SSH key uploaded and stored successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store SSH key: {str(e)}")

from utils.connections import check_sftp_connection
import tempfile


@router.post("/test-sftp-connection")
def test_sftp_connection(request: SFTPTestRequest):
    """
    Tests the SFTP connection using uploaded SSH key or password.
    """
    try:
        if request.auth_method == "key":
            ssh_key_content = TEMP_SSH_KEYS.get("ssh_key")
            if not ssh_key_content:
                raise HTTPException(status_code=400, detail="No SSH key uploaded. Please upload it first.")

            # Save to a temp file
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".pem") as tmp_key:
                tmp_key.write(ssh_key_content)
                ssh_key_path = tmp_key.name

            success = check_sftp_connection(
                host=request.host,
                port=request.port,
                username=request.username,
                auth_method="key",
                ssh_key_path=ssh_key_path
            )
        else:
            success = check_sftp_connection(
                host=request.host,
                port=request.port,
                username=request.username,
                auth_method="password",
                password=request.password
            )

        if success:
            sftp_connection_successful = True
            print(sftp_connection_successful)
            return {"message": "✅ SFTP connection successful."}
        else:
            raise HTTPException(status_code=400, detail="❌ Failed to connect to SFTP server.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test SFTP connection: {str(e)}")

api_connection_successful = False

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
from sqlalchemy.orm import Session
from utils.connections import check_api_connection  # Assuming your function is in utils/api_utils.py




@router.post("/test-api-connection", summary="Test external API connectivity")
def test_api_connection(request: APITestRequest):
    """
    Test connectivity to a 3rd-party API with optional authentication.
    """
    try:
        success = check_api_connection(
            url=request.url,
            auth_type=request.auth_type,
            token=request.token,
            api_key=request.api_key,
            api_key_header_name=request.api_key_header_name,
            custom_headers=request.custom_headers,
            ssl_enabled=request.ssl_enabled,
        )

        if success:
            api_connection_successful = True
            print(api_connection_successful)
            return {"message": "✅ API connection successful."}
        else:
            raise HTTPException(status_code=400, detail="❌ API connection failed. Please check credentials or URL.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test API connection: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models.on_boarding_models import SystemIntegration, SFTPDetails, APIDetails
from models.on_boarding_enums import FileTransmissionMethodEnum, AuthenticationMethodEnum, FileUploadFrequencyEnum
from services.audit_service import log_audit



@router.post("/save-integration-settings", summary="Store integration preferences for a company")
def save_integration_settings(request: IntegrationSaveRequest, db: Session = Depends(get_db)):
    try:

        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Step 1️⃣ Save System Integration
        integration = SystemIntegration(
            company_id=request.company_id,
            transmission_method=request.file_transmission_method,
            file_upload_frequency=request.file_frequency,
            file_format=request.file_format,
            
        )
        db.add(integration)
        db.flush()

        # Step 2️⃣ Save SFTP Details
        if request.file_transmission_method == FileTransmissionMethodEnum.sftp:
            if not request.sftp_details:
                raise HTTPException(status_code=400, detail="Missing SFTP details.")
            db.add(SFTPDetails(
                system_integration_id=integration.id,
                host=request.sftp_details.host,
                port=request.sftp_details.port,
                username=request.sftp_details.username,
                auth_method=request.sftp_details.auth_method,
                credential_delivery_method=request.sftp_details.credential_delivery_method,
                ssh_key=TEMP_SSH_KEYS.get("ssh_key") if request.sftp_details.auth_method == AuthenticationMethodEnum.key else None
            ))

        # Step 3️⃣ Save API Details
        elif request.file_transmission_method == FileTransmissionMethodEnum.api:
            if not request.api_details:
                raise HTTPException(status_code=400, detail="Missing API details.")
            db.add(APIDetails(
                system_integration_id=integration.id,
                url=request.api_details.url,
                auth_type=request.api_details.auth_type,
                ssl_enabled=request.api_details.ssl_enabled
            ))


        company.step_in_progress = 4
        db.commit()



        # Step 4️⃣ Audit Logging
        log_audit(
            db=db,
            audit_title="system",
            message=f"Integration settings saved for Company ID {request.company_id}"
        )

        return {"message": "✅ Integration settings saved successfully.", "system_integration_id": integration.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save integration settings: {str(e)}")




from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.on_boarding_models import Company, ValidationPreferences
from schemas.on_boarding_schemas import XMLValidationPreferenceRequest
from services.audit_service import log_audit


@router.post("/validation-preferences", summary="Set XML validation preferences")
def set_validation_preferences(payload: XMLValidationPreferenceRequest, db: Session = Depends(get_db)):
    try:
        # 🔍 Check if company exists
        company = db.query(Company).filter(Company.id == payload.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # ❌ Prevent duplicate preferences
        existing = db.query(ValidationPreferences).filter(
            ValidationPreferences.company_id == payload.company_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Validation preferences already set for this company.")

        # ✅ Insert into validation_preferences
        preference = ValidationPreferences(
            company_id=payload.company_id,
            validation_option=payload.xml_validation
        )
        db.add(preference)

        # 🔁 Update step_in_progress to 5
        company.step_in_progress = 5

        # 🪵 Add audit log
        log_audit(
            db=db,
            audit_title="Validation Preferences Set",  # Replace with user ID later if needed
            message=f"Validation preferences set to '{payload.xml_validation}' for Company ID {payload.company_id}"
        )

        db.commit()
        return {
            "message": "Validation preferences saved successfully.",
            "company_id": payload.company_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save validation preferences: {str(e)}")


from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.audit_service import log_audit
from models.on_boarding_models import (
    Company, ApprovalConfig, AutoApprovalSettings, ControlTotalApprovalSettings,
    ManualApprovalSingleSettings, ManualApprovalMultiSettings
)
from schemas.on_boarding_schemas import ApprovalSettingsRequest  # Define below
from fastapi import status


@router.post("/approval-settings", status_code=status.HTTP_201_CREATED)
def set_approval_settings(request: ApprovalSettingsRequest, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # ✅ Save main Approval config
        db.add(ApprovalConfig(
            company_id=request.company_id,
            approval_type_config=request.approval_type_config
        ))

        # 🟡 Conditionally add child configs
        if request.auto:
            db.add(AutoApprovalSettings(
                company_id=request.company_id,
                max_auto_approval_amount=request.auto.max_dollar_limit,
                enable_update_dollar_limit=request.auto.enable_update_dollar_limit,
                exceed_limit_behavior=request.auto.exceed_limit_behavior
            ))

        if request.control_total:
            db.add(ControlTotalApprovalSettings(
                company_id=request.company_id,
                file_format=request.control_total.file_format,
                prefix=request.control_total.prefix,
                timezone=request.control_total.timezone,
                duplicate_file=request.control_total.duplicate_file,
                duplicate_file_data=request.control_total.duplicate_file_data
            ))

        if request.manual_single:
            db.add(ManualApprovalSingleSettings(
                company_id=request.company_id,
                wait_time_before_moving_to_backup=request.manual_single.wait_time_before_moving_to_backup,
                wait_time_before_escalation=request.manual_single.wait_time_before_escalation,
                escalation_option=request.manual_single.escalation_option
            ))

        if request.manual_multi:
            db.add(ManualApprovalMultiSettings(
                company_id=request.company_id,
                wait_time_primary_approver=request.manual_multi.wait_time_primary_approver,
                wait_time_primary_backup_approver=request.manual_multi.wait_time_primary_backup_approver,
                wait_time_secondary_approver=request.manual_multi.wait_time_secondary_approver,
                wait_time_secondary_backup_approver=request.manual_multi.wait_time_secondary_backup_approver,
                escalation_option_for_primary_approver=request.manual_multi.escalation_option_for_primary_approver,
                escalation_option_for_primary_backup_approver=request.manual_multi.escalation_option_for_primary_backup_approver,
                escalation_option_for_secondary_approver=request.manual_multi.escalation_option_for_secondary_approver,
                escalation_option_for_secondary_backup_approver=request.manual_multi.escalation_option_for_secondary_backup_approver,
            ))

        # 🔄 Step progress + Commit
        company.step_in_progress = 6
        db.commit()

        # 📝 Audit Log
        log_audit(db=db, audit_title="Approval Settings", message=f"Approval settings configured for Company ID {request.company_id}")

        return {"message": "Approval settings saved successfully", "company_id": request.company_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save approval settings: {str(e)}")
    

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.on_boarding_models import Company, OFACCertification
from schemas.on_boarding_schemas import OFACCertificationRequest
from models.on_boarding_enums import OnboardingStatusEnum
from services.audit_service import log_audit


@router.post("/ofac-certification", summary="Submit OFAC Certification")
def submit_ofac_certification(request: OFACCertificationRequest, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not request.is_certified:
            raise HTTPException(status_code=400, detail="Must be certified")

        # Check if already certified to avoid duplicates
        existing = db.query(OFACCertification).filter(OFACCertification.company_id == request.company_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="OFAC certification already exists for this company")

        # Create new record
        ofac = OFACCertification(
            company_id=request.company_id,
            is_certified=True
        )
        db.add(ofac)

        # Update company step & status
        company.step_in_progress = 7
        company.onboarding_status = OnboardingStatusEnum.onboarding_done
        db.commit()

        # Audit log
        log_audit(db=db, changed_by="On boarding done", message=f"OFAC certification completed for Company ID {company.id}")

        return {"message": "OFAC certification recorded successfully", "company_id": company.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit OFAC certification: {str(e)}")
