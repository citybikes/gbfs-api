from functools import partial

from starlette.routing import Mount

from citybikes.gbfs.types import GBFS3
from citybikes.gbfs.api import Gbfs as BaseGbfs


LANGUAGES = ["en"]


class Gbfs(BaseGbfs):
    GBFS = GBFS3

    @property
    def routes(self):
        network_routes = [
            self.route("/gbfs.json", self.gbfs),
            self.route("/system_information.json", self.system_information),
            self.route("/vehicle_types.json", self.vehicle_types),
            self.route("/station_information.json", self.station_information),
            self.route("/station_status.json", self.station_status),
        ]

        return [
            Mount("/{uid}", routes=network_routes),
            self.route("/manifest.json", self.manifest),
        ]

    async def gbfs(self, request, db, uid):
        url_for = partial(self.url_for, request, uid=uid)

        feeds = [
            {
                "name": "system_information",
                "url": url_for("/system_information.json"),
            },
            {
                "name": "vehicle_types",
                "url": url_for("/vehicle_types.json"),
            },
            {
                "name": "station_information",
                "url": url_for("/station_information.json"),
            },
            {
                "name": "station_status",
                "url": url_for("/station_status.json"),
            },
        ]

        return GBFS3.Feeds(feeds=feeds)

    async def system_information(self, request, db, uid):
        network = await db.get_network(uid)

        data = {
            "system_id": uid,
            "languages": LANGUAGES,
            "name": network.name,
            "opening_hours": "off",
            "short_name": network.name,
            "feed_contact_email": "info@citybik.es",
            "manifest_url": self.url_for(request, "/manifest.json"),
            # XXX maybe we start collecting timezones on pybikes meta
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

        return GBFS3.VehicleTypes(vehicle_types=vehicle_types)

    async def station_information(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: GBFS3.Station2GbfsStationInfo(s), stations)
        return GBFS3.StationInfoR(stations=list(stations))

    async def station_status(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: GBFS3.Station2GbfsStationStatus(s), stations)
        return GBFS3.StationStatusR(stations=list(stations))

    async def manifest(self, request, db):
        tags = await db.get_tags()

        datasets = [
            {
                "system_id": tag,
                "versions": [
                    {
                        "version": version,
                        "url": self.url_for(
                            request, "/gbfs.json", uid=tag, version=version
                        ),
                    }
                    for version in request.app.VERSIONS
                ],
            }
            for tag in tags
        ]

        return GBFS3.Manifest(datasets=datasets)
