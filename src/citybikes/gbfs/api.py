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


from citybikes.gbfs.base_api import GBFSApi


class Gbfs(GBFSApi):

    GBFS = GBFS3
    ttl = 0

    async def gbfs(self, request, db, uid):

        return GBFS3.Feeds(
            **{
                "feeds": [
                    {
                        "name": "system_information",
                        "url": self.url_for(request, "/system_information.json", uid=uid),
                    },
                    {
                        "name": "vehicle_types",
                        "url": self.url_for(request, "/vehicle_types.json", uid=uid),
                    },
                    {
                        "name": "station_information",
                        "url": self.url_for(request, "/station_information.json", uid=uid),
                    },
                    {
                        "name": "station_status",
                        "url": self.url_for(request, "/station_status.json", uid=uid),
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

        datasets = [
            {
                "system_id": tag,
                "versions": [
                    {
                        "version": version,
                        "url": self.url_for(request, "/gbfs.json", uid=tag),
                    }
                    for version in VERSIONS
                ],
            }
            for tag in tags
        ]

        return GBFS3.Manifest(datasets=datasets)

    @property
    def routes(self):
        return [
            Mount(
                "/{uid}",
                routes=[
                    self.route('/gbfs.json', self.gbfs),
                    self.route("/system_information.json", self.system_information),
                    self.route("/vehicle_types.json", self.vehicle_types),
                    self.route("/station_information.json", self.station_information),
                    self.route("/station_status.json", self.station_status),
                ],
            ),
            self.route("/manifest.json", self.manifest),
        ]
