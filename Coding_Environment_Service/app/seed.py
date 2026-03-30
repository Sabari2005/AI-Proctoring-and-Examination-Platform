"""
seed.py — Create initial admin user.
Run once after migrations (from project root):
    python -m app.seed

Inside docker-compose:
    docker compose exec -w /app api python -m app.seed
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.models import Base, User
from app.routers.auth import hash_password


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)

    # Create tables (if not using alembic yet)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        users_to_seed = [
            {
                "username": "admin",
                "email": "admin@yourplatform.com",
                "password": "changeme123",
                "role": "admin",
            },
            {
                "username": "proctor1",
                "email": "proctor1@yourplatform.com",
                "password": "proctor123",
                "role": "proctor",
            },
            {
                "username": "candidate1",
                "email": "candidate1@yourplatform.com",
                "password": "candidate123",
                "role": "candidate",
            },
            {
                "username": "sabari",
                "email": "sabari@yourplatform.com",
                "password": "sabari@admin",
                "role": "candidate",
            },
        ]

        created_users = []
        for seed_user in users_to_seed:
            result = await db.execute(
                select(User).where(User.username == seed_user["username"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                continue

            db.add(
                User(
                    username=seed_user["username"],
                    email=seed_user["email"],
                    hashed_password=hash_password(seed_user["password"]),
                    role=seed_user["role"],
                )
            )
            created_users.append(seed_user["username"])

        await db.commit()
        if created_users:
            print("Seeded users:", ", ".join(created_users))
        else:
            print("Seed complete: users already present")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
