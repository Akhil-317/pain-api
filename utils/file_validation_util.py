import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import re
import csv
import zipfile
import logging
from lxml import etree
from xmldiff import main as xmldiff
from pain001.xmlutils import validate
from jinja2 import Template
import time
from holidays import UnitedStates
from colorama import Fore, Style, init
from datetime import datetime, timedelta, time as dtime
init(autoreset=True)

# Configuration switches
XML_DIR = "files/pain001_upload_xml_files" #pain001.001.003.xml input
CSV_DIR = "files/pain001_upload_csv_files" #input 
SCHEMA_DIR = "files/pain_001_schemas_xsd" #o
REFERENCE_DIR = "files/pain_001_reference_xml" #o
TEMPLATE_DIR = "files/pain_001_templates_xml" #o
REPORTS_DIR = "files/pain_001_output_reports" 
ENABLE_CONSOLE_SUMMARY = True
ENABLE_ZIP_EXPORT = False
LOG_LEVEL = logging.INFO
ALLOW_VERSION_PROMPT = True
SKIP_LOG_TO_TXT = True
RUN_SESSION_LOG_TO_TXT = True
ENABLE_XML_DIFF = False
ENABLE_HTML_ANNOTATION = True  # New config: Controls whether annotated HTML is generated

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pain001_validation.log"),
        logging.StreamHandler()
    ]
)

os.makedirs(REPORTS_DIR, exist_ok=True)
seen_message_ids = {}
html_files_generated = []

# Helpers

def log_check_result(f, description, passed):
    if f:
        if passed:
            f.write(f"    ✔️ {description} passed.\n")
        else:
            f.write(f"    ❌ {description} failed.\n")
    if passed:
        print(f"{Fore.GREEN}    ✔️ {description} passed.")
    else:
        print(f"{Fore.RED}    ❌ {description} failed.")


def iban_checksum_is_valid(iban):
    """Validate IBAN using ISO 13616 checksum rules."""
    # 1. Move the four initial characters to the end of the string
    rearranged = iban[4:] + iban[:4]
    
    # 2. Replace each letter in the string with two digits
    numeric_iban = ''
    for ch in rearranged:
        if ch.isdigit():
            numeric_iban += ch
        else:
            numeric_iban += str(ord(ch.upper()) - 55)
    
    # 3. Interpret the string as a decimal integer and compute the remainder of that number on division by 97
    return int(numeric_iban) % 97 == 1


def aba_routing_mod10_check(value):
    if len(value) != 9 or not value.isdigit():
        return False
    weights = [3, 7, 1] * 3
    total = sum(int(d) * w for d, w in zip(value, weights))
    return total % 10 == 0

def check_member_id(xml_path):
    errors = []
    info = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}
        mmbid_nodes = tree.findall('.//ns:DbtrAgt/ns:FinInstnId/ns:ClrSysMmbId/ns:MmbId', namespaces=ns)
        if not mmbid_nodes:
            info.append("No Member IDs (MmbId) found.")
        else:
            for node in mmbid_nodes:
                mmbid = node.text.strip()
                if not mmbid.isdigit():
                    line = node.sourceline if node is not None else "Unknown"
                    errors.append(f"Line {line} - Member ID (MmbId) is not numeric: {mmbid}")

    except Exception as e:
        errors.append(f"Error during Member ID check: {str(e)}")
    return errors, info

def check_duplicate_end_to_end_id(xml_path):
    errors = []
    info = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}
        seen_ids = {}

        end_to_end_nodes = tree.findall('.//ns:CdtTrfTxInf/ns:PmtId/ns:EndToEndId', namespaces=ns)
        if not end_to_end_nodes:
            info.append("No EndToEndId elements found in file.")
        
        for node in end_to_end_nodes:
            end_to_end_id = node.text.strip()
            line = node.sourceline if node is not None else "Unknown"

            if end_to_end_id in seen_ids:
                errors.append(f"Line {line} - Duplicate EndToEndId '{end_to_end_id}' found (also at Line {seen_ids[end_to_end_id]}).")
            else:
                seen_ids[end_to_end_id] = line

    except Exception as e:
        errors.append(f"Error during Duplicate EndToEndId check: {str(e)}")
    
    return errors, info


def check_total_file_control(xml_path):
    errors = []
    nboftxs_passed = True
    ctrlsum_passed = True
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()
        ns = {'ns': root.nsmap[None]}

        nb_of_txs_element = tree.find('.//ns:NbOfTxs', namespaces=ns)
        nb_of_txs_declared = nb_of_txs_element.text.strip() if nb_of_txs_element is not None else None

        ctrl_sum_element = tree.find('.//ns:CtrlSum', namespaces=ns)
        ctrl_sum_declared = ctrl_sum_element.text.strip() if ctrl_sum_element is not None else None

        instd_amt_nodes = tree.findall('.//ns:CdtTrfTxInf/ns:Amt/ns:InstdAmt', namespaces=ns)

        nb_of_txs_actual = len(instd_amt_nodes)
        sum_of_amounts = 0.0
        for node in instd_amt_nodes:
            try:
                amount = float(node.text.strip())
                if amount <= 0:
                    line = node.sourceline if node is not None else "Unknown"
                    errors.append(f"Line {line} - InstdAmt must be greater than 0. Found: {amount}")
                sum_of_amounts += amount
            except Exception:
                errors.append("Invalid amount format in one of the <InstdAmt> fields.")

        # NbOfTxs Check
        if nb_of_txs_declared:
            if int(nb_of_txs_declared) != nb_of_txs_actual:
                line_nb = nb_of_txs_element.sourceline if nb_of_txs_element is not None else "Unknown"
                errors.append(f"Line {line_nb} - NbOfTxs mismatch: Declared {nb_of_txs_declared}, Found {nb_of_txs_actual} transactions in the file.")
                nboftxs_passed = False

        # CtrlSum Check
        if ctrl_sum_declared:
            declared_sum = float(ctrl_sum_declared)
            if declared_sum <= 0:
                line_ctrl = ctrl_sum_element.sourceline if ctrl_sum_element is not None else "Unknown"
                errors.append(f"Line {line_ctrl} - CtrlSum must be greater than 0. Found: {declared_sum}")
                ctrlsum_passed = False
            if round(declared_sum, 2) != round(sum_of_amounts, 2):
                line_ctrl = ctrl_sum_element.sourceline if ctrl_sum_element is not None else "Unknown"
                errors.append(f"Line {line_ctrl} - CtrlSum mismatch: Declared {declared_sum}, Calculated {round(sum_of_amounts, 2)} from transaction amounts.")
                ctrlsum_passed = False

    except Exception as e:
        errors.append(f"Error during total file control check: {str(e)}")
        nboftxs_passed = False
        ctrlsum_passed = False

    return errors, nboftxs_passed, ctrlsum_passed



