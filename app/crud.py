import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models, schemas
from app.auth import get_password_hash
from app.config import settings


async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: schemas.UserCreate) -> models.User:
    hashed_pw = get_password_hash(user_data.password)
    user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pw
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _generate_short_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


async def get_link_by_short_code(db: AsyncSession, short_code: str) -> models.Link | None:
    result = await db.execute(
        select(models.Link).where(models.Link.short_code == short_code)
    )
    return result.scalar_one_or_none()


async def get_link_by_alias(db: AsyncSession, alias: str) -> models.Link | None:
    result = await db.execute(
        select(models.Link).where(models.Link.custom_alias == alias)
    )
    return result.scalar_one_or_none()


async def get_link_by_original_url(db: AsyncSession, original_url: str) -> models.Link | None:
    result = await db.execute(
        select(models.Link).where(models.Link.original_url == original_url)
    )
    return result.scalar_one_or_none()


async def create_link(
    db: AsyncSession,
    link_data: schemas.LinkCreate,
    owner_id: int | None
) -> models.Link:
    if link_data.custom_alias:
        existing = await get_link_by_alias(db, link_data.custom_alias)
        if existing:
            raise ValueError(f"Alias '{link_data.custom_alias}' is already taken")
        short_code = link_data.custom_alias
    else:
        while True:
            short_code = _generate_short_code()
            existing = await get_link_by_short_code(db, short_code)
            if not existing:
                break

    link = models.Link(
        original_url=str(link_data.original_url),
        short_code=short_code,
        custom_alias=link_data.custom_alias,
        expires_at=link_data.expires_at,
        owner_id=owner_id
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def increment_click(db: AsyncSession, link: models.Link):
    link.click_count += 1
    link.last_used_at = datetime.utcnow()
    await db.commit()


async def update_link(
    db: AsyncSession,
    link: models.Link,
    update_data: schemas.LinkUpdate
) -> models.Link:
    if update_data.original_url is not None:
        link.original_url = str(update_data.original_url)

    if update_data.new_short_code is not None:
        existing = await get_link_by_short_code(db, update_data.new_short_code)
        if existing and existing.id != link.id:
            raise ValueError(f"Short code '{update_data.new_short_code}' is already taken")
        link.short_code = update_data.new_short_code

    await db.commit()
    await db.refresh(link)
    return link


async def delete_link(db: AsyncSession, link: models.Link):
    await db.delete(link)
    await db.commit()


async def archive_and_delete_expired(db: AsyncSession):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=settings.UNUSED_LINK_DAYS)

    result = await db.execute(
        select(models.Link).where(
            (models.Link.expires_at <= now) |
            (
                (models.Link.last_used_at != None) &
                (models.Link.last_used_at <= cutoff)
            ) |
            (
                (models.Link.last_used_at == None) &
                (models.Link.created_at <= cutoff)
            )
        )
    )
    expired_links = result.scalars().all()

    for link in expired_links:
        archived = models.ExpiredLink(
            original_url=link.original_url,
            short_code=link.short_code,
            custom_alias=link.custom_alias,
            created_at=link.created_at,
            click_count=link.click_count,
            owner_id=link.owner_id
        )
        db.add(archived)
        await db.delete(link)

    if expired_links:
        await db.commit()

    return len(expired_links)


async def get_expired_links(db: AsyncSession) -> list[models.ExpiredLink]:
    result = await db.execute(select(models.ExpiredLink))
    return result.scalars().all()


async def set_unused_days(days: int):
    settings.UNUSED_LINK_DAYS = days