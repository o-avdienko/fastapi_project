import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import cache

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    return create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine, setup_database):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Патчим get_redis чтобы lifespan не пытался подключиться к реальному Redis
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock(return_value=None)
    mock_redis.aclose = AsyncMock(return_value=None)

    # Патчим все функции кэша на заглушки
    cache.cache_get_url = AsyncMock(return_value=None)
    cache.cache_set_url = AsyncMock(return_value=None)
    cache.cache_invalidate = AsyncMock(return_value=None)
    cache.cache_get_stats = AsyncMock(return_value=None)
    cache.cache_set_stats = AsyncMock(return_value=None)
    cache.cache_invalidate_stats = AsyncMock(return_value=None)

    # Патчим get_redis и close_redis чтобы lifespan не падал
    with patch("app.cache.get_redis", AsyncMock(return_value=mock_redis)), \
         patch("app.cache.close_redis", AsyncMock(return_value=None)), \
         patch("app.main.get_redis", AsyncMock(return_value=mock_redis)), \
         patch("app.main.close_redis", AsyncMock(return_value=None)):

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    response = await client.post("/users/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    return response.json()


@pytest_asyncio.fixture
async def auth_token(client):
    await client.post("/users/register", json={
        "username": "authuser",
        "email": "auth@example.com",
        "password": "authpass123"
    })
    response = await client.post("/users/login", data={
        "username": "authuser",
        "password": "authpass123"
    })
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}