import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.routers import links, users
from app.cache import get_redis, close_redis
from app import crud
from app.database import AsyncSessionLocal


async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)
        try:
            async with AsyncSessionLocal() as db:
                count = await crud.archive_and_delete_expired(db)
                if count:
                    print(f"[Cleanup] Удалено истёкших ссылок: {count}")
        except Exception as e:
            print(f"[Cleanup] Ошибка: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_redis()
    cleanup_task = asyncio.create_task(periodic_cleanup())

    print("Сервис запущен. БД и Redis готовы.")
    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    await close_redis()
    print("Сервис остановлен.")


app = FastAPI(
    title="URL Shortener API",
    description="Сервис сокращения ссылок с аналитикой и кэшированием",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(users.router)
app.include_router(links.router)


@app.get("/", tags=["Сервис"])
async def root():
    return {"status": "ok", "message": "URL Shortener работает"}