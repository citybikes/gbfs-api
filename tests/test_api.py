import re

from jsonschema import validate


def test_not_found(client):
    assert client.get("/3.0/foobar/gbfs.json").status_code == 404


class TestData:
    def test_endpoint(self, client, tags, url):
        assert client.get(url).status_code == 200

    def test_gbfs_json_schema(self, client, gbfs_json_schema, url):
        response = client.get(url)
        data = response.json()

        version = data["version"]
        uri = url.split("/")[-1]
        schema = gbfs_json_schema(version, uri)

        assert validate(data, schema) is None

    def test_version_is_major(self, client, url):
        response = client.get(url)
        data = response.json()
        major_version = re.sub(r"\..*", "", data["version"])
        path_version = url.split("/")[1]
        assert major_version == path_version
