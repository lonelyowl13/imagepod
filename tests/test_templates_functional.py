from copy import deepcopy
import requests
import pytest


@pytest.mark.functional
def test_create_template(base_url, tokens):
    
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


@pytest.mark.functional
def test_list_templates(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/templates/", headers=headers) 

    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


@pytest.fixture(scope="session")
def disposable_template(base_url, tokens):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/templates/", headers=headers) 

    assert r.status_code == 200, r.text
    assert len(r.json()) == 1

    return r.json()[0]


@pytest.mark.functional
def test_get_template_by_id(base_url, tokens, disposable_template):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.get(f"{base_url}/templates/{disposable_template["id"]}", headers=headers) 

    assert r.status_code == 200, r.text
    assert r.json()["id"] == disposable_template["id"]


@pytest.mark.functional
def test_update_template(base_url, tokens, disposable_template):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    body = deepcopy(disposable_template)

    body["env"]["ANOTHERKEY"] = 20

    r = requests.patch(f"{base_url}/templates/{disposable_template["id"]}", headers=headers, json=body) 

    assert r.status_code == 200, r.text

    j = r.json()

    assert r.status_code == 200, r.text
    assert "ANOTHERKEY" in j["env"].keys()

    r = requests.get(f"{base_url}/templates/{disposable_template["id"]}", headers=headers) 

    assert r.status_code == 200, r.text

    j = r.json()

    assert r.status_code == 200, r.text
    assert "ANOTHERKEY" in j["env"].keys()


@pytest.mark.functional
def test_delete_template(base_url, tokens, disposable_template):

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(f"{base_url}/templates/{disposable_template["id"]}", headers=headers) 

    assert r.status_code == 204, r.text


@pytest.mark.functional
def test_delete_template_bad(base_url, tokens):
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = requests.delete(f"{base_url}/templates/{1234}", headers=headers) 

    assert r.status_code == 404, r.text

