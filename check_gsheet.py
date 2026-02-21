"""Google Sheets 연결 진단"""
import json
import requests
from google.oauth2.service_account import Credentials
import google.auth.transport.requests

SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_ID = "1NEsimkXycdXQCz4g0cr31j93MGI7HKNDeoiJO4HjgOw"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

try:
    with open(SERVICE_ACCOUNT_FILE) as f:
        sa_info = json.load(f)
    print(f"서비스 계정: {sa_info.get('client_email')}")

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    token = creds.token

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    data = resp.json()

    if resp.status_code == 200:
        title = data.get("properties", {}).get("title")
        sheets = [s["properties"]["title"] for s in data.get("sheets", [])]
        print(f"✅ 접근 성공! 시트명: '{title}'")
        print(f"   탭 목록: {sheets}")
    else:
        error = data.get("error", {})
        print(f"❌ {error.get('code')}: {error.get('message')}")

except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")
