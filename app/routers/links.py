from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app import crud, schemas, models
from app.auth import get_current_user, require_current_user
from app.database import get_db
from app.cache import (
    cache_get_url, cache_set_url, cache_invalidate,
    cache_get_stats, cache_set_stats, cache_invalidate_stats
)

router = APIRouter(tags=["Ссылки"])


@router.post("/links/shorten", response_model=schemas.LinkResponse, status_code=201)
async def shorten_link(
    link_data: schemas.LinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user)
):
    try:
        owner_id = current_user.id if current_user else None
        link = await crud.create_link(db, link_data, owner_id)
        await cache_set_url(link.short_code, link.original_url)
        return link
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/links/search", response_model=schemas.LinkResponse)
async def search_link(
    original_url: str = Query(..., description="Оригинальный URL для поиска"),
    db: AsyncSession = Depends(get_db)
):
    link = await crud.get_link_by_original_url(db, original_url)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


@router.get("/links/expired", response_model=list[schemas.ExpiredLinkResponse])
async def get_expired_links(db: AsyncSession = Depends(get_db)):
    return await crud.get_expired_links(db)


@router.get("/links/{short_code}/stats", response_model=schemas.LinkStats)
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    cached = await cache_get_stats(short_code)
    if cached:
        return cached

    link = await crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    stats = schemas.LinkStats.model_validate(link)
    await cache_set_stats(short_code, stats.model_dump())
    return stats


@router.delete("/links/{short_code}", status_code=204)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_current_user)
):
    link = await crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    old_code = link.short_code
    await crud.delete_link(db, link)
    await cache_invalidate(old_code)
    await cache_invalidate_stats(old_code)


@router.put("/links/{short_code}", response_model=schemas.LinkResponse)
async def update_link(
    short_code: str,
    update_data: schemas.LinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_current_user)
):
    link = await crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    old_code = link.short_code
    try:
        updated = await crud.update_link(db, link, update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await cache_invalidate(old_code)
    await cache_invalidate_stats(old_code)
    await cache_set_url(updated.short_code, updated.original_url)
    return updated


@router.post("/links/admin/cleanup", status_code=200)
async def cleanup_expired(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_current_user)
):
    count = await crud.archive_and_delete_expired(db)
    return {"message": f"Archived and deleted links: {count}"}


@router.put("/links/admin/unused-days", status_code=200)
async def set_unused_days(
    days: int = Query(..., ge=1, description="Через сколько дней удалять неиспользуемые ссылки"),
    current_user: models.User = Depends(require_current_user)
):
    await crud.set_unused_days(days)
    return {"message": f"Settings updated: links will be deleted after {days} days of inactivity"}


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, db: AsyncSession = Depends(get_db)):
    # cached_url = await cache_get_url(short_code)
    # if cached_url:
    #     link = await crud.get_link_by_short_code(db, short_code)
    #     if link:
    #         await crud.increment_click(db, link)
    #         await cache_invalidate_stats(short_code)
    #     return RedirectResponse(url=cached_url, status_code=307)
    cached_url = await cache_get_url(short_code)
    if cached_url:
        link = await crud.get_link_by_short_code(db, short_code)
        if link:
            if link.expires_at and link.expires_at < datetime.utcnow():
                await cache_invalidate(short_code)
                raise HTTPException(status_code=410, detail="Link has expired")
            await crud.increment_click(db, link)
            await cache_invalidate_stats(short_code)
        return RedirectResponse(url=cached_url, status_code=307)

    link = await crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link has expired")

    await crud.increment_click(db, link)
    await cache_set_url(short_code, link.original_url)
    await cache_invalidate_stats(short_code)

    return RedirectResponse(url=link.original_url, status_code=307)