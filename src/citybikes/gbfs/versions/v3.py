from datetime import datetime

from citybikes.gbfs.constants import Vehicles as BVehicles
from typing import Annotated, Optional, Union

from pydantic import AfterValidator, BaseModel, BeforeValidator

# Set here the current version these types support. Minor can be increased
version = "3.0"


type Float = Annotated[
    float,
    AfterValidator(lambda x: round(x, 6)),
]

type p_int = Annotated[int, BeforeValidator(lambda n: max(n, 0))]

type Timestamp = Annotated[str,
    BeforeValidator(lambda t: datetime.fromisoformat(t).isoformat()),
]


class i18n(BaseModel):
    language: str
    text: str


def toi18n(text):
    if isinstance(text, str):
        return [i18n(language="en", text=text)]
    return text


type i18nL = Annotated[
    list[i18n],
    BeforeValidator(toi18n),
]


class VehicleType(BaseModel):
    vehicle_type_id: str
    form_factor: str
    propulsion_type: str
    name: i18nL
    max_range_meters: Optional[float] = None


class VehicleTypeCount(BaseModel):
    vehicle_type_id: str
    count: p_int


class VehicleTypes(BaseModel):
    vehicle_types: list[VehicleType]


class SystemInfo(BaseModel):
    system_id: str
    languages: list[str]
    name: i18nL
    opening_hours: str
    short_name: i18nL
    feed_contact_email: str
    # manifest_url is optional by spec, but required for us
    manifest_url: str
    timezone: str
    attribution_organization_name: i18nL
    attribution_url: str
    operator: Optional[i18nL] = None
    license_url: Optional[str] = None


class StationInfo(BaseModel):
    station_id: str
    name: i18nL
    lat: Float
    lon: Float
    address: Optional[str] = None
    post_code: Optional[str] = None
    rental_methods: Optional[list[str]] = None
    rental_uris: Optional[dict] = None
    capacity: Optional[p_int] = None


class StationStatus(BaseModel):
    station_id: str
    num_vehicles_available: p_int
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


class Dataset(BaseModel):
    system_id: str
    versions: list[Version]


class Manifest(BaseModel):
    datasets: list[Dataset]


class Feed(BaseModel):
    name: str
    url: str


class Feeds(BaseModel):
    feeds: list[Feed]


class Response(BaseModel):
    last_updated: Timestamp
    ttl: p_int
    version: str = version
    data: Union[
        Feeds,
        SystemInfo,
        VehicleTypes,
        StationInfoR,
        StationStatusR,
        Manifest,
    ]


class Vehicles:
    normal_bike = VehicleType(**BVehicles.normal_bike)
    normal_kid_bike = VehicleType(**BVehicles.normal_kid_bike)
    electric_bike = VehicleType(**BVehicles.electric_bike)
    cargo_bike = VehicleType(**BVehicles.cargo_bike)
    electric_cargo_bike = VehicleType(**BVehicles.electric_cargo_bike)

    default = normal_bike

    # aliases that map to Citybikes fields
    normal_bikes = normal_bike
    ebikes = electric_bike
    cargo = cargo_bike
    ecargo = electric_cargo_bike
    kid_bikes = normal_kid_bike


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
