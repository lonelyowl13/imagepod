import random
import requests
import pytest


@pytest.fixture(scope="session")
def test_user():
    username = f"testuser{random.randint(0, 99999)}"
    password = "supersecretpassword123456"
    return {"username": username, "password": password}


@pytest.fixture(scope="session")
def tokens(base_url, test_user):
    """Register + login, return access and refresh tokens."""
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
def second_user(base_url):
    """A second user for sharing tests."""
    username = f"shareuser{random.randint(0, 99999)}"
    password = "supersecretpassword123456"

    r = requests.post(f"{base_url}/auth/register", json={
        "username": username,
        "password": password,
        "password2": password,
    })

    assert r.status_code in (200, 201, 400), r.text

    r = requests.post(f"{base_url}/auth/login", json={
        "username": username,
        "password": password,
    })

    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "username": username,
        "password": password,
        "access_token": data["access_token"],
    }


@pytest.fixture(scope="session")
def executor(base_url, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/executors/add", headers=headers, json={
        "name": "Executor For Sharing",
    })

    assert r.status_code == 200, r.text
    j = r.json()
    assert "api_key" in j and "executor_id" in j

    return {
        "api_key": j["api_key"],
        "executor_id": j["executor_id"],
    }


@pytest.mark.functional
def test_list_executors(base_url, tokens, executor):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/executors/", headers=headers)

    assert r.status_code == 200, r.text
    executors = r.json()
    assert isinstance(executors, list)
    assert any(e["id"] == executor["executor_id"] for e in executors)


@pytest.mark.functional
def test_share_executor(base_url, tokens, executor, second_user):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(
        f"{base_url}/executors/{executor['executor_id']}/share",
        headers=headers,
        json={"username": second_user["username"]},
    )

    assert r.status_code == 200, r.text
    j = r.json()
    assert j["executor_id"] == executor["executor_id"]
    assert j["username"] == second_user["username"]


@pytest.mark.functional
def test_list_shares(base_url, tokens, executor, second_user):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(
        f"{base_url}/executors/{executor['executor_id']}/shares",
        headers=headers,
    )

    assert r.status_code == 200, r.text
    shares = r.json()
    assert any(s["username"] == second_user["username"] for s in shares)


@pytest.mark.functional
def test_shared_executor_visible_to_target(base_url, executor, second_user):
    """The second user should see the shared executor in their list."""

    headers = {"Authorization": f"Bearer {second_user['access_token']}"}

    r = requests.get(f"{base_url}/executors/", headers=headers)

    assert r.status_code == 200, r.text
    executors = r.json()
    match = [e for e in executors if e["id"] == executor["executor_id"]]
    assert len(match) == 1
    assert match[0]["is_shared"] is True


@pytest.mark.functional
def test_unshare_executor(base_url, tokens, executor, second_user):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(
        f"{base_url}/executors/{executor['executor_id']}/share/{second_user['username']}",
        headers=headers,
    )

    assert r.status_code == 200, r.text

    r = requests.get(
        f"{base_url}/executors/{executor['executor_id']}/shares",
        headers=headers,
    )

    assert r.status_code == 200, r.text
    shares = r.json()
    assert not any(s["username"] == second_user["username"] for s in shares)
