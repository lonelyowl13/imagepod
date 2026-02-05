import random
import pytest 
import requests

@pytest.fixture(scope="session")
def test_user():
    # random username
    username = f"testuser{random.randint(0, 99999)}"
    password = "supersecretpassword123456"
    return {"username": username, "password": password}


@pytest.fixture(scope="session")
def tokens(base_url, test_user):
    """ a fixture to get tokens """
    r = requests.post(f"{base_url}/auth/register", json={
        "username": test_user["username"],
        "password": test_user["password"],
        "password2": test_user["password"],
    })

    assert r.status_code in (200, 201, 400), r.text

    r = requests.post(f"{base_url}/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"],
    })

    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


@pytest.fixture(scope="session")
def template(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/templates/", headers=headers, 
    json={
        "name": "test_template",
        "image_name": "nvidia/cuda",
        "docker_entrypoint": [
            "python3 main.py"
        ],
        "docker_start_cmd": [
            "--arg1 a --arg2 b"
        ],
        "env": {
            "SOME_KEY": "123"
        }
    })

    assert r.status_code == 200, r.text

    j = r.json()
    assert "id" in j.keys()
    assert j["name"] == "test_template"

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/templates/", headers=headers) 

    assert r.status_code == 200, r.text

    return r.json()[0]


@pytest.fixture(scope="session")
def executor(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "name": "Test Executor"
    }

    r = requests.post(f"{base_url}/executors/add", headers=headers, json=body)

    assert r.status_code == 200, r.text
    assert "api_key" in r.json().keys() and "executor_id" in r.json().keys()

    return {
        "api_key": r.json()["api_key"],
        "executor_id": r.json()["executor_id"]
    }
