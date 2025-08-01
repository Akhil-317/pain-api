import paramiko

def check_sftp_connection(host: str, port: int, username: str, 
                          auth_method: str, 
                          password: str = None, 
                          ssh_key_path: str = None) -> bool:
    """
    Check connection to an SFTP server.

    Args:
        host (str): SFTP server hostname or IP.
        port (int): Port number (default is usually 22).
        username (str): SFTP username.
        auth_method (str): Authentication method - 'password' or 'key'.
        password (str): Required if auth_method is 'password'.
        ssh_key_path (str): Required if auth_method is 'key'.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        transport = paramiko.Transport((host, port))

        if auth_method == 'password':
            if not password:
                raise ValueError("Password is required for password-based authentication.")
            transport.connect(username=username, password=password)

        elif auth_method == 'key':
            if not ssh_key_path:
                raise ValueError("SSH key path is required for key-based authentication.")
            private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
            transport.connect(username=username, pkey=private_key)

        else:
            raise ValueError("Invalid authentication method. Use 'password' or 'key'.")

        # Try to open an SFTP session
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.close()
        transport.close()
        print("✅ SFTP connection successful.")
        return True

    except Exception as e:
        print(f"❌ SFTP connection failed: {e}")
        return False



import requests

def check_api_connection(url: str,
                         auth_type: str,
                         token: str = None,
                         api_key: str = None,
                         api_key_header_name: str = "x-api-key",
                         custom_headers: dict = None,
                         ssl_enabled: bool = True) -> bool:
    """
    Checks connectivity to an API endpoint with specified auth type.

    Args:
        url (str): API endpoint.
        auth_type (str): One of 'OAuth2', 'API Key', or 'Other'.
        token (str): OAuth2 Bearer token (if auth_type is 'OAuth2').
        api_key (str): API Key value (if auth_type is 'API Key').
        api_key_header_name (str): Header name for API key. Default is 'x-api-key'.
        custom_headers (dict): Optional headers if using 'Other'.
        ssl_enabled (bool): Whether to verify SSL certificates.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    headers = {}

    try:
        if auth_type == "OAuth2":
            if not token:
                raise ValueError("OAuth2 selected but no token provided.")
            headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "API Key":
            if not api_key:
                raise ValueError("API Key selected but no key provided.")
            headers[api_key_header_name] = api_key

        elif auth_type == "Other":
            if custom_headers:
                headers.update(custom_headers)
            else:
                print("⚠️ No custom headers provided for 'Other' auth_type. Proceeding without auth.")

        else:
            raise ValueError("auth_type must be one of: 'OAuth2', 'API Key', 'Other'.")

        response = requests.get(url, headers=headers, verify=ssl_enabled, timeout=10)

        if 200 <= response.status_code < 300:
            print("✅ API connection successful.")
            return True
        else:
            print(f"❌ API responded with status code {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ API connection failed: {e}")
        return False

