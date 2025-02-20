# XXX: etc

def test_endpoints(client):
    assert client.get("/3.0/manifest.json").status_code == 200
    assert client.get("/3.0/bicing/gbfs.json").status_code == 200
    assert client.get("/3.0/velib/gbfs.json").status_code == 200

def test_not_found(client):
    assert client.get("/3.0/foobar/gbfs.json").status_code == 404

