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
def executor(base_url, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/executors/add", headers=headers, json={
        "name": "Volume Test Executor",
    })

    assert r.status_code == 200, r.text
    j = r.json()
    return {
        "api_key": j["api_key"],
        "executor_id": j["executor_id"],
    }


@pytest.fixture(scope="session")
def template(base_url, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/templates/", headers=headers, json={
        "name": "volume_test_template",
        "image_name": "nvidia/cuda",
        "docker_entrypoint": ["python3 main.py"],
        "docker_start_cmd": ["--serve"],
        "env": {"KEY": "val"},
    })

    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def endpoint(base_url, tokens, template, executor):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/endpoints/", headers=headers, json={
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "execution_timeout_ms": 600000,
        "idle_timeout": 5,
        "name": "VolumeTestEndpoint",
        "template_id": template["id"],
        "vcpu_count": 2,
    })

    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.functional
def test_create_volume(base_url, tokens, executor):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/volumes/", headers=headers, json={
        "name": "test-volume",
        "executor_id": executor["executor_id"],
        "size_gb": 10,
    })

    assert r.status_code == 201, r.text
    j = r.json()
    assert "id" in j
    assert j["name"] == "test-volume"
    assert j["executor_id"] == executor["executor_id"]
    assert j["size_gb"] == 10


@pytest.fixture(scope="session")
def volume(base_url, tokens, executor):
    """Create and return a volume for subsequent tests."""
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/volumes/", headers=headers, json={
        "name": "fixture-volume",
        "executor_id": executor["executor_id"],
        "size_gb": 20,
    })

    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.functional
def test_list_volumes(base_url, tokens, volume):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/volumes/", headers=headers)

    assert r.status_code == 200, r.text
    volumes = r.json()
    assert isinstance(volumes, list)
    assert any(v["id"] == volume["id"] for v in volumes)


@pytest.mark.functional
def test_get_volume(base_url, tokens, volume):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/volumes/{volume['id']}", headers=headers)

    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == volume["id"]
    assert j["name"] == "fixture-volume"


@pytest.mark.functional
def test_update_volume(base_url, tokens, volume):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.patch(f"{base_url}/volumes/{volume['id']}", headers=headers, json={
        "name": "renamed-volume",
        "size_gb": 50,
    })

    assert r.status_code == 200, r.text
    j = r.json()
    assert j["name"] == "renamed-volume"
    assert j["size_gb"] == 50


@pytest.mark.functional
def test_mount_volume(base_url, tokens, volume, endpoint):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/volumes/mount/{endpoint['id']}", headers=headers, json={
        "volume_id": volume["id"],
        "mount_path": "/data",
    })

    assert r.status_code == 200, r.text
    j = r.json()
    assert j["volume_id"] == volume["id"]
    assert j["endpoint_id"] == endpoint["id"]
    assert j["mount_path"] == "/data"


@pytest.mark.functional
def test_list_mounts(base_url, tokens, volume, endpoint):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/volumes/mounts/{endpoint['id']}", headers=headers)

    assert r.status_code == 200, r.text
    mounts = r.json()
    assert isinstance(mounts, list)
    assert any(m["volume_id"] == volume["id"] for m in mounts)


@pytest.mark.functional
def test_unmount_volume(base_url, tokens, volume, endpoint):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(
        f"{base_url}/volumes/mount/{endpoint['id']}/{volume['id']}",
        headers=headers,
    )

    assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/volumes/mounts/{endpoint['id']}", headers=headers)

    assert r.status_code == 200, r.text
    mounts = r.json()
    assert not any(m["volume_id"] == volume["id"] for m in mounts)


@pytest.mark.functional
def test_delete_volume(base_url, tokens, volume):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(f"{base_url}/volumes/{volume['id']}", headers=headers)

    assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/volumes/{volume['id']}", headers=headers)

    assert r.status_code == 404, r.text
