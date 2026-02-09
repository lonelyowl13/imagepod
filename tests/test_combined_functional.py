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

    api_key = r.json()["api_key"]
    executor_id = r.json()["executor_id"]

    headers = {"Authorization": f"Bearer {r.json()['api_key']}"}

    body = {
        "gpu": "gtx 1060",
        "vram": 3221225472,
        "cpu": "xeon e5",
        "ram": 17179869184,
        "compute_type": "GPU",
        "cuda_version": "string",
        "metadata": {}
    }

    r = requests.post(f"{base_url}/executors/register", headers=headers, json=body)


    return {
        "api_key": api_key,
        "executor_id": executor_id,
    }

@pytest.mark.functional
def test_deploy_endpoint(base_url, tokens, executor, template):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = {
        "compute_type": "GPU",
        "executor_id": executor["executor_id"],
        "execution_timeout_ms": 600000,
        "idle_timeout": 5,
        "name": "TestEndpoint",
        "template_id": template["id"],
        "vcpu_count": 2
    }

    r = requests.post(f"{base_url}/endpoints", headers=headers, json=body)

    assert r.status_code == 200, r.text
    assert "id" in r.json().keys()
    assert r.json()["name"] == "TestEndpoint"
    assert r.json()["executor_id"] == executor["executor_id"]
    assert r.json()["template_id"] == template["id"]
    assert r.json()["compute_type"] == "GPU"
    assert r.json()["execution_timeout_ms"] == 600000
    assert r.json()["idle_timeout"] == 5
    assert r.json()["vcpu_count"] == 2


@pytest.mark.functional
def test_process_job(base_url, tokens, executor):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    executor_headers = {"Authorization": f"Bearer {executor["api_key"]}"}

    r = requests.get(f"{base_url}/endpoints", headers=headers)

    assert r.status_code == 200, r.text

    #got endpoint
    endpoint = r.json()[0]

    # set endpoint status to "ready"
    r = requests.patch(f"{base_url}/executors/endpoints/{endpoint["id"]}", headers=executor_headers, 
    json={"status": "READY"})

    assert r.status_code == 200, r.text

    job = {        
        "input": { "prompt": "pls gen an image" }
    }

    r = requests.post(f"{base_url}/jobs/{endpoint["id"]}/run", headers=headers, json=job)

    # got job
    assert r.status_code == 200, r.text
    job_response = r.json()
    assert "id" in job_response.keys(), job_response
    assert job_response["status"] == "IN_QUEUE", job_response

    # executor gets updates (jobs IN_QUEUE + endpoints Deploying)
    r = requests.get(f"{base_url}/executors/updates", headers=executor_headers, params={"timeout": 0})

    assert r.status_code == 200, r.text
    data = r.json()
    assert "jobs" in data and "endpoints" in data
    job = data["jobs"][0]

    body = {
        "delay_time": 123,
        "execution_time": 1234,
        "output_data": {
            "image": "https://images.com/123456.png"
        },
        "status": "COMPLETED"
    }

    # executor completed the job
    r = requests.patch(f"{base_url}/executors/job/{job["id"]}", headers=executor_headers, json=body)

    assert r.status_code == 200, r.text

    # user querying their job
    r = requests.get(f"{base_url}/jobs/{endpoint["id"]}/status/{job["id"]}", headers=headers)

    assert r.status_code == 200, r.text
    completed_job = r.json()

    assert completed_job["status"] == "COMPLETED", completed_job
    assert completed_job["delay_time"] == 123, completed_job
    assert completed_job["output"]["image"] == "https://images.com/123456.png", completed_job
    
