"""
WARNING: This script deletes large amounts of Salesforce data.
Intended ONLY for Developer Edition and this demo project.

It safely:
- Counts records in key objects
- Shows you what will be deleted
- Asks for confirmation
- Deletes in correct dependency order
"""

from salesforce.client.session import get_salesforce_client

DEPENDENCY_ORDER = [
    ("Opportunity", "SELECT Id FROM Opportunity"),
    ("Contact", "SELECT Id FROM Contact"),
    ("Account", "SELECT Id FROM Account"),
    ("Case", "SELECT Id FROM Case"),
    ("Campaign", "SELECT Id FROM Campaign"),
    ("Task", "SELECT Id FROM Task"),
    ("Event", "SELECT Id FROM Event"),
]

def main():
    sf = get_salesforce_client()

    print("Connected. Checking record counts...\n")

    counts = {}

    for obj, soql in DEPENDENCY_ORDER:
        try:
            result = sf.query_all(soql)
            ids = [r["Id"] for r in result.get("records", [])]
            counts[obj] = ids
            print(f"{obj}: {len(ids)} record(s)")
        except Exception as e:
            print(f"{obj}: error querying ({e})")

    print("\n--- SUMMARY ---")
    for obj, ids in counts.items():
        print(f"{obj}: {len(ids)} to delete")

    proceed = input("\nType 'DELETE' to confirm: ")
    if proceed.strip() != "DELETE":
        print("Aborted.")
        return

    print("\nDeleting records...")
    for obj, ids in counts.items():
        if not ids:
            continue
        print(f"Deleting from {obj}...")
        for Id in ids:
            try:
                getattr(sf, obj).delete(Id)
            except Exception as e:
                print(f"  Error deleting {Id}: {e}")

    print("\nCleanup completed.")

if __name__ == "__main__":
    main()
