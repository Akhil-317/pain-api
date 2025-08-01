from lxml import etree

def validate(xml_file_path, xsd_file_path):
    """
    Validate an XML file against a given XSD schema.

    Returns:
        (bool, list[str]) → (is_valid, list_of_errors)
    """
    try:
        # Load schema
        with open(xsd_file_path, 'rb') as xsd_file:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)

        # Load XML
        with open(xml_file_path, 'rb') as xml_file:
            xml_doc = etree.parse(xml_file)

        # Validate
        is_valid = xmlschema.validate(xml_doc)
        errors = [str(error) for error in xmlschema.error_log]

        return is_valid, errors

    except Exception as e:
        return False, [f"Exception during validation: {e}"]