def check_mod10_fields(xml_path):
    errors = []
    info = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        iban_nodes = tree.findall('.//ns:DbtrAcct/ns:Id/ns:IBAN', namespaces=ns)
        if not iban_nodes:
            info.append("No IBANs found for Mod10 check.")
        else:
            for node in iban_nodes:
                iban = node.text.strip()
                if not iban_checksum_is_valid(iban):
                    errors.append(f"Mod10 check failed for IBAN: {iban}")

    except Exception as e:
        errors.append(f"Error during Mod10 check: {str(e)}")
    return errors, info

def check_aba_routing(xml_path):
    errors = []
    info = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        bic_nodes = tree.findall('.//ns:DbtrAgt/ns:FinInstnId/ns:BIC', namespaces=ns)
        found_numeric_bic = False
        for node in bic_nodes:
            bic = node.text.strip()
            if bic.isdigit() and len(bic) == 9:
                found_numeric_bic = True
                if not aba_routing_mod10_check(bic):
                    errors.append(f"ABA Routing Mod10 check failed for BIC: {bic}")

        if not found_numeric_bic:
            info.append("No 9-digit BICs found for ABA check.")

    except Exception as e:
        errors.append(f"Error during ABA Routing check: {str(e)}")
    return errors, info

def check_purpose_code(xml_path):
    errors = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        # Define valid purpose codes
        valid_purpose_codes = {
            "SALA", "PENS", "TAXS", "INTE", "DIVI", "CASH", "GOVT", "SUPP",
            "INSM", "CBTV", "RLWY", "GASB", "ELEC", "WTER", "TELB", "INFR",
            "HSPC", "CHAR", "TRAD", "GDSV"
        }

        purp_nodes = tree.findall('.//ns:Purp/ns:Cd', namespaces=ns)
        for node in purp_nodes:
            code = node.text.strip()
            if code not in valid_purpose_codes:
                line = node.sourceline if node is not None else "Unknown"
                errors.append(f"Line {line} - Invalid Purpose Code found: {code}")

    except Exception as e:
        errors.append(f"Error during Purpose Code check: {str(e)}")
    return errors

def check_utf8_encoding(xml_path):
    errors = []
    try:
        with open(xml_path, "rb") as f:
            raw_data = f.read()
        try:
            raw_data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append("File is not properly UTF-8 encoded.")
    except Exception as e:
        errors.append(f"Error during UTF-8 encoding check: {str(e)}")
    return errors

def check_currency_codes(xml_path):
    errors = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        # Define valid ISO currency codes
        valid_currency_codes = {
            "USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "CHF", "CNY",
            "SEK", "NZD", "SGD", "HKD", "NOK", "KRW", "TRY", "RUB", "BRL", "ZAR"
        }

        currency_nodes = tree.findall('.//ns:InstdAmt', namespaces=ns)
        for node in currency_nodes:
            currency_attr = node.attrib.get('Ccy')
            if currency_attr and currency_attr not in valid_currency_codes:
                line = node.sourceline if node is not None else "Unknown"
                errors.append(f"Line {line} - Invalid Currency Code found: {currency_attr}")

    except Exception as e:
        errors.append(f"Error during Currency Code check: {str(e)}")
    return errors

def check_duplicate_message_id(xml_path, seen_message_ids, current_filename):
    errors = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        msg_id_node = tree.find('.//ns:GrpHdr/ns:MsgId', namespaces=ns)
        if msg_id_node is not None:
            msg_id = msg_id_node.text.strip()
            line = msg_id_node.sourceline if msg_id_node is not None else "Unknown"

            if msg_id in seen_message_ids:
                prev_files = seen_message_ids[msg_id]
                error_msg = f"Line {line} - Duplicate Message ID '{msg_id}' found. (Already used in files: {prev_files})"
                errors.append(error_msg)
                seen_message_ids[msg_id].append(current_filename)  # Also add current file
            else:
                seen_message_ids[msg_id] = [current_filename]

    except Exception as e:
        errors.append(f"Error during Duplicate Message ID check: {str(e)}")
    return errors

