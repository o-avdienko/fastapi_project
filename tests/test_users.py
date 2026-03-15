import pytest

# Регистрация
async def test_register_success(client):
    response = await client.post("/users/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password" not in data

async def test_register_duplicate_username(client):
    await client.post("/users/register", json={
        "username": "duplicate",
        "email": "first@example.com",
        "password": "password123"
    })
    response = await client.post("/users/register", json={
        "username": "duplicate",
        "email": "second@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


async def test_register_duplicate_email(client):
    await client.post("/users/register", json={
        "username": "user1",
        "email": "same@example.com",
        "password": "password123"
    })
    response = await client.post("/users/register", json={
        "username": "user2",
        "email": "same@example.com",
        "password": "password123"
    })
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

async def test_register_short_username(client):
    response = await client.post("/users/register", json={
        "username": "ab",
        "email": "ab@example.com",
        "password": "password123"
    })
    assert response.status_code == 422


async def test_register_short_password(client):
    response = await client.post("/users/register", json={
        "username": "validuser",
        "email": "valid@example.com",
        "password": "123"
    })
    assert response.status_code == 422


# Логин
async def test_login_success(client):
    await client.post("/users/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "password123"
    })
    response = await client.post("/users/login", data={
        "username": "loginuser",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/users/register", json={
        "username": "wrongpass",
        "email": "wrongpass@example.com",
        "password": "correctpassword"
    })
    response = await client.post("/users/login", data={
        "username": "wrongpass",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


async def test_login_nonexistent_user(client):
    response = await client.post("/users/login", data={
        "username": "nobody",
        "password": "password123"
    })
    assert response.status_code == 401


# Профиль
async def test_get_me_success(client, auth_headers):
    response = await client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "authuser"


async def test_get_me_without_token(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_get_me_invalid_token(client):
    response = await client.get("/users/me", headers={
        "Authorization": "Bearer invalidtoken123"
    })
    assert response.status_code == 401