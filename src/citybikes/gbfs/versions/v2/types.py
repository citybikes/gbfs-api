from datetime import datetime

from citybikes.gbfs.constants import Vehicles as BVehicles
from typing import Annotated, Optional, Union

from pydantic import AfterValidator, BaseModel, BeforeValidator

# Set here the current version these types support. Minor can be increased
version = "2.3"


type Float = Annotated[
    float,
    AfterValidator(lambda x: round(x, 6)),
]

type p_int = Annotated[int, BeforeValidator(lambda n: max(n, 0))]

type Timestamp = Annotated[int,
    BeforeValidator(lambda t: int(datetime.fromisoformat(t).timestamp())),
]  # fmt: skip


class VehicleType(BaseModel):
    vehicle_type_id: str
    form_factor: str
    propulsion_type: str
    name: str
    max_range_meters: Optional[float] = None


class VehicleTypeCount(BaseModel):
    vehicle_type_id: str
    count: p_int


class VehicleTypes(BaseModel):
    vehicle_types: list[VehicleType]


class BikeStatus(BaseModel):
    bike_id: str
    vehicle_type_id: str

    lat: Float
    lon: Float

    is_reserved: bool
    is_disabled: bool

    last_reported: Timestamp

    current_range_meters: Optional[float] = None
    current_fuel_percent: Optional[float] = None


class BikeStatusR(BaseModel):
    bikes: list[BikeStatus]


class SystemInfo(BaseModel):
    system_id: str
    language: str
    name: str
    short_name: str
    operator: Optional[str] = None
    feed_contact_email: str
    timezone: str
    license_url: Optional[str] = None


class StationInfo(BaseModel):
    station_id: str
    name: str
    lat: Float
    lon: Float
    address: Optional[str] = None
    post_code: Optional[str] = None
    rental_methods: Optional[list[str]] = None
    capacity: Optional[p_int] = None
    rental_uris: Optional[dict] = None


class StationStatus(BaseModel):
    station_id: str
    num_bikes_available: p_int
    vehicle_types_available: list[VehicleTypeCount]
    num_docks_available: Optional[p_int]
    is_installed: bool
    is_renting: bool
    is_returning: bool
    last_reported: Timestamp


class StationInfoR(BaseModel):
    stations: list[StationInfo]


class StationStatusR(BaseModel):
    stations: list[StationStatus]


class Version(BaseModel):
    version: str
    url: str


class Versions(BaseModel):
    versions: list[Version]


class Feed(BaseModel):
    name: str
    url: str


class Feeds(BaseModel):
    feeds: list[Feed]


class Gbfs(BaseModel):
    # XXX hardcoded LANGUAGE. This is the _safest_ option, either this or
    # accept any arbitrary dict, which defeats the purpose of using types
    en: Feeds


class Response(BaseModel):
    last_updated: Timestamp
    ttl: p_int
    version: str = version
    data: Union[
        Gbfs,
        Versions,
        SystemInfo,
        VehicleTypes,
        StationInfoR,
        StationStatusR,
        BikeStatusR,
    ]


class Vehicles:
    normal_bike = VehicleType(**BVehicles.normal_bike)
    normal_kid_bike = VehicleType(**BVehicles.normal_kid_bike)
    electric_bike = VehicleType(**BVehicles.electric_bike)
    cargo_bike = VehicleType(**BVehicles.cargo_bike)
    electric_cargo_bike = VehicleType(**BVehicles.electric_cargo_bike)
    scooter = VehicleType(**BVehicles.scooter)

    default = normal_bike

    # aliases that map to Citybikes station fields
    normal_bikes = normal_bike
    ebikes = electric_bike
    cargo = cargo_bike
    ecargo = electric_cargo_bike
    kid_bikes = normal_kid_bike

    # aliases that map to Citybikes vehicle fields
    bike = normal_bike
    ebike = electric_bike
    scooter = scooter


class VehicleCounts:
    # XXX I hate this

    class Normal(VehicleTypeCount):
        vehicle_type_id: str = Vehicles.normal_bike.vehicle_type_id

    class NormalKid(VehicleTypeCount):
        vehicle_type_id: str = Vehicles.normal_kid_bike.vehicle_type_id

    class ElectricBike(VehicleTypeCount):
        vehicle_type_id: str = Vehicles.electric_bike.vehicle_type_id

    class CargoBike(VehicleTypeCount):
        vehicle_type_id: str = Vehicles.cargo_bike.vehicle_type_id

    class ElectricCargoBike(VehicleTypeCount):
        vehicle_type_id: str = Vehicles.electric_cargo_bike.vehicle_type_id

    Default = Normal

    # aliases that map to Citybikes fields
    ebikes = ElectricBike
    normal_bikes = Normal
    cargo = CargoBike
    ecargo = ElectricCargoBike
    kid_bikes = NormalKid


class Station2GbfsStationInfo(StationInfo):
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


class Station2GbfsStationStatus(StationStatus):
    @staticmethod
    def vehicle_types(station):
        counts = station.stat.vehicle_counts()

        if not counts:
            return [VehicleCounts.Default(count=station.stat.bikes)]

        return [getattr(VehicleCounts, k)(count=v) for k, v in counts]

    def __init__(self, station):
        stat = station.stat.model_dump(exclude_none=True)
        d = {
            "station_id": station.uid,
            "num_bikes_available": station.bikes,
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


class Vehicle2GbfsBikeStatus(BikeStatus):
    @staticmethod
    def type_id(vehicle):
        vt = getattr(Vehicles, vehicle.kind, Vehicles.default)
        return vt.vehicle_type_id

    def __init__(self, vehicle):
        stat = vehicle.stat.model_dump(exclude_none=True)
        d = {
            "lat": vehicle.latitude,
            "lon": vehicle.longitude,
            "bike_id": vehicle.uid,
            "vehicle_type_id": self.type_id(vehicle),
            "is_reserved": False,
            "is_disabled": not stat.get("online", True),
            "last_reported": vehicle.stat.timestamp,
        }
        super().__init__(**d)
