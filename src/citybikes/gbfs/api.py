import json

from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.exceptions import HTTPException


LANGUAGES = ["en"]
VERSIONS = ["3.0"]


class RowObj:
    def __init__(self, row):
        for k, v in row.items():
            setattr(self, k, v)
        self._d = row

    def dump(self):
        return dict(filter(lambda i: i[1] not in [None, []], self._d.items()))


class Network(RowObj):
    def __init__(self, row):
        super().__init__(row)
        self.meta = RowObj(json.loads(row["meta"]))


class Station(RowObj):
    def __init__(self, row):
        super().__init__(row)
        self.stat = RowObj(json.loads(row["stat"]))
        self.extra = RowObj(json.loads(row["stat"])["extra"])


class GbfsStationInfo(Station):
    def __init__(self, row):
        super().__init__(row)
        d = {
            "station_id": self.hash,
            "name": i18n(self.name),
            "lat": GbfsFloat(self.latitude),
            "lon": GbfsFloat(self.longitude),
            "address": getattr(self.extra, "address", None),
            "post_code": getattr(self.extra, "post_code", None),
            "rental_methods": getattr(self.extra, "payment", []),
            # XXX Virtual
            # "is_virtual_station": ...
            "capacity": getattr(self.extra, "slots", None),
            "rental_uris": getattr(self.extra, "rental_uris", None),
        }

        if hasattr(self.extra, "payment-terminal"):
            m = set(d["rental_methods"] + ["key", "creditcard"])
            d["rental_methods"] = list(m)

        self._d = d


class GbfsStationStatus(Station):
    @property
    def vehicle_types(self):
        # First detect if we have types at all, because then we default to
        # normal bikes

        types = [(t, v) for t, v in Vehicles.def_map.items() if hasattr(self.extra, t)]

        if not types:
            return [
                {
                    "vehicle_type_id": Vehicles.normal_bike["vehicle_type_id"],
                    "count": self.stat.bikes,
                }
            ]

        return [
            {
                "vehicle_type_id": getattr(Vehicles, v)["vehicle_type_id"],
                "count": getattr(self.extra, t),
            }
            for t, v in types
        ]

    def __init__(self, row):
        super().__init__(row)

        d = {
            "station_id": self.hash,
            "num_vehicles_available": self.stat.bikes,
            "vehicle_types_available": self.vehicle_types,
            "num_docks_available": self.stat.free,
            # pybikes ignores non installed stations
            "is_installed": True,
            # XXX status ? and if not available, default to true
            "is_renting": getattr(self.stat, "online", True),
            "is_returning": getattr(self.stat, "online", True),
            "last_reported": self.stat.timestamp,
        }

        if hasattr(self.extra, "payment-terminal"):
            m = set(d["rental_methods"] + ["key", "creditcard"])
            d["rental_methods"] = list(m)

        self._d = d


def i18n(text):
    # XXX We do not support localized texts
    if not text:
        return []
    return [{"text": text, "language": lang} for lang in LANGUAGES]


def GbfsFloat(num):
    return round(float(num), 6)


class Vehicles:
    def_map = {
        "ebikes": "electric_bike",
        "normal_bikes": "normal_bike",
        "cargo": "cargo_bike",
        "ecargo": "electric_cargo_bike",
        "kid_bikes": "normal_kid_bike",
    }

    normal_bike = {
        "vehicle_type_id": "cb:vehicle:bike",
        "form_factor": "bicycle",
        "propulsion_type": "human",
        "name": i18n("Humble Bike"),
    }

    normal_kid_bike = {
        "vehicle_type_id": "cb:vehicle:kid-bike",
        "form_factor": "bicycle",
        "propulsion_type": "human",
        "name": i18n("Humble Kid Bike"),
    }

    electric_bike = {
        "vehicle_type_id": "cb:vehicle:ebike",
        "form_factor": "bicycle",
        "propulsion_type": "electric",
        "name": i18n("Electric Bike"),
    }

    cargo_bike = {
        "vehicle_type_id": "cb:vehicle:cargo",
        "form_factor": "cargo_bicycle",
        "propulsion_type": "human",
        "name": i18n("Humble Cargo Bike"),
    }

    electric_cargo_bike = {
        "vehicle_type_id": "cb:vehicle:ecargo",
        "form_factor": "cargo_bicycle",
        "propulsion_type": "eletric",
        "name": i18n("Electric Cargo Bike"),
    }


