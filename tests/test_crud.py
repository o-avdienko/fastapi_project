import pytest
from datetime import datetime, timedelta
from app import crud, schemas

async def test_create_and_get_link(db_session):
    data = schemas.LinkCreate(original_url="https://crud-test.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    assert link.short_code
    found = await crud.get_link_by_short_code(db_session, link.short_code)
    assert found.id == link.id

async def test_create_link_custom_alias(db_session):
    data = schemas.LinkCreate(original_url="https://alias-test.com", custom_alias="testalias99")
    link = await crud.create_link(db_session, data, owner_id=None)
    assert link.short_code == "testalias99"

async def test_create_link_duplicate_alias(db_session):
    data = schemas.LinkCreate(original_url="https://dup.com", custom_alias="dupalias99")
    await crud.create_link(db_session, data, owner_id=None)
    with pytest.raises(ValueError):
        await crud.create_link(db_session, data, owner_id=None)

async def test_get_link_by_alias(db_session):
    data = schemas.LinkCreate(original_url="https://alias2.com", custom_alias="alias2test")
    link = await crud.create_link(db_session, data, owner_id=None)
    found = await crud.get_link_by_alias(db_session, "alias2test")
    assert found.id == link.id

async def test_get_link_by_original_url(db_session):
    data = schemas.LinkCreate(original_url="https://origurl-test.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    found = await crud.get_link_by_original_url(db_session, "https://origurl-test.com/")
    assert found.id == link.id

async def test_increment_click(db_session):
    data = schemas.LinkCreate(original_url="https://click-test.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    await crud.increment_click(db_session, link)
    await crud.increment_click(db_session, link)
    assert link.click_count == 2
    assert link.last_used_at is not None

async def test_update_link_url(db_session):
    data = schemas.LinkCreate(original_url="https://old-url.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    update = schemas.LinkUpdate(original_url="https://new-url.com")
    updated = await crud.update_link(db_session, link, update)
    assert updated.original_url == "https://new-url.com/"

async def test_update_link_short_code(db_session):
    data = schemas.LinkCreate(original_url="https://code-update.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    update = schemas.LinkUpdate(new_short_code="newcode999")
    updated = await crud.update_link(db_session, link, update)
    assert updated.short_code == "newcode999"

async def test_update_link_duplicate_short_code(db_session):
    data1 = schemas.LinkCreate(original_url="https://first.com", custom_alias="firstcode1")
    data2 = schemas.LinkCreate(original_url="https://second.com", custom_alias="secondcode1")
    await crud.create_link(db_session, data1, owner_id=None)
    link2 = await crud.create_link(db_session, data2, owner_id=None)
    update = schemas.LinkUpdate(new_short_code="firstcode1")
    with pytest.raises(ValueError):
        await crud.update_link(db_session, link2, update)

async def test_delete_link(db_session):
    data = schemas.LinkCreate(original_url="https://delete-test.com")
    link = await crud.create_link(db_session, data, owner_id=None)
    await crud.delete_link(db_session, link)
    found = await crud.get_link_by_short_code(db_session, link.short_code)
    assert found is None

async def test_archive_and_delete_expired(db_session):
    past = datetime.utcnow() - timedelta(hours=1)
    data = schemas.LinkCreate(original_url="https://expired-test.com", expires_at=past)
    link = await crud.create_link(db_session, data, owner_id=None)
    count = await crud.archive_and_delete_expired(db_session)
    assert count >= 1
    found = await crud.get_link_by_short_code(db_session, link.short_code)
    assert found is None

async def test_get_expired_links(db_session):
    expired = await crud.get_expired_links(db_session)
    assert isinstance(expired, list)

async def test_create_user(db_session):
    data = schemas.UserCreate(username="cruduser1", email="crud1@test.com", password="pass123")
    user = await crud.create_user(db_session, data)
    assert user.id is not None
    assert user.username == "cruduser1"

async def test_get_user_by_username(db_session):
    data = schemas.UserCreate(username="cruduser2", email="crud2@test.com", password="pass123")
    await crud.create_user(db_session, data)
    found = await crud.get_user_by_username(db_session, "cruduser2")
    assert found is not None

async def test_get_user_by_email(db_session):
    data = schemas.UserCreate(username="cruduser3", email="crud3@test.com", password="pass123")
    await crud.create_user(db_session, data)
    found = await crud.get_user_by_email(db_session, "crud3@test.com")
    assert found is not None
