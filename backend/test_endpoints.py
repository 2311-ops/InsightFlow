import sys
try:
    import requests
except ImportError:                       # <–– catch missing dependency
    print("Error: the `requests` library is not installed.")
    print("Run `python -m pip install requests` (use the same interpreter VS Code is using).")
    sys.exit(1)

import json
import os

# -----------------------------
# Config
# -----------------------------
BASE_URL = "http://localhost:5000"  
EMAIL = "testuser@example.com"
PASSWORD = "Password123!"
COMPANY_NAME = "Test Company"
DATASET_PATH = r"C:\Users\LOQ\Documents\Insightflow\backend\insightflow_test_sales.csv"

# -----------------------------
# Helper
# -----------------------------
def pretty_print(resp):
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

def main():
    # 1️⃣ Register
    print("1️⃣ Registering user...")
    resp = requests.post(f"{BASE_URL}/auth/register",
                         json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code == 400:
        print("User may already exist, skipping register")
    else:
        pretty_print(resp)

    # 2️⃣ Login
    print("\n2️⃣ Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login",
                         json={"email": EMAIL, "password": PASSWORD})
    resp.raise_for_status()
    data = resp.json()
    JWT = data["token"]
    headers = {"Authorization": f"Bearer {JWT}"}
    print("JWT acquired!")

    # 3️⃣ Create company
    print("\n3️⃣ Creating company...")
    resp = requests.post(f"{BASE_URL}/companies",
                         json={"name": COMPANY_NAME}, headers=headers)
    resp.raise_for_status()
    company = resp.json()
    COMPANY_ID = company.get("id", company.get("companyId", 1))
    pretty_print(company)

    # 4️⃣ List companies
    print("\n4️⃣ Listing companies...")
    resp = requests.get(f"{BASE_URL}/companies", headers=headers)
    pretty_print(resp)

    # 5️⃣ Upload dataset
    print("\n5️⃣ Uploading dataset...")
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset file {DATASET_PATH} not found")

    with open(DATASET_PATH, "rb") as f:              # <-- context manager
        files = {"file": f}
        data = {"companyId": COMPANY_ID}
        resp = requests.post(f"{BASE_URL}/datasets/upload",
                             headers=headers, files=files, data=data)
    resp.raise_for_status()
    dataset = resp.json()
    DATASET_ID = dataset.get("id", 1)
    pretty_print(dataset)

    # the remaining steps are unchanged…
    print("\n6️⃣ Listing datasets…")
    resp = requests.get(f"{BASE_URL}/datasets?companyId={COMPANY_ID}", headers=headers)
    pretty_print(resp)

    print("\n7️⃣ Fetching metrics…")
    resp = requests.get(f"{BASE_URL}/metrics?datasetId={DATASET_ID}", headers=headers)
    pretty_print(resp)

    print("\n8️⃣ Fetching metrics summary…")
    resp = requests.get(f"{BASE_URL}/metrics/summary?datasetId={DATASET_ID}", headers=headers)
    pretty_print(resp)

    print("\n9️⃣ Fetching insights…")
    resp = requests.get(f"{BASE_URL}/insights?datasetId={DATASET_ID}", headers=headers)
    pretty_print(resp)

    print("\n🔟 Asking AI question…")
    question_data = {"datasetId": DATASET_ID,
                     "question": "Why did revenue drop in February?"}
    resp = requests.post(f"{BASE_URL}/insights/ask",
                         headers=headers, json=question_data)
    pretty_print(resp)

    print("\n11️⃣ Regenerating insight…")
    resp = requests.post(f"{BASE_URL}/insights/regenerate",
                         headers=headers, json={"datasetId": DATASET_ID})
    pretty_print(resp)

    print("\n✅ All endpoints tested!")

if __name__ == "__main__":
    main()