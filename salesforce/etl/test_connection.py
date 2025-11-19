"""
Quick connectivity test to the Salesforce dev org.

- Uses salesforce.client.session.get_salesforce_client()
- Runs small SOQL queries against Account and Contact
- Prints a few rows to verify that credentials and API access are working
"""

from __future__ import annotations

from typing import List, Dict, Any

from salesforce.client.session import get_salesforce_client

# --- New Constant Defined Here ---
# Define a module-level constant for the default number of sample records.
# This follows the Python convention of using ALL_CAPS for constants.
DEFAULT_RECORD_LIMIT = 25

# -----------------------------------


def summarize_records(records: List[Dict[str, Any]], fields: List[str], max_rows: int = DEFAULT_RECORD_LIMIT) -> None:
    """
    Prints a summary of the retrieved records up to max_rows.
    The default value now references the module-level constant.
    """
    for i, rec in enumerate(records[:max_rows], start=1):
        summary = ", ".join(f"{f}={rec.get(f)!r}" for f in fields)
        print(f"  [{i}] {summary}")


def main(record_limit: int = DEFAULT_RECORD_LIMIT):
    """
    The main function now accepts an optional record_limit argument
    that defaults to the module constant.
    """
    print("Creating Salesforce client...")
    sf = get_salesforce_client()

    print("Successfully connected. Running test queries...\n")
    print(f"Using a record limit of **{record_limit}** for all queries.")

    # Test 1: Accounts (companies)
    try:
        # --- SOQL query uses an f-string to insert the variable ---
        account_query = f"SELECT Id, Name FROM Account LIMIT {record_limit}"
        print(f"Running Account query: {account_query}")
        result = sf.query(account_query)
        records = result.get("records", [])
        print(f"Retrieved {len(records)} Account record(s).")
        # --- Pass the limit to summarize_records to ensure consistency ---
        summarize_records(records, ["Id", "Name"], max_rows=record_limit)
        print()
    except Exception as e:
        print(f"[ERROR] Failed to query Account: {e}")

    # Test 2: Contacts (people)
    try:
        # --- SOQL query uses an f-string to insert the variable ---
        contact_query = f"SELECT Id, FirstName, LastName, Name FROM Contact LIMIT {record_limit}"
        print(f"Running Contact query: {contact_query}")
        result = sf.query(contact_query)
        records = result.get("records", [])
        print(f"Retrieved {len(records)} Contact record(s).")
        # --- Pass the limit to summarize_records to ensure consistency ---
        summarize_records(records, ["Id", "FirstName", "LastName", "Name"], max_rows=record_limit)
        print()
    except Exception as e:
        print(f"[ERROR] Failed to query Contact: {e}")

    print("Test connection script completed.")


if __name__ == "__main__":
    # To customize the limit when running the script:
    # main(record_limit={user defined limit}) 
    main()