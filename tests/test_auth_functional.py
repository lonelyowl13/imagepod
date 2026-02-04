import requests
import pytest


@pytest.mark.functional
def test_register(base_url, test_user):

    r = requests.post(f"{base_url}/auth/register", json={
        "username": test_user["username"],
        "password": test_user["password"],
        "password2": test_user["password"],
    })

    assert r.status_code in (200,), r.text


@pytest.mark.functional
def test_register_username_exists(base_url, test_user):
    r = requests.post(f"{base_url}/auth/register", json={
        "username": test_user["username"],
        "password": test_user["password"],
        "password2": test_user["password"],
    })

    assert r.status_code in (400,), r.text

@pytest.mark.functional
def test_register_passwords_dont_match(base_url, test_user):
    r = requests.post(f"{base_url}/auth/register", json={
        "username": test_user["username"] + "123",
        "password": test_user["password"],
        "password2": test_user["password"] + "123456",
    })

    assert r.status_code in (422,), r.text

@pytest.mark.functional
def test_login_wrong_user(base_url):

    r = requests.post(f"{base_url}/auth/login", json={
        "username": "nonsense",
        "password": "nonsense",
    })

    assert r.status_code in (401,), r.text

    assert "access_token" not in r.json().keys()


@pytest.mark.functional
def test_login_wrong_password(base_url, test_user):

    r = requests.post(f"{base_url}/auth/login", json={
        "username": test_user["username"],
        "password": "nonsense",
    })

    assert r.status_code in (401,), r.text

    assert "access_token" not in r.json().keys()


@pytest.mark.functional
def test_login(base_url, test_user):

    r = requests.post(f"{base_url}/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"],
    })

    assert r.status_code in (200,), r.text

    assert "access_token" in r.json().keys(), r.text
    assert "refresh_token" in r.json().keys(), r.text


@pytest.mark.functional
def test_refresh(base_url, tokens):

    r = requests.post(f"{base_url}/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })

    assert r.status_code == 200, r.text


@pytest.mark.functional
def test_refresh_bad_token(base_url, tokens):

    r = requests.post(f"{base_url}/auth/refresh", json={
        "refresh_token": tokens["refresh_token"] + "123",
    })

    assert r.status_code == 401, r.text


@pytest.fixture(scope="session")
def api_key(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/auth/key", headers=headers)

    assert r.status_code == 200, r.text
    assert "api_key" in r.json().keys()

    j = r.json()

    return {
        "id": j["id"],
        "api_key": j["api_key"],
    }


@pytest.mark.functional 
def test_get_keys(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/auth/keys", headers=headers)

    assert r.status_code == 200, r.text
    assert "keys" in r.json().keys(), r.json()
    assert len(r.json()["keys"]) == 0, r.json()


@pytest.mark.functional
def test_key_auth(base_url, api_key):
    # let's use the same keys endpoint since it allow authentication by key
    headers = {"Authorization": f"Bearer {api_key['api_key']}"}

    r = requests.get(f"{base_url}/auth/keys", headers=headers)

    assert r.status_code == 200, r.text
    assert "keys" in r.json().keys(), r.json()
    assert len(r.json()["keys"]) == 1, r.json()


@pytest.mark.functional
def test_key_auth_fail(base_url, api_key):
    headers = {"Authorization": f"Bearer {api_key['api_key'] + "123456"}"}

    r = requests.get(f"{base_url}/auth/keys", headers=headers)

    assert r.status_code == 401, r.text
    assert "keys" not in r.json().keys(), r.json()


@pytest.mark.functional
def test_delete_key(base_url, api_key):
    headers = {"Authorization": f"Bearer {api_key['api_key']}"}

    r = requests.delete(f"{base_url}/auth/key/{api_key["id"]}", headers=headers)

    assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/auth/keys", headers=headers)

    # key deleted - 401
    assert r.status_code == 401, r.text
