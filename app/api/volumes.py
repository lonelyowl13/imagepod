from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import get_current_active_user
from app.models.user import User
from app.schemas.volume import (
    VolumeCreate,
    VolumeUpdate,
    VolumeResponse,
    VolumeMountRequest,
    VolumeMountResponse,
)
from app.services.volume_service import (
    create_volume as svc_create,
    get_volume,
    get_user_volumes,
    update_volume,
    delete_volume,
    mount_volume,
    unmount_volume,
    get_mounts_for_endpoint,
)

router = APIRouter(prefix="/volumes", tags=["volumes"])


@router.post("/", response_model=VolumeResponse, status_code=status.HTTP_201_CREATED)
async def create_volume_route(
    data: VolumeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new volume on a specific executor."""
    try:
        volume = svc_create(db, current_user.id, data)
        return volume
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[VolumeResponse])
async def list_volumes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all volumes owned by the current user."""
    return get_user_volumes(db, current_user.id)


@router.get("/{volume_id}", response_model=VolumeResponse)
async def get_volume_route(
    volume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific volume."""
    volume = get_volume(db, volume_id, current_user.id)
    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")
    return volume


@router.patch("/{volume_id}", response_model=VolumeResponse)
async def update_volume_route(
    volume_id: int,
    data: VolumeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a volume's metadata."""
    updated = update_volume(db, volume_id, current_user.id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Volume not found")
    return updated


@router.delete("/{volume_id}", status_code=status.HTTP_200_OK)
async def delete_volume_route(
    volume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a volume. Removes all associated mounts."""
    if not delete_volume(db, volume_id, current_user.id):
        raise HTTPException(status_code=404, detail="Volume not found")
    return {"message": "Volume deleted successfully"}


@router.post("/mount/{endpoint_id}", response_model=VolumeMountResponse)
async def mount_volume_route(
    endpoint_id: int,
    body: VolumeMountRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mount a volume to an endpoint. Both must share the same executor."""
    try:
        ev = mount_volume(db, current_user.id, endpoint_id, body.volume_id, body.mount_path)
        ev_with_vol = get_mounts_for_endpoint(db, endpoint_id)
        matched = next((m for m in ev_with_vol if m.id == ev.id), ev)
        return matched
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/mount/{endpoint_id}/{volume_id}", status_code=status.HTTP_200_OK)
async def unmount_volume_route(
    endpoint_id: int,
    volume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Unmount a volume from an endpoint."""
    if not unmount_volume(db, current_user.id, endpoint_id, volume_id):
        raise HTTPException(status_code=404, detail="Mount not found")
    return {"message": "Volume unmounted successfully"}


@router.get("/mounts/{endpoint_id}", response_model=List[VolumeMountResponse])
async def list_mounts_route(
    endpoint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all volumes mounted to an endpoint."""
    return get_mounts_for_endpoint(db, endpoint_id)
