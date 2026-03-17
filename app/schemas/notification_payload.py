"""Executor notification payload schemas. Minimal fields necessary for executor actions."""

from typing import Dict, Any, List

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Job payloads
# --------------------------------------------------------------------------- #


class JobSubmittedPayload(BaseModel):
    id: int
    endpoint_id: int


class JobCanceledPayload(BaseModel):
    id: int
    endpoint_id: int


class JobTimedOutPayload(BaseModel):
    id: int
    endpoint_id: int


# --------------------------------------------------------------------------- #
# Endpoint payloads
# --------------------------------------------------------------------------- #


class EndpointTemplatePayload(BaseModel):
    image_name: str
    docker_entrypoint: List[str] = Field(default_factory=list)
    docker_start_cmd: List[str] = Field(default_factory=list)
    env: Dict[str, Any] = Field(default_factory=dict)


class MountedVolumePayload(BaseModel):
    volume_id: int
    name: str
    mount_path: str = "/runpod-volume"


class EndpointPayload(BaseModel):
    id: int
    execution_timeout_ms: int = 600000
    idle_timeout: int = 5
    env: Dict[str, Any] = Field(default_factory=dict)
    template: EndpointTemplatePayload
    volumes: List[MountedVolumePayload] = Field(default_factory=list)


class DeleteEndpointPayload(BaseModel):
    id: int


# --------------------------------------------------------------------------- #
# Pod payloads
# --------------------------------------------------------------------------- #


class PodTemplatePayload(BaseModel):
    image_name: str
    docker_entrypoint: List[str] = Field(default_factory=list)
    docker_start_cmd: List[str] = Field(default_factory=list)
    env: Dict[str, Any] = Field(default_factory=dict)


class PodTunnelPayload(BaseModel):
    port: int
    domain: str


class PodPayload(BaseModel):
    id: int
    executor_id: int
    env: Dict[str, Any] = Field(default_factory=dict)
    ports: List[int] = Field(default_factory=list)
    template: PodTemplatePayload
    tunnels: List[PodTunnelPayload] = Field(default_factory=list)
    volumes: List[MountedVolumePayload] = Field(default_factory=list)


class PodActionPayload(BaseModel):
    """For START_POD, STOP_POD, DELETE_POD."""
    id: int


# --------------------------------------------------------------------------- #
# Volume payloads
# --------------------------------------------------------------------------- #


class VolumePayload(BaseModel):
    id: int
    name: str


class MountVolumePayload(BaseModel):
    endpoint_id: int
    volume_id: int
    volume_name: str
    mount_path: str = "/runpod-volume"


class UnmountVolumePayload(BaseModel):
    endpoint_id: int
    volume_id: int


# --------------------------------------------------------------------------- #
# Payload builders (ORM -> dict for create_notification)
# --------------------------------------------------------------------------- #


def build_endpoint_payload(endpoint) -> dict:
    """Build EndpointPayload from endpoint ORM (with template and volume_mounts loaded)."""
    template = endpoint.template
    mounts = getattr(endpoint, "volume_mounts", None) or []
    return EndpointPayload(
        id=endpoint.id,
        execution_timeout_ms=endpoint.execution_timeout_ms,
        idle_timeout=endpoint.idle_timeout,
        env=endpoint.env or {},
        template=EndpointTemplatePayload(
            image_name=template.image_name,
            docker_entrypoint=template.docker_entrypoint or [],
            docker_start_cmd=template.docker_start_cmd or [],
            env=template.env or {},
        ),
        volumes=[
            MountedVolumePayload(
                volume_id=m.volume_id,
                name=m.volume.name,
                mount_path=m.mount_path,
            )
            for m in mounts
        ],
    ).model_dump(mode="json")


def build_pod_payload(pod) -> dict:
    """Build PodPayload from pod ORM (with template and tunnels loaded)."""
    template = pod.template
    tunnels = pod.tunnels or []
    return PodPayload(
        id=pod.id,
        executor_id=pod.executor.id,
        env=pod.env or {},
        ports=pod.ports or [],
        template=PodTemplatePayload(
            image_name=template.image_name,
            docker_entrypoint=template.docker_entrypoint or [],
            docker_start_cmd=template.docker_start_cmd or [],
            env=template.env or {},
        ),
        tunnels=[PodTunnelPayload(port=t.port, domain=t.domain) for t in tunnels],
    ).model_dump(mode="json")