def check_payment_dates(xml_path):
    errors = []
    payment_date_results = {}

    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}
        today = datetime.utcnow().date()
        now_utc = datetime.utcnow()
        timestamp_str = now_utc.strftime("%A, %Y-%m-%d at %H:%M:%S UTC")
        us_holidays = UnitedStates()

        # Parse <CreDtTm> once for WIRE/RTP time-of-day validation
        cre_dt_tm = None
        cre_dt_tm_node = tree.find('.//ns:GrpHdr/ns:CreDtTm', namespaces=ns)
        if cre_dt_tm_node is not None:
            try:
                cre_dt_tm = datetime.strptime(cre_dt_tm_node.text.strip(), "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(tz=None)
            except Exception as e1:
                try:
                    cre_dt_tm = datetime.strptime(cre_dt_tm_node.text.strip(), "%Y-%m-%dT%H:%M:%S%z").astimezone(tz=None)
                except Exception as e2:
                    errors.append(f"⚠️ Could not parse CreDtTm ('{cre_dt_tm_node.text.strip()}') — error: {e2.__class__.__name__}: {e2}. Skipping business hours check.")

        pmtinf_nodes = tree.findall('.//ns:PmtInf', namespaces=ns)
        for pmtinf in pmtinf_nodes:
            pmtmtd_node = pmtinf.find('./ns:PmtMtd', namespaces=ns)
            pmtmtd = pmtmtd_node.text.strip() if pmtmtd_node is not None else ""

            svclvl_node = pmtinf.find('./ns:PmtTpInf/ns:SvcLvl/ns:Cd', namespaces=ns)
            svclvl = svclvl_node.text.strip() if svclvl_node is not None else ""

            lclinstrm_node = pmtinf.find('./ns:PmtTpInf/ns:LclInstrm/ns:Cd', namespaces=ns)
            lclinstrm = lclinstrm_node.text.strip() if lclinstrm_node is not None else ""

            reqd_exctn_dt_node = pmtinf.find('./ns:ReqdExctnDt', namespaces=ns)
            if reqd_exctn_dt_node is None:
                errors.append("PaymentInfo missing ReqdExctnDt.")
                continue

            try:
                reqd_exctn_dt = datetime.strptime(reqd_exctn_dt_node.text.strip(), "%Y-%m-%d").date()
            except ValueError:
                line = reqd_exctn_dt_node.sourceline if reqd_exctn_dt_node is not None else "Unknown"
                errors.append(f"Line {line} - Invalid ReqdExctnDt format (should be YYYY-MM-DD).")
                errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                continue

            # Detect Transaction Type
            txn_type = "OTHER"
            if pmtmtd == "CHK":
                txn_type = "CHK"
            elif pmtmtd == "TRF":
                if lclinstrm == "RTP":
                    txn_type = "RTP"
                elif svclvl in ["URGP", "SDVA"]:
                    txn_type = "WIRE"
                elif svclvl in ["CUST", "ACH"]:
                    txn_type = "ACH"
                else:
                    txn_type = "ACH"

            if txn_type not in payment_date_results:
                payment_date_results[txn_type] = True

            line = reqd_exctn_dt_node.sourceline if reqd_exctn_dt_node is not None else "Unknown"

            def next_business_datetime():
                suggest = today
                while suggest.weekday() >= 5 or suggest in us_holidays:
                    suggest += timedelta(days=1)
                return datetime.combine(suggest, dtime(9, 0)).strftime("%A, %Y-%m-%d at %H:%M:%S UTC")

            # === VALIDATION LOGIC ===

            if txn_type == "CHK":
                if not (today - timedelta(days=3) <= reqd_exctn_dt <= today):
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - CHK payment must have execution date within past 3 days. Found: {reqd_exctn_dt}")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")

            elif txn_type in ["WIRE", "RTP"]:
                if reqd_exctn_dt != today:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - {txn_type} payment must have execution date as today. Found: {reqd_exctn_dt}")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {now_utc.replace(hour=9, minute=0, second=0, microsecond=0).strftime('%A, %Y-%m-%d at %H:%M:%S UTC')} (today)")
                elif reqd_exctn_dt.weekday() >= 5:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - {txn_type} payment falls on a weekend ({reqd_exctn_dt.strftime('%A')}) which is non-settlement day.")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")
                elif reqd_exctn_dt in us_holidays:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - {txn_type} payment cannot be processed on U.S. federal holiday: {us_holidays[reqd_exctn_dt]}.")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")
                elif cre_dt_tm:
                    submit_time = cre_dt_tm.time()
                    if submit_time < dtime(9, 0) or submit_time >= dtime(17, 0):
                        payment_date_results[txn_type] = False
                        errors.append(f"Line {line} - {txn_type} submission time {submit_time.strftime('%H:%M:%S')} UTC is outside allowed window (09:00–17:00 UTC).")
                        errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                        errors.append(f"    📌 Suggested next valid submission time: 09:00:00 UTC on {cre_dt_tm.date().strftime('%A, %Y-%m-%d')}")

            elif txn_type == "ACH":
                if reqd_exctn_dt < today:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - ACH payment must have execution date today or in the future. Found: {reqd_exctn_dt}")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (next business day)")
                elif reqd_exctn_dt.weekday() >= 5:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - ACH payment falls on a weekend ({reqd_exctn_dt.strftime('%A')}) which is non-settlement day.")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")
                elif reqd_exctn_dt in us_holidays:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - ACH payment cannot be scheduled on U.S. federal holiday: {us_holidays[reqd_exctn_dt]}.")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")

            else:
                if reqd_exctn_dt < today:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - Unknown payment type treated as ACH. Execution date must be today or future. Found: {reqd_exctn_dt}")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (next business day)")
                elif reqd_exctn_dt.weekday() >= 5:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - Unknown payment type treated as ACH. Execution date falls on weekend ({reqd_exctn_dt.strftime('%A')}).")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")
                elif reqd_exctn_dt in us_holidays:
                    payment_date_results[txn_type] = False
                    errors.append(f"Line {line} - Unknown payment type treated as ACH. Execution date is a U.S. federal holiday ({us_holidays[reqd_exctn_dt]}).")
                    errors.append(f"    ⏱️ Validation attempted on {timestamp_str}.")
                    errors.append(f"    📌 Suggested next valid execution: {next_business_datetime()} (not a weekend/holiday)")

    except Exception as e:
        errors.append(f"Error during Payment Date check: {str(e)}")

    return errors, payment_date_results




