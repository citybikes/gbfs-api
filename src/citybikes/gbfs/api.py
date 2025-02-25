from functools import wraps

from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.exceptions import HTTPException


from citybikes.gbfs.types import GBFS3


LANGUAGES = ["en"]
VERSIONS = ["3.0"]


# XXX These go somewhere
class Station2GbfsStationInfo(GBFS3.StationInfo):
    def __init__(self, station):
        d = {
            "station_id": station.uid,
            "name": i18n(station.name),
            "lat": station.latitude,
            "lon": station.longitude,
            "address": station.extra.address,
            "post_code": station.extra.post_code,
            "rental_methods": station.extra.payment,
            # XXX Virtual
            # "is_virtual_station": ...
            "capacity": station.extra.slots,
            "rental_uris": station.extra.rental_uris,
        }

        if station.extra.payment_terminal is not None:
            m = set(d["rental_methods"] or [] + ["key", "creditcard"])
            d["rental_methods"] = list(m)

        super().__init__(**d)


class Station2GbfsStationStatus(GBFS3.StationStatus):
    @staticmethod
    def vehicle_types(station):
        # First detect if we have types at all, because then we default to
        # normal bikes

        extra = station.extra.model_dump(exclude_none=True)

        types = [(t, v) for t, v in Vehicles.def_map.items() if t in extra]

        if not types:
            return [
                {
                    "vehicle_type_id": Vehicles.normal_bike["vehicle_type_id"],
                    "count": station.stat.bikes,
                }
            ]

        return [
            {
                "vehicle_type_id": getattr(Vehicles, v)["vehicle_type_id"],
                "count": getattr(station.extra, t),
            }
            for t, v in types
        ]

    def __init__(self, station):
        stat = station.stat.model_dump(exclude_none=True)
        d = {
            "station_id": station.uid,
            "num_vehicles_available": station.bikes,
            "vehicle_types_available": self.vehicle_types(station),
            "num_docks_available": station.free,
            # pybikes ignores non installed stations
            "is_installed": True,
            # XXX status ? and if not available, default to true
            "is_renting": stat.get("online", True),
            "is_returning": stat.get("online", True),
            "last_reported": station.timestamp,
        }
        super().__init__(**d)


def i18n(text):
    # XXX We do not support localized texts
    if not text:
        return []
    return [{"text": text, "language": lang} for lang in LANGUAGES]


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
        "max_range_meters": 9000,
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
        "max_range_meters": 9000,
    }


class Gbfs:
    def __init__(self, endpoint):
        self.endpoint = endpoint.rstrip("/")
        self.version = "3.0"
        self.ttl = 0
        self.base_url = f"{self.endpoint}/{self.version}"

    async def gbfs(self, request, db, uid):
        base_url = f"{self.base_url}/{uid}"

        return GBFS3.Feeds(
            **{
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
        )

    async def system_information(self, request, db, uid):
        network = await db.get_network(uid)

        data = {
            "system_id": uid,
            "languages": LANGUAGES,
            "name": i18n(network.name),
            "opening_hours": "off",
            "short_name": i18n(network.name),
            "feed_contact_email": "info@citybik.es",
            "timezone": "Etc/UTC",
            "attribution_organization_name": i18n("CityBikes"),
            "attribution_url": "https://citybik.es",
        }

        if network.meta.company:
            data["operator"] = i18n(" | ".join(network.meta.company))

        if network.meta.license and network.meta.license.url:
            data["license_url"] = network.meta.license.url

        return GBFS3.SystemInfo(**data)

    async def vehicle_types(self, request, db, uid):
        vehicle_types_q = await db.vehicle_types(uid)

        types = [(t, v) for t, v in Vehicles.def_map.items() if vehicle_types_q[t]]

        # default to normal bikes if no extra info specified
        if not types:
            vehicle_types = [Vehicles.normal_bike]
        else:
            vehicle_types = [getattr(Vehicles, v) for _, v in types]

        data = {"vehicle_types": vehicle_types}

        return GBFS3.VehicleTypes(**data)

    async def station_information(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: Station2GbfsStationInfo(s), stations)
        return GBFS3.StationInfoR(stations=list(stations))

    async def station_status(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: Station2GbfsStationStatus(s), stations)
        return GBFS3.StationStatusR(stations=list(stations))

    async def manifest(self, request, db):
        tags = await db.get_tags()
        base_url = self.endpoint

        datasets = [
            {
                "system_id": tag,
                "versions": [
                    {
                        "version": version,
                        "url": f"{base_url}/{version}/{tag}/gbfs.json",
                    }
                    for version in VERSIONS
                ],
            }
            for tag in tags
        ]

        return GBFS3.Manifest(datasets=datasets)

    @property
    def routes(self):
        def d(handler):
            """decorates requests with:
            * check if network exists
            * a db parameter
            * named params from url
            """

            @wraps(handler)
            async def _handler(request):
                args = request.path_params
                db = request.app.db

                uid = args.get("uid", None)

                if uid and not (await db.network_exists(uid)):
                    raise HTTPException(status_code=404)

                response = GBFS3.Response(
                    last_updated=await db.get_last_updated(uid),
                    ttl=self.ttl,
                    data=await handler(request, db, **args),
                )
                return JSONResponse(response.model_dump(exclude_none=True))

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
