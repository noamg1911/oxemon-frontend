import requests
import time
import json
import re

GRAFANA_URL = "http://grafana:3000"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"
SERVICE_ACCOUNT_NAME = "my-service-account"
TOKEN_NAME = "my-service-token"

auth = (ADMIN_USER, ADMIN_PASSWORD)
headers = {"Content-Type": "application/json"}

def wait_for_grafana():
    print("Waiting for Grafana to be ready...")
    while True:
        try:
            r = requests.get(f"{GRAFANA_URL}/api/health", auth=auth)
            if r.status_code == 200 and r.json().get("database") == "ok":
                break
        except Exception:
            pass
        time.sleep(2)


def get_service_account_id_by_name(name):
    response = requests.get(f"{GRAFANA_URL}/api/serviceaccounts/search?perpage=10&page=1&query={SERVICE_ACCOUNT_NAME}", auth=auth)
    if response.status_code != 200:
        raise RuntimeError("Failed to fetch existing SA's id")
    
    content = response.json()
    assert content["totalCount"] > 0
    return content["serviceAccounts"][0]["id"]


def delete_existing_tokens(service_account_id):
    response = requests.get(f"{GRAFANA_URL}/api/serviceaccounts/{service_account_id}/tokens", auth=auth)
    assert response.status_code == 200
    content = response.json()

    print(content)

    for token in content:
        response = requests.delete(f"{GRAFANA_URL}/api/serviceaccounts/{service_account_id}/tokens/{token['id']}", auth=auth)
        assert response.status_code == 200


def create_service_account():
    payload = {
        "name": SERVICE_ACCOUNT_NAME,
        "role": "Admin"
    }
    response = requests.post(
        f"{GRAFANA_URL}/api/serviceaccounts", auth=auth, headers=headers, json=payload
    )

    # Success
    if response.status_code in (200, 201):
        return response.json()["id"]

    # Already exists
    elif response.status_code == 400 and "serviceaccounts.ErrAlreadyExists" in response.text:
        print("Service account already exists")

        return get_service_account_id_by_name(SERVICE_ACCOUNT_NAME)
    
    # Unknown error
    else:
        print("Failed to create service account.")
        print(response.status_code, response.text)
        exit(1)    


def create_token(service_account_id):
    print("Creating token...")
    payload = {
        "name": TOKEN_NAME,
        "seconds": 315360000  # 10 years
    }
    response = requests.post(
        f"{GRAFANA_URL}/api/serviceaccounts/{service_account_id}/tokens",
        auth=auth,
        headers=headers,
        json=payload
    )
    if response.status_code in (200, 201):
        api_token = response.json()["key"]
        return api_token
    elif response.status_code == 400 and "serviceaccounts.ErrTokenAlreadyExists" in response.text:
        delete_existing_tokens(service_account_id)
        return create_token(service_account_id)
    else:
        print("Failed to create token.")
        print(response.status_code, response.text)
        exit(1)


def create_grafana_api_key():
    wait_for_grafana()
    sa_id = create_service_account()
    return create_token(sa_id)
