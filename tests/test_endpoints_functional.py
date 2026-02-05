from copy import copy
import random
import requests
import pytest

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


@pytest.mark.functional 
def test_create_endpoint(base_url, tokens, template, executor):
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "execution_timeout_ms": 600000,
        "idle_timeout": 5,
        "name": "test endpoint",
        "template_id": template["id"],
        "vcpu_count": 2
    }

    r = requests.post(f"{base_url}/endpoints/", headers=headers, json=body)

    assert r.status_code == 200, r.text


@pytest.fixture(scope="session")
def endpoint(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/endpoints/", headers=headers)

    assert r.status_code == 200

    return r.json()[0]


@pytest.mark.functional
def test_update_endpoint(base_url, tokens, endpoint):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "version": 1,
        "compute_type": "GPU",
        "executor_id": endpoint["executor_id"],
        "execution_timeout_ms": endpoint["execution_timeout_ms"],
        "idle_timeout": endpoint["idle_timeout"],
        "name": "Updated Test Endpoint",
        "template_id": endpoint["template_id"],
        "vcpu_count": endpoint["vcpu_count"]
    }

    r = requests.patch(f"{base_url}/endpoints/{endpoint["id"]}", headers=headers, json=body)

    assert r.status_code == 200, r.text 
    assert r.json()["name"] == "Updated Test Endpoint"

@pytest.mark.functional
def test_delete_endpoint(base_url, tokens, endpoint):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(f"{base_url}/endpoints/{endpoint["id"]}", headers=headers)

    assert r.status_code == 200, r.text 
