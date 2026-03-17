import random
import pytest
import requests


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
def pod_template(base_url, tokens):
    """Create a non-serverless template for pods."""
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/templates/", headers=headers, json={
        "name": "pod_template",
        "image_name": "nvidia/cuda",
        "docker_entrypoint": ["python3 main.py"],
        "docker_start_cmd": ["--serve"],
        "env": {"KEY": "val"},
        "is_serverless": False,
    })

    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def executor(base_url, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/executors/add", headers=headers, json={
        "name": "Pod Test Executor",
    })
    assert r.status_code == 200, r.text
    j = r.json()
    api_key = j["api_key"]
    executor_id = j["executor_id"]

    # Register executor with fake specs so compute_type etc. are set (required for pods/endpoints)
    r = requests.post(
        f"{base_url}/executors/register",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "gpu": "Test GPU",
            "vram": 3221225472,
            "cpu": "Test CPU",
            "ram": 17179869184,
            "compute_type": "GPU",
            "cuda_version": "12.0",
            "metadata": {},
        },
    )
    assert r.status_code == 200, r.text

    return {"api_key": api_key, "executor_id": executor_id}


@pytest.mark.functional
def test_create_pod(base_url, tokens, pod_template, executor):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "name": "TestPod",
        "template_id": pod_template["id"],
        "vcpu_count": 2,
        "ports": [8080],
    }

    r = requests.post(f"{base_url}/pods/", headers=headers, json=body)

    assert r.status_code == 200, r.text
    j = r.json()
    assert j["name"] == "TestPod"
    assert j["template"]["id"] == pod_template["id"]
    assert j["executor"]["id"] == executor["executor_id"]
    assert j["ports"] == [8080]
    assert j["status"] in ("STOPPED", "RUNNING")


@pytest.fixture(scope="session")
def pod(base_url, tokens, pod_template, executor):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    body = {
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "name": "FixturePod",
        "template_id": pod_template["id"],
        "vcpu_count": 2,
        "ports": [8081],
    }
    r = requests.post(f"{base_url}/pods/", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.functional
def test_list_pods(base_url, tokens, pod):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = requests.get(f"{base_url}/pods/", headers=headers)
    assert r.status_code == 200, r.text
    pods = r.json()
    assert isinstance(pods, list)
    assert any(p["id"] == pod["id"] for p in pods)


@pytest.mark.functional
def test_get_pod(base_url, tokens, pod):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = requests.get(f"{base_url}/pods/{pod['id']}", headers=headers)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == pod["id"]


@pytest.mark.functional
def test_update_pod_emits_update_notification(base_url, tokens, pod, executor):
    """Patching a pod should emit UPDATE_POD notification to the executor."""
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    executor_headers = {"Authorization": f"Bearer {executor['api_key']}"}

    r = requests.patch(
        f"{base_url}/pods/{pod['id']}",
        headers=headers,
        json={"name": "UpdatedFixturePod"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "UpdatedFixturePod"

    r = requests.get(f"{base_url}/executors/updates", headers=executor_headers, params={"timeout": 0})
    assert r.status_code == 200, r.text
    data = r.json()
    update_notifications = [
        n for n in data["notifications"]
        if n.get("entity_kind") == "POD" and n.get("type") == "UPDATE_POD" and n.get("entity_id") == pod["id"]
    ]
    assert len(update_notifications) >= 1, "executor should have received UPDATE_POD notification for pod patch"


@pytest.mark.functional
def test_start_stop_pod(base_url, tokens, pod):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.post(f"{base_url}/pods/{pod['id']}/start", headers=headers)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == pod["id"]

    r = requests.post(f"{base_url}/pods/{pod['id']}/stop", headers=headers)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == pod["id"]


@pytest.mark.functional
def test_delete_pod(base_url, tokens, pod):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(f"{base_url}/pods/{pod['id']}", headers=headers)
    assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/pods/{pod['id']}", headers=headers)
    assert r.status_code == 404, r.text


@pytest.mark.functional
def test_endpoint_rejects_pod_template(base_url, tokens, pod_template, executor):
    """Ensure endpoints cannot be created from non-serverless templates."""
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "execution_timeout_ms": 600000,
        "idle_timeout": 5,
        "name": "BadEndpointFromPodTemplate",
        "template_id": pod_template["id"],
        "vcpu_count": 2,
    }

    r = requests.post(f"{base_url}/endpoints/", headers=headers, json=body)
    assert r.status_code == 400, r.text