def check_country_codes(xml_path):
    errors = []
    try:
        tree = etree.parse(xml_path)
        ns = {'ns': tree.getroot().nsmap[None]}

        valid_country_codes = {  # (full set pasted here)
            "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
            "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
            "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
            "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
            "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG",
            "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR",
            "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP",
            "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK",
            "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM",
            "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NC", "NE",
            "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK",
            "PL", "PM", "PN", "PR", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC",
            "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV", "SX",
            "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV",
            "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI", "VN", "VU", "WF", "WS",
            "YE", "YT", "ZA", "ZM", "ZW"
        }

        ctry_nodes = tree.findall('.//ns:Ctry', namespaces=ns)
        for node in ctry_nodes:
            country = node.text.strip()
            if len(country) != 2 or country.upper() not in valid_country_codes:
                line = node.sourceline if node is not None else "Unknown"
                errors.append(f"Line {line} - Invalid Country Code: {country}")

    except Exception as e:
        errors.append(f"Error during Country Code check: {str(e)}")
    return errors

def write_annotated_html(xml_file_path, errors, summary_text, output_dir=REPORTS_DIR):
    """
    Creates a split-pane interactive HTML editor with error line highlights and inline messages.
    Displays full validation summary, supports dark/light mode toggle, and auto-clears errors on edit.
    
    :param xml_file_path: Path to the XML file to annotate.
    :param errors: List of validation errors with line numbers.
    :param summary_text: Full validation summary (str) with ✔️, ⚠️, ℹ️ lines.
    :param output_dir: Where to save the HTML file.
    :return: Path to the generated interactive HTML.
    """
    import os
    import re
    import html
    import logging

    original_name = os.path.splitext(os.path.basename(xml_file_path))[0]

    line_error_map = {}
    for err in errors:
        match = re.search(r"Line (\d+)", err)
        if match:
            line_no = int(match.group(1))
            line_error_map.setdefault(line_no, []).append(err)

    with open(xml_file_path, "r", encoding="utf-8") as f:
        xml_lines = f.readlines()

    html_lines = [
        "<!DOCTYPE html>",
        f"<html class='dark-theme'><head><meta charset='utf-8'>",
        "<style>",
        "body { margin: 0; display: flex; height: 100vh; font-family: 'Courier New', monospace; }",
        ".left, .right { flex: 1; overflow: auto; padding: 10px; box-sizing: border-box; }",
        ".left { background: var(--bg-left); color: var(--text-left); }",
        ".right { background: var(--bg-right); color: var(--text-right); }",
        ".line { display: flex; align-items: flex-start; }",
        ".line-number { width: 50px; text-align: right; padding-right: 10px; background: var(--bg-left); color: var(--line-num); font-size: 15px; line-height: 1.4em; }",
        ".code-line { flex: 1; background: var(--bg-left); color: var(--text-left); font-size: 15px; line-height: 1.4em; padding: 0 8px; white-space: pre; border-left: 4px solid transparent; }",
        ".code-line:hover { background-color: var(--hover-bg); }",
        ".code-line.error { background: #3c1f1f; color: #ff9999; border-left: 4px solid #ff4d4d; }",
        ".inline-error { margin-left: 60px; background: #3c1f1f; color: #ff9999; font-size: 0.9em; padding: 4px 8px; border-left: 4px solid #ff4d4d; margin-bottom: 4px; }",
        "#nav { position: fixed; top: 10px; right: 1350px; z-index: 999; }",
        "button { margin: 2px; padding: 4px 8px; background: #333; color: white; border: none; border-radius: 4px; cursor: pointer; }",
        "button:hover { background: #555; }",
        ":root.dark-theme { --bg-left: #1e1e1e; --bg-right: #1e1e1e; --text-left: #d4d4d4; --text-right: #cccccc; --line-num: #888; --hover-bg: #2a2a2a; }",
        ":root.light-theme { --bg-left: #f4f4f4; --bg-right: #ffffff; --text-left: #000000; --text-right: #333333; --line-num: #555; --hover-bg: #e0e0e0; }",
        "</style></head><body>",
        f"<script>const ORIGINAL_FILENAME = '{original_name}';</script>"
    ]

    # Left panel with XML lines
    html_lines.append("<div class='left' id='leftPane'>")
    for i, line in enumerate(xml_lines, start=1):
        safe_line = html.escape(line.rstrip())
        is_error = i in line_error_map
        error_class = " error" if is_error else ""

        html_lines.append(f"<div class='line'>")
        html_lines.append(f"<div class='line-number'>{i}</div>")
        html_lines.append(f"<div class='code-line{error_class}' id='line-{i}' contenteditable='true' spellcheck='false'>{safe_line}</div>")
        html_lines.append("</div>")

        if is_error:
            for msg in line_error_map[i]:
                html_lines.append(f"<div class='inline-error'>⚠️ {html.escape(msg)}</div>")
    html_lines.append("</div>")  # End left pane

    # Right panel with full summary
    html_lines.append("<div class='right'><pre id='errorBox' style='white-space: pre-wrap;'>")
    html_lines.append(html.escape(summary_text))
    html_lines.append("</pre></div>")

    # Navigation + script block
    html_lines.append("""
<div id="nav">
    <button onclick="gotoPrevError()">⬆️ Prev</button>
    <button onclick="gotoNextError()">⬇️ Next</button>
    <button onclick="downloadFile()">💾 Download Fixed XML</button>
    <button onclick="toggleTheme()">🌓 Toggle Theme</button>
</div>

<script>
let currentErrorIndex = 0;
function getErrorLines() {
    return [...document.querySelectorAll('.code-line.error')].map(e => parseInt(e.id.split('-')[1]));
}
function gotoError(index) {
    const lines = getErrorLines();
    const targetLine = lines[index];
    const elem = document.getElementById('line-' + targetLine);
    if (elem) elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    currentErrorIndex = index;
}
function gotoNextError() {
    const errors = getErrorLines();
    if (!errors.length) return;
    currentErrorIndex = (currentErrorIndex + 1) % errors.length;
    gotoError(currentErrorIndex);
}
function gotoPrevError() {
    const errors = getErrorLines();
    if (!errors.length) return;
    currentErrorIndex = (currentErrorIndex - 1 + errors.length) % errors.length;
    gotoError(currentErrorIndex);
}
function downloadFile() {
    const codeLines = document.querySelectorAll('.code-line');
    const xmlContent = Array.from(codeLines).map(el => el.innerText).join('\\n');
    const blob = new Blob([xmlContent], {type: 'text/xml'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = ORIGINAL_FILENAME + '_fixed.xml';
    a.click();
}
function toggleTheme() {
    const root = document.documentElement;
    if (root.classList.contains('dark-theme')) {
        root.classList.remove('dark-theme');
        root.classList.add('light-theme');
    } else {
        root.classList.remove('light-theme');
        root.classList.add('dark-theme');
    }
}

// Auto-clear red highlight and inline errors on input
window.addEventListener("DOMContentLoaded", () => {
    const lines = document.querySelectorAll('.code-line');
    lines.forEach(line => {
        line.addEventListener("input", () => {
            line.classList.remove("error");
            const parent = line.parentElement;
            const nextSiblings = [];
            let el = parent.nextElementSibling;
            while (el && el.classList.contains("inline-error")) {
                nextSiblings.push(el);
                el = el.nextElementSibling;
            }
            nextSiblings.forEach(e => e.remove());
        });
    });
});
</script>
""")

    html_lines.append("</body></html>")

    output_name = os.path.basename(xml_file_path).replace(".xml", "_interactive.html")
    output_path = os.path.join(output_dir, output_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    logging.info(f"✅ Interactive HTML with all enhancements created: {output_path}")
    return output_path





def get_version_from_xml(xml_path):
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()
        namespace = root.nsmap[None]
        version = namespace.split('.')[-1]
        logging.info(f"Detected version '{version}' from XML: {xml_path}")
        return f"pain.001.001.{version}"
    except Exception as e:
        logging.warning(f"Failed to parse version from XML {xml_path}: {e}")
        return None

def get_version_from_filename(filename):
    for v in range(3, 10):
        if f"pain.001.001.0{v}" in filename or f"v{v}" in filename.lower():
            version = f"pain.001.001.0{v}"
            logging.info(f"Detected version from filename '{filename}': {version}")
            return version
    logging.warning(f"No version detected in filename: {filename}")
    return None

def prompt_for_version(filename):
    if not ALLOW_VERSION_PROMPT:
        logging.warning(f"Skipping file '{filename}' due to undetectable version and prompting disabled.")
        return None
    print(f"❓ Unable to detect version for '{filename}'.")
    print("Please enter the version number (e.g., 03, 04, ..., 09):")
    while True:
        version_input = input("Version: ").strip()
        if version_input in [f"0{v}" for v in range(3, 10)]:
            version = f"pain.001.001.{version_input}"
            logging.info(f"User manually selected version {version} for '{filename}'")
            return version
        print("❌ Invalid input. Please enter a valid version number between 03 and 09.")

def generate_xml_from_csv(csv_file, version):
    template_path = os.path.join(TEMPLATE_DIR, f"{version}.xml")
    output_path = os.path.join(XML_DIR, os.path.basename(csv_file).replace(".csv", f"_{version}.xml"))
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        template = Template(template_content)
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = next(reader)
        rendered_xml = template.render(**data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_xml)
        logging.info(f"Generated XML written to {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Failed to generate XML for {csv_file}: {e}")
        return None

def extract_line_number_from_error(error_message):
    # First, if already in "Line xyz" format, keep it
    if "Line " in error_message:
        return error_message
    
    # Else try regex extraction
    match = re.search(r'file:.+?:(\d+):\d+:ERROR:', error_message)
    if match:
        line_num = match.group(1)
        short_msg = error_message.split("ERROR:")[-1].strip()
        return f"Line {line_num} - {short_msg}"
    else:
        return error_message


def validate_and_compare(xml_file, version):
    xsd_file = os.path.join(SCHEMA_DIR, f"{version}.xsd")
    reference_file = os.path.join(REFERENCE_DIR, f"ref_{version[-2:]}.xml")
    
    if not os.path.exists(xml_file):
        logging.error(f"File not found for validation: {xml_file}")
        return False, ["Generated XML not found."], [], {}

    # 1. XSD validation
    valid, xsd_errors = validate(xml_file, xsd_file)
    validation_errors = [extract_line_number_from_error(e) for e in xsd_errors] if not valid else []

    # 2. Additional Structure and Logical Checks
    total_control_errors, nboftxs_passed, ctrlsum_passed = check_total_file_control(xml_file)
    mod10_errors, mod10_info = check_mod10_fields(xml_file)
    aba_errors, aba_info = check_aba_routing(xml_file)
    mmbid_errors, mmbid_info = check_member_id(xml_file)   # <-- NEW

    # 3. New Checks (the 4 you added)
    purpose_code_errors = check_purpose_code(xml_file)
    utf8_encoding_errors = check_utf8_encoding(xml_file)
    currency_code_errors = check_currency_codes(xml_file)
    duplicate_msgid_errors = check_duplicate_message_id(xml_file, seen_message_ids, os.path.basename(xml_file))
    payment_date_errors, payment_date_results = check_payment_dates(xml_file)
    country_code_errors = check_country_codes(xml_file)
    duplicate_e2e_errors, duplicate_e2e_info = check_duplicate_end_to_end_id(xml_file)

    purpose_code_passed = len(purpose_code_errors) == 0
    utf8_encoding_passed = len(utf8_encoding_errors) == 0
    currency_code_passed = len(currency_code_errors) == 0
    duplicate_msgid_passed = len(duplicate_msgid_errors) == 0
    iban_passed = len(mod10_errors) == 0                 # <-- NEW
    mmbid_passed = len(mmbid_errors) == 0                 # <-- NEW
    country_code_passed = len(country_code_errors) == 0
    duplicate_e2e_passed = len(duplicate_e2e_errors) == 0

    # 4. Collect all errors together
    real_errors = (
        validation_errors +
        total_control_errors +
        mod10_errors +
        aba_errors +
        purpose_code_errors +
        utf8_encoding_errors +
        currency_code_errors +
        duplicate_msgid_errors +
        mmbid_errors +
        payment_date_errors +
        country_code_errors +
        duplicate_e2e_errors
    )
    
    # Sort errors by line number
    def extract_line_number(error):
        match = re.search(r"Line (\d+)", error)
        return int(match.group(1)) if match else 99999  # If no line info, push it last

    real_errors = sorted(real_errors, key=extract_line_number)

    # 5. Info messages (not real errors)
    info_messages = mod10_info + aba_info + mmbid_info + duplicate_e2e_info

    # 6. XML Diff (optional)
    differences = xmldiff.diff_files(reference_file, xml_file) if ENABLE_XML_DIFF and os.path.exists(reference_file) else []

    # 7. Build extra_info for console reporting
    extra_info = {
    "nboftxs_passed": nboftxs_passed,
    "ctrlsum_passed": ctrlsum_passed,
    "purpose_code_passed": purpose_code_passed,
    "utf8_encoding_passed": utf8_encoding_passed,
    "currency_code_passed": currency_code_passed,
    "duplicate_msgid_passed": duplicate_msgid_passed,
    "iban_passed": iban_passed,
    "mmbid_passed": mmbid_passed,
    "payment_date_results": payment_date_results,
    "country_code_passed": country_code_passed,
    "duplicate_e2e_passed": duplicate_e2e_passed,
    "info_messages": info_messages
    }

    return valid and not real_errors, real_errors, differences, extra_info




def write_individual_report(filename, version, ftype, passed, errors, diffs):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(filename)[0]
    report_path = os.path.join(REPORTS_DIR, f"{base_name}_{timestamp}_validation.csv")

    with open(report_path, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Version", "Type", "ValidationPassed", "Error/Diff Type", "Message"])

        # Main summary row
        writer.writerow([filename, version, ftype, passed, "", ""])

        # Write errors
        for e in errors:
            writer.writerow(["", "", "", "", "Error", e])

        # Write differences
        for d in diffs:
            writer.writerow(["", "", "", "", "Difference", d])

    logging.info(f"Report written: {report_path}")
    return report_path

# ======================
#         MAIN
# ======================
# results = []
# script_start_time = time.time()
# report_files = []
# skipped_files = []

# # Process CSV files
# for filename in os.listdir(CSV_DIR):
#     if filename.lower().endswith(".csv"):
#         start_time = time.time()
#         full_path = os.path.join(CSV_DIR, filename)
#         version = get_version_from_filename(filename) or prompt_for_version(filename)
#         if not version:
#             log_msg = f"⏭️ Skipped CSV file '{filename}' - Reason: Missing version detection."
#             logging.warning(log_msg)
#             skipped_files.append(log_msg)
#             continue
#         xml_generated = generate_xml_from_csv(full_path, version)
#         if xml_generated:
#             passed, errors, diffs, extra_info = validate_and_compare(xml_generated, version)
#             results.append([filename, version, "CSV", passed, errors, diffs, extra_info])
#             report_files.append(write_individual_report(filename, version, "CSV", passed, errors, diffs))
#             if not passed and ENABLE_HTML_ANNOTATION:
#                 try:
#                     html_gen_start = time.time()
#                     html_path = write_annotated_html(xml_generated, errors)
#                     html_gen_elapsed = time.time() - html_gen_start
#                     html_files_generated.append((filename, html_path, html_gen_elapsed))
#                     logging.info(f"Elapsed time for HTML annotation '{filename}': {html_gen_elapsed:.2f} seconds")
#                 except Exception as e:
#                     msg = f"⚠️ Failed to generate annotated HTML for '{filename}': {str(e)}"
#                     logging.warning(msg)
#                     html_files_generated.append((filename, msg, None))
#         elapsed = time.time() - start_time
#         logging.info(f"Elapsed time for '{filename}': {elapsed:.2f} seconds")
#     else:
#         log_msg = f"⏭️ Skipped CSV file '{filename}' - Reason: Unsupported file type."
#         logging.warning(log_msg)
#         skipped_files.append(log_msg)

# # Process XML files
# for filename in os.listdir(XML_DIR):
#     if filename.lower().endswith(".xml"):
#         start_time = time.time()
#         full_path = os.path.join(XML_DIR, filename)
#         version = get_version_from_xml(full_path) or prompt_for_version(filename)
#         if not version:
#             log_msg = f"⏭️ Skipped XML file '{filename}' - Reason: Missing version detection."
#             logging.warning(log_msg)
#             skipped_files.append(log_msg)
#             continue
#         passed, errors, diffs, extra_info = validate_and_compare(full_path, version)
#         results.append([filename, version, "XML", passed, errors, diffs, extra_info])
#         report_files.append(write_individual_report(filename, version, "XML", passed, errors, diffs))
#         if not passed and ENABLE_HTML_ANNOTATION:
#             try:
#                 html_gen_start = time.time()
#                 from io import StringIO

#                 summary_io = StringIO()
#                 status = "PASSED" if passed else "FAILED"
#                 summary_io.write(f"XML - {filename} - {version} - {status}\n")

#                 for e in errors:
#                     summary_io.write(f"    ⚠️  {e}\n")
#                 for msg in extra_info.get("info_messages", []):
#                     summary_io.write(f"    ℹ️  {msg}\n")

#                 # Add result checks
#                 log_check_result(summary_io, "NbOfTxs check", extra_info.get("nboftxs_passed"))
#                 log_check_result(summary_io, "CtrlSum check", extra_info.get("ctrlsum_passed"))
#                 log_check_result(summary_io, "Purpose Code check", extra_info.get("purpose_code_passed"))
#                 log_check_result(summary_io, "UTF-8 Encoding", extra_info.get("utf8_encoding_passed"))
#                 log_check_result(summary_io, "Currency Code check", extra_info.get("currency_code_passed"))
#                 log_check_result(summary_io, "Duplicate Message ID", extra_info.get("duplicate_msgid_passed"))
#                 log_check_result(summary_io, "IBAN checksum", extra_info.get("iban_passed"))
#                 log_check_result(summary_io, "MmbId check", extra_info.get("mmbid_passed"))
#                 log_check_result(summary_io, "Country Code check", extra_info.get("country_code_passed"))
#                 log_check_result(summary_io, "Duplicate EndToEndId inside file", extra_info.get("duplicate_e2e_passed"))

#                 for ptype, pval in extra_info.get("payment_date_results", {}).items():
#                     log_check_result(summary_io, f"Payment Date Check - {ptype} payments", pval)

#                 # ✨ NOW generate HTML
#                 summary_text = summary_io.getvalue()
#                 html_path = write_annotated_html(full_path, errors, summary_text)
#                 html_gen_elapsed = time.time() - html_gen_start
#                 html_files_generated.append((filename, html_path, html_gen_elapsed))
#                 logging.info(f"Elapsed time for HTML annotation '{filename}': {html_gen_elapsed:.2f} seconds")
#             except Exception as e:
#                 msg = f"⚠️ Failed to generate annotated HTML for '{filename}': {str(e)}"
#                 logging.warning(msg)
#                 html_files_generated.append((filename, msg, None))

#         elapsed = time.time() - start_time
#         logging.info(f"Elapsed time for '{filename}': {elapsed:.2f} seconds")
#     else:
#         log_msg = f"⏭️ Skipped XML file '{filename}' - Reason: Unsupported file type."
#         logging.warning(log_msg)
#         skipped_files.append(log_msg)

# # Write skipped files to .txt
# if SKIP_LOG_TO_TXT and skipped_files:
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     with open(f"skipped_files_{timestamp}.txt", "w", encoding="utf-8") as f:
#         for line in skipped_files:
#             f.write(line + "\n")

# # Write session summary to .txt
# if RUN_SESSION_LOG_TO_TXT:
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     with open(f"run_log_{timestamp}.txt", "w", encoding="utf-8") as f:
#         f.write("Validation Summary\n\n")
#         for result in results:
#             filename, version, ftype, passed, err, diffs, extra_info = result
#             status = "PASSED" if passed else "FAILED"
#             f.write(f"{ftype} - {filename} - {version} - {status}\n")

#             # Write errors
#             if err:
#                 f.write("  Errors:\n")
#                 for e in err:
#                     f.write(f"    ⚠️  {e}\n")
                    
#             # Write info messages
#             if extra_info.get("info_messages"):
#                 f.write("  Info Messages:\n")
#                 for msg in extra_info["info_messages"]:
#                     f.write(f"    ℹ️  {msg}\n")

#             # Write Extra Checks Pass/Fail
#             f.write("  Checks:\n")
#             log_check_result(f, "NbOfTxs check", extra_info.get("nboftxs_passed"))
#             log_check_result(f, "CtrlSum check", extra_info.get("ctrlsum_passed"))
#             log_check_result(f, "Purpose Code check", extra_info.get("purpose_code_passed"))
#             log_check_result(f, "UTF-8 Encoding", extra_info.get("utf8_encoding_passed"))
#             log_check_result(f, "Currency Code check", extra_info.get("currency_code_passed"))
#             log_check_result(f, "Duplicate Message ID", extra_info.get("duplicate_msgid_passed"))
#             log_check_result(f, "IBAN checksum", extra_info.get("iban_passed"))
#             log_check_result(f, "MmbId check", extra_info.get("mmbid_passed"))
#             log_check_result(f, "Country Code check", extra_info.get("country_code_passed"))
#             log_check_result(f, "Duplicate EndToEndId inside file", extra_info.get("duplicate_e2e_passed"))
#             # Write Payment Date Check results
#             if extra_info.get("payment_date_results"):
#                 for payment_type, passed in extra_info["payment_date_results"].items():
#                     log_check_result(f, f"Payment Date Check - {payment_type} payments", passed)

#             f.write("\n")  # blank line between files

#         if skipped_files:
#             f.write("\nSkipped Files:\n")
#             for line in skipped_files:
#                 f.write(f"{line}\n")

#         if html_files_generated:
#             f.write("\nAnnotated HTML Views (for failed files):\n")
#             for fname, html_result, elapsed in html_files_generated:
#                 if isinstance(html_result, str) and html_result.startswith("⚠️ Failed to generate"):
#                     f.write(f"  ❌ {fname} - {html_result}\n")
#                 else:
#                     if elapsed is not None:
#                         elapsed_str = f"{elapsed:.2f} sec" if elapsed is not None else "??? sec"
#                         f.write(f"  ✅ {fname} -> {html_result} ({elapsed_str})\n")
#                     else:
#                         logging.warning(f"Elapsed time missing for HTML annotation '{fname}' (logged in .txt)")
#                         f.write(f"  ✅ {fname} -> {html_result}\n")

        
        
        

# # Optionally zip all reports
# if ENABLE_ZIP_EXPORT:
#     zip_name = f"pain001_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
#     with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
#         for report_path in report_files:
#             arcname = os.path.basename(report_path)
#             zipf.write(report_path, arcname=arcname)
#             logging.info(f"Added to ZIP: {arcname}")
    
#     logging.info(f"Reports zipped to {zip_name}")

#     # Delete individual report files
#     for report_path in report_files:
#         try:
#             os.remove(report_path)
#             logging.info(f"Deleted report file: {report_path}")
#         except Exception as e:
#             logging.warning(f"Could not delete {report_path}: {e}")




# # Sort results by pass/fail
# results_sorted = sorted(results, key=lambda r: r[3])  # r[3] = passed

# # Count passed, failed, skipped
# passed_count = sum(1 for r in results if r[3])
# failed_count = sum(1 for r in results if not r[3])
# skipped_count = len(skipped_files)

# # Final Colored Console Summary
# print(f"\n{Style.BRIGHT}{Fore.CYAN}========== FINAL SUMMARY ==========\n")
# for filename, version, ftype, passed, err, diffs, extra_info in results_sorted:
#     status_color = Fore.GREEN if passed else Fore.RED
#     status_text = "PASSED" if passed else "FAILED"
#     print(f"{Style.BRIGHT}{Fore.BLUE}{ftype}{Style.RESET_ALL} - {Fore.YELLOW}{filename}{Style.RESET_ALL} - {Fore.MAGENTA}{version}{Style.RESET_ALL} - {status_color}{status_text}")

#     # Errors if any
#     if err:
#         for e in err:
#             print(f"{Fore.LIGHTYELLOW_EX}    ⚠️  {e}")

#     # Info messages (e.g., no IBANs, no 9-digit BICs)
#     if extra_info["info_messages"]:
#         for msg in extra_info["info_messages"]:
#             print(f"{Fore.LIGHTCYAN_EX}    ℹ️  {msg}")

#     # Always show CtrlSum / NbOfTxs status
#     log_check_result(None, "NbOfTxs check", extra_info.get("nboftxs_passed"))
#     log_check_result(None, "CtrlSum check", extra_info.get("ctrlsum_passed"))
#     log_check_result(None, "Purpose Code check", extra_info.get("purpose_code_passed"))
#     log_check_result(None, "UTF-8 Encoding", extra_info.get("utf8_encoding_passed"))
#     log_check_result(None, "Currency Code check", extra_info.get("currency_code_passed"))
#     log_check_result(None, "Duplicate Message ID", extra_info.get("duplicate_msgid_passed"))
#     log_check_result(None, "IBAN checksum", extra_info.get("iban_passed"))
#     log_check_result(None, "MmbId check", extra_info.get("mmbid_passed"))
#     log_check_result(None, "Country Code check", extra_info.get("country_code_passed"))
#     log_check_result(None, "Duplicate EndToEndId inside file", extra_info.get("duplicate_e2e_passed"))
#     # Show Payment Date Check results
#     if extra_info.get("payment_date_results"):
#         for payment_type, passed in extra_info["payment_date_results"].items():
#             log_check_result(None, f"Payment Date Check - {payment_type} payments", passed)

#     print()  # Blank line between files for better separation

# if html_files_generated:
#     print(f"\n{Style.BRIGHT}{Fore.CYAN}📝 Annotated HTML View Summary:")
#     for fname, html_result, elapsed in html_files_generated:
#         if isinstance(html_result, str) and html_result.startswith("⚠️ Failed to generate"):
#             print(f"{Fore.RED}    ❌ {fname} - {html_result}")
#         else:
#             if elapsed is not None:
#                 elapsed_str = f"{elapsed:.2f} sec" if elapsed is not None else "??? sec"
#                 print(f"{Fore.LIGHTYELLOW_EX}    ✅ {fname} → {html_result} ({elapsed_str})")
#             else:
#                 logging.warning(f"Elapsed time missing for HTML annotation '{fname}'")
#                 print(f"{Fore.LIGHTYELLOW_EX}    ✅ {fname} → {html_result}")

# if skipped_files:
#     print(f"\n{Style.BRIGHT}{Fore.YELLOW}⏭️  SKIPPED FILES:")
#     for line in skipped_files:
#         print(f"{Fore.LIGHTYELLOW_EX}    • {line}")

# print(f"\n{Style.BRIGHT}✔️ {Fore.GREEN}{passed_count} PASSED"
#       f"  ❌ {Fore.RED}{failed_count} FAILED"
#       f"  ⏭️ {Fore.YELLOW}{skipped_count} SKIPPED")

# # Total runtime from script start
# script_end_time = time.time()
# print(f"\n⏱️ Total Runtime: {Fore.CYAN}{script_end_time - script_start_time:.2f} seconds\n")

# logging.info(f"Validation complete. Reports {'zipped and deleted' if ENABLE_ZIP_EXPORT else 'saved'} in '{REPORTS_DIR}'")
