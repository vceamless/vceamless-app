"""
Session helpers for connecting to Salesforce using credentials from Secrets Manager.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from simple_salesforce import Salesforce
from .secrets import get_salesforce_login_config


def get_salesforce_client(
    env: str = "dev",
    secret_id: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Salesforce:
    """
    Instantiate a simple_salesforce.Salesforce client using credentials from Secrets Manager.

    Currently supports the 'password' auth method:
      - username
      - password
      - security_token
      - login_url (e.g. https://login.salesforce.com)
      - api_version (optional, defaults to 61.0)

    Parameters
    ----------
    env : str
        Logical environment name (currently unused, placeholder for future).
    secret_id : str, optional
        Override the default SecretId if needed (defaults to SF_SECRET_ID or dev/vceamless).
    region_name : str, optional
        AWS region for Secrets Manager (defaults to AWS_REGION or us-east-1).

    Returns
    -------
    Salesforce
        Authenticated Salesforce client.
    """
    cfg: Dict[str, Any] = get_salesforce_login_config(secret_id=secret_id, region_name=region_name)

    username = cfg.get("username")
    password = cfg.get("password")
    security_token = cfg.get("security_token")
    login_url = cfg.get("login_url") or "https://login.salesforce.com"
    api_version = cfg.get("api_version") or "61.0"
    auth_method = (cfg.get("auth_method") or "password").lower()

    if auth_method != "password":
        raise NotImplementedError(f"Auth method {auth_method!r} is not supported yet (password-only for now).")

    if not username or not password or not security_token:
        raise ValueError("Missing required Salesforce credentials (username/password/security_token).")

    # simple_salesforce expects domain='login' or 'test', not full URL, but we can derive it.
    domain = "login"
    if "test.salesforce.com" in login_url:
        domain = "test"

    sf = Salesforce(
        username=username,
        password=password,
        security_token=security_token,
        domain=domain,
        version=api_version,
    )
    return sf
