from typing import Annotated, Optional, Union

from pydantic import AfterValidator, BaseModel

# Set here the current version these types support. Minor can be increased
version = "3.0"


class i18n(BaseModel):
    language: str
    text: str


type i18nL = list[i18n]


class VehicleType(BaseModel):
    vehicle_type_id: str
    form_factor: str
    propulsion_type: str
    name: list[i18n]


class VehicleTypes(BaseModel):
    vehicle_types: list[VehicleType]


type Float = Annotated[
    float,
    AfterValidator(lambda x: round(x, 6)),
]


class SystemInfo(BaseModel):
    system_id: str
    languages: list[str]
    name: i18nL
    opening_hours: str
    short_name: i18nL
    feed_contact_email: str
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
    capacity: Optional[int] = None
    rental_uris: Optional[list[dict]] = None


class StationStatus(BaseModel):
    station_id: str
    num_vehicles_available: int
    vehicle_types_available: list[dict]
    num_docks_available: int
    is_installed: bool
    is_renting: bool
    is_returning: bool
    last_reported: str


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
    last_updated: str
    ttl: int
    version: str = version
    data: Union[
        Feeds,
        SystemInfo,
        VehicleTypes,
        StationInfoR,
        StationStatusR,
        Manifest,
    ]
