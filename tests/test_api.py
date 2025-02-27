from jsonschema import validate


def test_not_found(client):
    assert client.get("/3.0/foobar/gbfs.json").status_code == 404


class TestData:
    def test_endpoint(self, client, tags, url):
        if "uid" in url:
            for uid in tags:
                assert client.get(url.format(uid=uid)).status_code == 200
        else:
            assert client.get(url).status_code == 200

    def test_schema(self, client, gbfs_json_schema, url):
        response = client.get(url)
        data = response.json()

        version = data["version"]
        uri = url.rsplit("/")[-1]
        schema = gbfs_json_schema(version, uri)

        assert validate(data, schema) is None
