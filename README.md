# gbfs-api

`gbfs-api` is a lightweight implementation of the [General Bikeshare Feed
Specification (GBFS)][1] built on top of CityBikes data. It provides a
standardized HTTP API for accessing real-time bike share information.

The API supports GBFS versions [2.3][2.3] and [3.0][3.0].

[1]: https://gbfs.org
[2.3]: https://github.com/MobilityData/gbfs/blob/v2.3/gbfs.md
[3.0]: https://github.com/MobilityData/gbfs/blob/v3.0/gbfs.md

## Installation

```sh
git clone https://github.com/citybikes/gbfs-api
cd gbfs-api
pip install -e .
```
## Usage

```sh
# init db
python -m citybikes.cmd.migrate

# seed with test data
python -m citybikes.cmd.seed

# start the API
python -m citybikes.cmd.srv --port 8000

# alternatively
uvicorn citybikes.gbfs.app:app --port 8000

```
Once the API is running, you can query endpoints such as:

```sh
http :8000/3/manifest.json
http :8000/3/bicing/gbfs.json
http :8000/2/velib/gbfs.json
```

### Usage with CityBikes Hyper

For real-time data, install [hyper][2] and run a publisher and subscriber:

```sh
pip install https://github.com/citybikes/hyper
hyper publisher
```

```sh
python -m citybikes.cmd.subscriber
```

Now, `citybikes.db` contains real-time bike availability!

[2]: https://github.com/citybikes/hyper

## API Endpoints

* `GET /<version>/<resource>`
* `GET /<version>/<network>/<resource>`

For example:

* `GET /3/manifest.json` - Returns the GBFS v3 manifest document.
* `GET /3/bicing/gbfs.json` - Returns the GBFS v3 auto-discovery document for a
* `bicing` network.
* `GET /2/velib/station_status.json` - Returns the GBFS v2 station status
* document for a `velib` network.

See the full specification at https://docs.citybik.es/api/gbfs and
https://github.com/MobilityData/gbfs


## Configuration

- `DB_URI` - Path to the database (default: `citybikes.db`)
- `TEST_DB_URI` - Path to the test database (default: `:memory:`)

## Development

To set up a local development environment:

```sh
uv venv
source .venv/bin/activate
uv sync
uv pip install -e .
```

### Running Tests

Run tests with:

```sh
pytest -vv
```

To run tests against a populated database, set up `TEST_DB_URI`:

```sh
export TEST_DB_URI='citybikes.db'
pytest -vv
```

This is useful for validating endpoints against the GBFS JSON schema.

## License

`gbfs-api` is **free, open-source software** licensed under **AGPLv3**. See [LICENSE](LICENSE.txt) for details.

## Funding

This project is funded through the [NGI0 Commons Fund](https://nlnet.nl/commonsfund), a fund established by [NLnet](https://nlnet.nl) with financial support from the European Commission's [Next Generation Internet](https://ngi.eu) program. Learn more at the [NLnet project page](https://nlnet.nl/project/CityBikes).

[![NLnet foundation logo](https://nlnet.nl/logo/banner.png)](https://nlnet.nl)
[![NGI Zero Logo](https://nlnet.nl/image/logos/NGI0_tag.svg)](https://nlnet.nl/commonsfund)
