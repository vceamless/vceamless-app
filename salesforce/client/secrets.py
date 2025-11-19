"""
Helpers for loading Salesforce credentials from AWS Secrets Manager.

Assumes a secret structure like:

  SecretId: dev/vceamless
  SecretString: {
    "slack": "{ ... }",
    "salesforce": "{ \"SF_USERNAME\": \"...\", ... }"
  }

The "salesforce" value is itself a JSON string containing the SF fields.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any

import boto3


# Default secret id + region can be overridden via env vars
DEFAULT_SECRET_ID = os.getenv("SF_SECRET_ID", "dev/vceamless")
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")


def _get_secretsmanager_client(region_name: str | None = None):
    return boto3.client("secretsmanager", region_name=region_name or DEFAULT_REGION)


def load_raw_secret(secret_id: str | None = None, region_name: str | None = None) -> Dict[str, Any]:
    """
    Fetch and parse the raw secret from AWS Secrets Manager.

    Returns the *outer* JSON dict. For dev/vceamless that looks like:
      { "slack": "<json-string>", "salesforce": "<json-string>" }
    """
    sid = secret_id or DEFAULT_SECRET_ID
    sm = _get_secretsmanager_client(region_name)

    resp = sm.get_secret_value(SecretId=sid)
    secret_string = resp.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {sid!r} does not contain a SecretString")

    try:
        outer = json.loads(secret_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Secret {sid!r} SecretString is not valid JSON") from e

    if not isinstance(outer, dict):
        raise ValueError(f"Secret {sid!r} SecretString must decode to a JSON object")

    return outer


def load_salesforce_raw(secret_id: str | None = None, region_name: str | None = None) -> Dict[str, Any]:
    """
    Return the inner Salesforce credential dict from the secret.

    If the outer secret has a "salesforce" key (stringified JSON), we parse that.
    If not, we assume the entire secret is already the SF dict.
    """
    outer = load_raw_secret(secret_id=secret_id, region_name=region_name)

    # Case 1: nested under "salesforce" as a JSON string
    if "salesforce" in outer:
        sf_raw = outer["salesforce"]
        if isinstance(sf_raw, str):
            try:
                sf_dict = json.loads(sf_raw)
            except json.JSONDecodeError as e:
                raise ValueError("The 'salesforce' value is not valid JSON") from e
        elif isinstance(sf_raw, dict):
            sf_dict = sf_raw
        else:
            raise ValueError("The 'salesforce' value must be a JSON string or object")
        return sf_dict

    # Case 2: entire secret is the Salesforce dict
    return outer


def get_salesforce_login_config(secret_id: str | None = None, region_name: str | None = None) -> Dict[str, Any]:
    """
    Normalize Salesforce credentials into a convenient config dict.

    Returns a dict with at least:
      - username
      - password
      - security_token
      - login_url
      - client_id
      - client_secret
      - instance_url (optional)
      - api_version (optional)
      - auth_method (optional)
    """
    sf = load_salesforce_raw(secret_id=secret_id, region_name=region_name)

    # These keys are based on your existing secret structure.
    return {
        "username": sf.get("SF_USERNAME"),
        "password": sf.get("SF_PASSWORD"),
        "security_token": sf.get("SF_SECURITY_TOKEN"),
        "login_url": sf.get("SF_LOGIN_URL", "https://login.salesforce.com"),
        "client_id": sf.get("SF_CLIENT_ID"),
        "client_secret": sf.get("SF_CLIENT_SECRET"),
        "instance_url": sf.get("SF_INSTANCE_URL"),
        "api_version": sf.get("SF_API_VERSION", "61.0"),
        "auth_method": sf.get("SF_AUTH_METHOD", "password"),
        "raw": sf,
    }
