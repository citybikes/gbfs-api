from functools import wraps

from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.exceptions import HTTPException


from citybikes.gbfs.types import GBFS3
from citybikes.gbfs.base_api import GBFSApi


LANGUAGES = ["en"]
VERSIONS = ["3.0"]


# XXX These go somewhere
class Station2GbfsStationInfo(GBFS3.StationInfo):
    def __init__(self, station):
        d = {
            "station_id": station.uid,
            "name": station.name,
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
        counts = station.extra.vehicle_counts()

        if not counts:
            return [GBFS3.VehicleCounts.Default(count=station.stat.bikes)]

        return [getattr(GBFS3.VehicleCounts, k)(count=v) for k, v in counts]


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
            "name": network.name,
            "opening_hours": "off",
            "short_name": network.name,
            "feed_contact_email": "info@citybik.es",
            "timezone": "Etc/UTC",
            "attribution_organization_name": "CityBikes",
            "attribution_url": "https://citybik.es",
        }

        if network.meta.company:
            data["operator"] = " | ".join(network.meta.company)

        if network.meta.license and network.meta.license.url:
            data["license_url"] = network.meta.license.url

        return GBFS3.SystemInfo(**data)

    async def vehicle_types(self, request, db, uid):
        types = await db.vehicle_types(uid)

        # default to normal bikes if no extra info specified
        if not types:
            vehicle_types = [GBFS3.Vehicles.default]
        else:
            vehicle_types = [getattr(GBFS3.Vehicles, t) for t in types]

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