class Gbfs:
    def __init__(self, endpoint):
        self.endpoint = endpoint.rstrip("/")
        self.version = "3.0"
        self.ttl = 0
        self.base_url = f"{self.endpoint}/{self.version}"

    async def base_response(self, db, uid):
        return {
            "last_updated": await self.get_last_updated(db, uid),
            "ttl": self.ttl,
            "version": self.version,
            "data": {},
        }

    async def network_exists(self, db, uid):
        cur = await db.execute(
            """
            SELECT 1 from networks
            WHERE tag = ?
            LIMIT 1
        """,
            (uid,),
        )
        row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404)

        return True

    async def get_network(self, db, uid):
        cur = await db.execute(
            """
            SELECT * FROM networks
            WHERE tag = ?
            LIMIT 1
        """,
            (uid,),
        )

        row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404)

        return Network(row)

    async def get_last_updated(self, db, uid=None):
        if uid:
            cur = await db.execute(
                """
                SELECT MAX(stat->>'timestamp') as timestamp FROM stations
                WHERE network_tag = ?
            """,
                (uid,),
            )
        else:
            cur = await db.execute(
                """
                SELECT MAX(stat->>'timestamp') as timestamp FROM stations
            """
            )

        last_updated = (await cur.fetchone())["timestamp"]
        return last_updated

    async def gbfs(self, request, db, uid):
        assert await self.network_exists(db, uid)

        base_url = f"{self.base_url}/{uid}"

        return {
            "feeds": [
                {
                    "name": "system_information",
                    "url": f"{base_url}/system_information.json",
                },
                {
                    "name": "vehicle_types",
                    "url": f"{base_url}/vehicle_types.json",
                },
                {
                    "name": "station_information",
                    "url": f"{base_url}/station_information.json",
                },
                {
                    "name": "station_status",
                    "url": f"{base_url}/station_status.json",
                },
            ]
        }

    async def system_information(self, request, db, uid):
        network = await self.get_network(db, uid)

        data = {
            "system_id": uid,
            "languages": LANGUAGES,
            "name": i18n(network.name),
            "opening_hours": "off",
            "short_name": i18n(network.name),
            "feed_contact_email": "info@citybik.es",
            "timezone": "Etc/UTC",
            "attribution_organization_name": "CityBikes",
            "attribution_url": "https://citybik.es",
        }

        if network.meta.company:
            data["operator"] = i18n(" | ".join(network.meta.company))

        if hasattr(network.meta, "license") and "url" in network.meta.license:
            data["license_url"] = network.meta.license["url"]

        return data

    async def vehicle_types(self, request, db, uid):
        # match vehicle types according to station information heuristics
        # XXX ideally, we should set these on the network level in pybikes
        # so this info would be in meta

        cur = await db.execute(
            """
            SELECT
                   max(stat->>'extra'->>'normal_bikes' IS NOT NULL) as normal_bikes,
                   max(stat->>'extra'->>'ebikes' IS NOT NULL) as ebikes,
                   max(stat->>'extra'->>'cargo' IS NOT NULL) as cargo,
                   max(stat->>'extra'->>'ecargo' IS NOT NULL) as ecargo,
                   max(stat->>'extra'->>'kid_bikes' IS NOT NULL) as kid_bikes
            FROM stations
            WHERE network_tag = ?
            GROUP BY network_tag
        """,
            (uid,),
        )
        vehicle_types_q = await cur.fetchone()

        types = [(t, v) for t, v in Vehicles.def_map.items() if vehicle_types_q[t]]

        # default to normal bikes if no extra info specified
        if not types:
            vehicle_types = [Vehicles.normal_bike]
        else:
            vehicle_types = [getattr(Vehicles, v) for _, v in types]

        data = {"vehicle_types": vehicle_types}
        return data

    async def station_information(self, request, db, uid):
        network = await self.get_network(db, uid)
        cur = await db.execute(
            """
            SELECT * FROM stations
            WHERE network_tag = ?
            AND hash IN (
                SELECT value FROM json_each(?)
            )
            ORDER BY hash
        """,
            (
                uid,
                network.stations,
            ),
        )
        stations = map(lambda r: GbfsStationInfo(r).dump(), await cur.fetchall())
        return {
            "stations": list(stations),
        }

    async def station_status(self, request, db, uid):
        network = await self.get_network(db, uid)
        cur = await db.execute(
            """
            SELECT * FROM stations
            WHERE network_tag = ?
            AND hash IN (
                SELECT value FROM json_each(?)
            )
            ORDER BY hash
        """,
            (
                uid,
                network.stations,
            ),
        )
        stations = map(lambda r: GbfsStationStatus(r).dump(), await cur.fetchall())
        return {
            "stations": list(stations),
        }

    async def manifest(self, request, db):
        cur = await db.execute("""
            SELECT tag FROM networks
        """)
        rows = await cur.fetchall()

        base_url = self.endpoint

        return {
            "datasets": [
                {
                    "system_id": r["tag"],
                    "versions": [
                        {
                            "version": version,
                            "url": f"{base_url}/{version}/{r['tag']}/gbfs.json",
                        }
                        for version in VERSIONS
                    ],
                }
                for r in rows
            ]
        }

    @property
    def routes(self):
        def d(handler):
            """decorates requests with:
            * check if network exists
            * a db parameter
            * named params from url
            """

            async def _handler(request):
                args = request.path_params
                db = request.app.db

                uid = args.get("uid", None)

                if uid:
                    assert await self.network_exists(db, uid)

                base_response = await self.base_response(db, uid)

                r = await handler(request, db, **args)
                base_response.update({"data": r or {}})
                return JSONResponse(base_response)

            return _handler

        return [
            Mount(
                "/{uid}",
                routes=[
                    Route("/gbfs.json", d(self.gbfs)),
                    Route("/system_information.json", d(self.system_information)),
                    Route("/vehicle_types.json", d(self.vehicle_types)),
                    Route("/station_information.json", d(self.station_information)),
                    Route("/station_status.json", d(self.station_status)),
                ],
            ),
            Route("/manifest.json", d(self.manifest)),
        ]
