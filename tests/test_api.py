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


class TestUpstreamUrl:
    def test_manifest_exists(self, client):
        datasets = client.get("/3/manifest.json").json()["data"]["datasets"]
        assert len([d for d in datasets if "_upstream_url" in d]) > 0

    def test_manifest_with(self, client):
        datasets = client.get("/3/manifest.json").json()["data"]["datasets"]
        datasets = {d["system_id"]: d for d in datasets}
        assert datasets["divvy"]["_upstream_url"] == "https://gbfs.divvybikes.com/gbfs/gbfs.json"

    def test_manifest_without(self, client):
        datasets = client.get("/3/manifest.json").json()["data"]["datasets"]
        datasets = {d["system_id"]: d for d in datasets}
        assert "_upstream_url" not in datasets["bicing"]

    def test_system_information_with(self, client):
        assert client.get("/2/divvy/system_information.json").json()["data"]["_upstream_url"] == "https://gbfs.divvybikes.com/gbfs/gbfs.json"

    def test_system_information_without(self, client):
        assert "_upstream_url" not in client.get("/2/bicing/system_information.json").json()
