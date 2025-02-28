import os
import asyncio
import json
from contextlib import asynccontextmanager
from importlib import resources
from unittest import mock

import pytest
import pytest_asyncio
from starlette.schemas import SchemaGenerator
from starlette.testclient import TestClient

from citybikes.db import CBD
from citybikes.db.asyncio import get_session, migrate
from citybikes.gbfs.app import app


DB_URI = os.getenv("TEST_DB_URI", ":memory:")


@pytest_asyncio.fixture(scope="session")
async def db():
    test_data = resources.files("tests") / "fixtures/test_data.sql"
    async with get_session(DB_URI) as db:
        assert await migrate(db)
        if DB_URI == ":memory:":
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


@pytest.fixture(scope="session")
def gbfs_json_schema():
    base_path = resources.files("tests") / "fixtures/gbfs-json-schema/"

    def get_json_schema(version, uri):
        version = version.lstrip("v")
        return json.loads((base_path / f"v{version}" / uri).read_text())

    return get_json_schema


@pytest_asyncio.fixture(scope="function")
async def tags(db):
    tags = await CBD(db).get_tags()
    return tags


@pytest.fixture(scope="function", name="app")
def client_app(client):
    return client.app


async def get_urls(app):
    # XXX ideally we use the db and tags fixture here
    test_data = resources.files("tests") / "fixtures/test_data.sql"
    async with get_session(DB_URI) as db:
        assert await migrate(db)
        if DB_URI == ":memory:":
            await db.executescript(test_data.read_text())
        tags = await CBD(db).get_tags()

    schema = SchemaGenerator({})
    paths = [r.path for r in schema.get_endpoints(app.routes)]

    urls = []
    for url in paths:
        if "{uid}" in url:
            for tag in tags:
                urls.append(url.format(uid=tag))
        else:
            urls.append(url)

    return sorted(urls)


def pytest_generate_tests(metafunc):
    if "url" in metafunc.fixturenames:
        urls = asyncio.run(get_urls(app))
        metafunc.parametrize("url", urls)
