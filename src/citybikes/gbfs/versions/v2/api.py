from functools import partial

from starlette.routing import Mount

from citybikes.gbfs.types import GBFS2
from citybikes.gbfs.api import Gbfs as BaseGbfs


LANGUAGE = "en"


class Gbfs(BaseGbfs):
    GBFS = GBFS2

    @property
    def routes(self):
        network_routes = [
            self.route("/gbfs.json", self.gbfs),
            self.route("/gbfs_versions.json", self.gbfs_versions),
            self.route("/system_information.json", self.system_information),
            self.route("/vehicle_types.json", self.vehicle_types),
            self.route("/station_information.json", self.station_information),
            self.route("/station_status.json", self.station_status),
        ]

        return [
            Mount("/{uid}", routes=network_routes),
        ]

    async def gbfs(self, request, db, uid):
        url_for = partial(self.url_for, request, uid=uid)

        feeds = [
            {
                "name": "gbfs",
                "url": url_for("/gbfs.json"),
            },
            {
                "name": "gbfs_versions",
                "url": url_for("/gbfs_versions.json"),
            },
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

        return GBFS2.Gbfs(**{LANGUAGE: GBFS2.Feeds(feeds=feeds)})

    async def gbfs_versions(self, request, db, uid):
        url_for = partial(self.url_for, request, "/gbfs.json", uid=uid)
        versions = [
            {"version": version, "url": url_for(version=version)}
            for version in request.app.VERSIONS
        ]
        return GBFS2.Versions(versions=versions)

    async def system_information(self, request, db, uid):
        network = await db.get_network(uid)

        data = {
            "system_id": uid,
            "language": LANGUAGE,
            "name": network.name,
            "short_name": network.name,
            "feed_contact_email": "info@citybik.es",
            # XXX maybe we start collecting timezones on pybikes meta
            "timezone": "Etc/UTC",
        }

        if network.meta.company:
            data["operator"] = " | ".join(network.meta.company)

        if network.meta.license and network.meta.license.url:
            data["license_url"] = network.meta.license.url

        return GBFS2.SystemInfo(**data)

    async def vehicle_types(self, request, db, uid):
        types = await db.vehicle_types(uid)

        # default to normal bikes if no extra info specified
        if not types:
            vehicle_types = [GBFS2.Vehicles.default]
        else:
            vehicle_types = [getattr(GBFS2.Vehicles, t) for t in types]

        return GBFS2.VehicleTypes(vehicle_types=vehicle_types)

    async def station_information(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: GBFS2.Station2GbfsStationInfo(s), stations)
        return GBFS2.StationInfoR(stations=list(stations))

    async def station_status(self, request, db, uid):
        stations = await db.get_stations(uid)
        stations = map(lambda s: GBFS2.Station2GbfsStationStatus(s), stations)
        return GBFS2.StationStatusR(stations=list(stations))
