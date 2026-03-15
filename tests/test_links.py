import pytest
from datetime import datetime, timedelta

# Создание ссылки
async def test_create_link_anonymous(client):
    response = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com/"
    assert data["click_count"] == 0

async def test_create_link_authenticated(client, auth_headers):
    response = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["owner_id"] is not None

async def test_create_link_with_custom_alias(client, auth_headers):
    response = await client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "myalias"
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["short_code"] == "myalias"

async def test_create_link_duplicate_alias(client, auth_headers):
    await client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "dupalias"
    }, headers=auth_headers)
    response = await client.post("/links/shorten", json={
        "original_url": "https://other.com",
        "custom_alias": "dupalias"
    }, headers=auth_headers)
    assert response.status_code == 400


async def test_create_link_with_expiry(client, auth_headers):
    future = (datetime.utcnow() + timedelta(days=7)).isoformat()
    response = await client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "expires_at": future
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None


async def test_create_link_invalid_url(client):
    response = await client.post("/links/shorten", json={
        "original_url": "not-a-url"
    })
    assert response.status_code == 422

# Редирект
async def test_redirect_success(client):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    })
    short_code = create.json()["short_code"]
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"


async def test_redirect_nonexistent(client):
    response = await client.get("/nonexistent123", follow_redirects=False)
    assert response.status_code == 404


async def test_redirect_expired_link(client):
    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "expires_at": past
    })
    short_code = create.json()["short_code"]
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 410


async def test_redirect_increments_click_count(client):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    })
    short_code = create.json()["short_code"]

    await client.get(f"/{short_code}", follow_redirects=False)
    await client.get(f"/{short_code}", follow_redirects=False)

    stats = await client.get(f"/links/{short_code}/stats")
    assert stats.json()["click_count"] == 2

# Статистика
async def test_get_stats_success(client):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    })
    short_code = create.json()["short_code"]
    response = await client.get(f"/links/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://example.com/"
    assert "click_count" in data
    assert "created_at" in data


async def test_get_stats_nonexistent(client):
    response = await client.get("/links/nonexistent999/stats")
    assert response.status_code == 404

# Поиск
async def test_search_by_original_url(client):
    await client.post("/links/shorten", json={
        "original_url": "https://searchable.com"
    })
    response = await client.get(
        "/links/search",
        params={"original_url": "https://searchable.com/"}
    )
    assert response.status_code == 200
    assert "short_code" in response.json()

async def test_search_nonexistent_url(client):
    response = await client.get(
        "/links/search",
        params={"original_url": "https://notexists.com/"}
    )
    assert response.status_code == 404

# Обновление
async def test_update_link_url(client, auth_headers):
    create = await client.post("/links/shorten", json={
        "original_url": "https://old.com"
    }, headers=auth_headers)
    short_code = create.json()["short_code"]

    response = await client.put(f"/links/{short_code}", json={
        "original_url": "https://new.com"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["original_url"] == "https://new.com/"

async def test_update_link_short_code(client, auth_headers):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=auth_headers)
    short_code = create.json()["short_code"]

    response = await client.put(f"/links/{short_code}", json={
        "new_short_code": "newcode123"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["short_code"] == "newcode123"

async def test_update_link_unauthorized(client, auth_headers):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=auth_headers)
    short_code = create.json()["short_code"]

    response = await client.put(f"/links/{short_code}", json={
        "original_url": "https://hacked.com"
    })
    assert response.status_code == 401

async def test_update_link_wrong_owner(client):
    # Создаём первого пользователя и его ссылку
    await client.post("/users/register", json={
        "username": "owner1",
        "email": "owner1@example.com",
        "password": "password123"
    })
    login1 = await client.post("/users/login", data={
        "username": "owner1",
        "password": "password123"
    })
    headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=headers1)
    short_code = create.json()["short_code"]

    # Второй пользователь пытается изменить чужую ссылку
    await client.post("/users/register", json={
        "username": "owner2",
        "email": "owner2@example.com",
        "password": "password123"
    })
    login2 = await client.post("/users/login", data={
        "username": "owner2",
        "password": "password123"
    })
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    response = await client.put(f"/links/{short_code}", json={
        "original_url": "https://hacked.com"
    }, headers=headers2)
    assert response.status_code == 403

# Удаление
async def test_delete_link_success(client, auth_headers):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=auth_headers)
    short_code = create.json()["short_code"]

    response = await client.delete(f"/links/{short_code}", headers=auth_headers)
    assert response.status_code == 204

    # После удаления ссылка недоступна
    check = await client.get(f"/{short_code}", follow_redirects=False)
    assert check.status_code == 404

async def test_delete_link_unauthorized(client, auth_headers):
    create = await client.post("/links/shorten", json={
        "original_url": "https://example.com"
    }, headers=auth_headers)
    short_code = create.json()["short_code"]

    response = await client.delete(f"/links/{short_code}")
    assert response.status_code == 401


async def test_delete_nonexistent_link(client, auth_headers):
    response = await client.delete("/links/doesnotexist", headers=auth_headers)
    assert response.status_code == 404

# Дополнительные функции
async def test_get_expired_links(client):
    response = await client.get("/links/expired")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_cleanup_endpoint(client, auth_headers):
    response = await client.post("/links/admin/cleanup", headers=auth_headers)
    assert response.status_code == 200
    assert "Archived and deleted links" in response.json()["message"]

async def test_set_unused_days(client, auth_headers):
    response = await client.put(
        "/links/admin/unused-days",
        params={"days": 14},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "14" in response.json()["message"]