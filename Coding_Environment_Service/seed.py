"""Run DB seed from project root: python seed.py."""

import asyncio

from app.seed import seed


if __name__ == "__main__":
    asyncio.run(seed())