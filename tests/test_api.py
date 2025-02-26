import re

from jsonschema import validate

from starlette.schemas import SchemaGenerator


def test_endpoints(client):
    assert client.get("/3.0/manifest.json").status_code == 200
    assert client.get("/3.0/bicing/gbfs.json").status_code == 200
    assert client.get("/3.0/velib/gbfs.json").status_code == 200
    assert client.get("/3.0/bicing/vehicle_types.json").status_code == 200


def test_not_found(client):
    assert client.get("/3.0/foobar/gbfs.json").status_code == 404


def test_schema(app, client, gbfs_json_schema, tags):
    # XXX parametrize so it runs every call as a test case
    schema = SchemaGenerator({})
    paths = [r.path for r in SchemaGenerator({}).get_endpoints(app.routes)]

    for path in paths:
        uri = path.rsplit("/")[-1]
        version = re.search(r"^/(\d+\.\d+)", path).group(1)
        schema = gbfs_json_schema(version, uri)

        if "uid" in path:
            for uid in tags:
                response = client.get(path.format(uid=uid))
                assert response.status_code == 200
                assert validate(response.json(), schema) is None
        else:
            response = client.get(path)
            assert response.status_code == 200
            assert validate(response.json(), schema) is None
