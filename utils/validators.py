import re
from urllib.parse import urlparse
from sqlalchemy.orm import validates

def is_valid_password(password: str) -> bool:
    """
    Password must:
    - Be at least 8 characters long
    - Include uppercase, lowercase, number, and special character
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"[a-z]", password): 
        return False
    if not re.search(r"\d", password):    
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):  
        return False
    return True

def is_valid_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_valid_tax_id(value: str) -> bool:
    # Example: Basic check for 9-digit EIN/TaxID
    return bool(re.fullmatch(r"\d{2}-\d{7}", value) or re.fullmatch(r"\d{9}", value))

def is_valid_company_name(value: str) -> bool:
    return bool(value.strip())

def is_valid_naics(value: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", value))

import re

def is_valid_zipcode(value: str) -> bool:
    """Validate US ZIP code (5-digit or ZIP+4)."""
    return bool(re.match(r"^\d{5}(-\d{4})?$", value))

def is_valid_state(value: str) -> bool:
    """Basic validation to check state is alphabetic and reasonable length."""
    return bool(value and value.isalpha() and 2 <= len(value) <= 100)

def is_valid_country(value: str) -> bool:
    """Basic country validation."""
    return bool(value and value.isalpha() and 2 <= len(value) <= 100)


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email.strip()))

def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?\d{7,15}$", phone.strip()))


def is_valid_hostname_or_ip(value: str) -> bool:
    ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    hostname_pattern = r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,})+$"
    return bool(re.match(ip_pattern, value) or re.match(hostname_pattern, value))

def is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535

from urllib.parse import urlparse

def is_valid_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False
import ipaddress

def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False
