from contextlib import asynccontextmanager
from importlib import resources
from unittest import mock

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from citybikes.db import get_session


@pytest_asyncio.fixture(scope="session")
async def db():
    test_data = resources.files("tests") / "fixtures/test_data.sql"
    async with get_session(":memory:") as db:
        await db.executescript(test_data.read_text())
        yield db


@pytest_asyncio.fixture(scope="function", autouse=True)
async def rollback_db(db):
    yield
    await db.rollback()


@pytest.mark.asyncio
async def test_db_is_populated(db):
    cur = await db.execute("SELECT * FROM networks")
    rows = await cur.fetchall()
    assert len(rows) > 0


@pytest.fixture(scope="function")
def client(db):
    @asynccontextmanager
    async def get_session(*args, **kwargs):
        yield db

    with mock.patch("citybikes.gbfs.app.get_session", get_session):
        from citybikes.gbfs.app import app

        with TestClient(app) as client:
            yield client
