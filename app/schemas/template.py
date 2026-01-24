from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class TemplateBase(BaseModel):
    name: str
    image_name: str = Field(..., alias="imageName")
    category: Optional[str] = None
    container_disk_in_gb: int = Field(50, alias="containerDiskInGb")
    container_registry_auth_id: Optional[str] = Field(None, alias="containerRegistryAuthId")
    docker_entrypoint: List[str] = Field(default_factory=list, alias="dockerEntrypoint")
    docker_start_cmd: List[str] = Field(default_factory=list, alias="dockerStartCmd")
    env: Dict[str, str] = Field(default_factory=dict)
    ports: List[str] = Field(default_factory=list)  # For compatibility, unused
    readme: str = ""
    volume_in_gb: int = Field(20, alias="volumeInGb")  # Unused, for compatibility
    volume_mount_path: str = Field("/workspace", alias="volumeMountPath")  # Unused, for compatibility
    is_public: bool = Field(False, alias="isPublic")  # Unused, for compatibility
    is_serverless: bool = Field(True, alias="isServerless")  # Always True for now

    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    image_name: Optional[str] = Field(None, alias="imageName")
    category: Optional[str] = None
    container_disk_in_gb: Optional[int] = Field(None, alias="containerDiskInGb")
    container_registry_auth_id: Optional[str] = Field(None, alias="containerRegistryAuthId")
    docker_entrypoint: Optional[List[str]] = Field(None, alias="dockerEntrypoint")
    docker_start_cmd: Optional[List[str]] = Field(None, alias="dockerStartCmd")
    env: Optional[Dict[str, str]] = None
    ports: Optional[List[str]] = None
    readme: Optional[str] = None
    volume_in_gb: Optional[int] = Field(None, alias="volumeInGb")
    volume_mount_path: Optional[str] = Field(None, alias="volumeMountPath")
    is_public: Optional[bool] = Field(None, alias="isPublic")
    is_serverless: Optional[bool] = Field(None, alias="isServerless")

    class Config:
        populate_by_name = True


class TemplateResponse(BaseModel):
    id: str  # template_id
    name: str
    image_name: str = Field(..., alias="imageName")
    category: Optional[str] = None
    container_disk_in_gb: int = Field(..., alias="containerDiskInGb")
    container_registry_auth_id: Optional[str] = Field(None, alias="containerRegistryAuthId")
    docker_entrypoint: List[str] = Field(default_factory=list, alias="dockerEntrypoint")
    docker_start_cmd: List[str] = Field(default_factory=list, alias="dockerStartCmd")
    env: Dict[str, str] = Field(default_factory=dict)
    ports: List[str] = Field(default_factory=list)
    readme: str = ""
    volume_in_gb: int = Field(..., alias="volumeInGb")
    volume_mount_path: str = Field(..., alias="volumeMountPath")
    is_public: bool = Field(..., alias="isPublic")
    is_serverless: bool = Field(..., alias="isServerless")
    earned: int = 0
    runtime_in_min: int = Field(0, alias="runtimeInMin")
    is_runpod: bool = Field(False, alias="isRunpod")

    class Config:
        from_attributes = True
        populate_by_name = True

