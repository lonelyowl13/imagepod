from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    image_name: str
    docker_entrypoint: Optional[List[str]] = None
    docker_start_cmd: Optional[List[str]] = None
    env: Optional[Dict[str, Any]] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    image_name: Optional[str] = None
    docker_entrypoint: Optional[List[str]] = None
    docker_start_cmd: Optional[List[str]] = None
    env: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    image_name: str
    docker_entrypoint: List[str]
    docker_start_cmd: List[str]
    env: Dict[str, Any]

    class Config:
        from_attributes = True
