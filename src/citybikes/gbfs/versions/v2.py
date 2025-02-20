from typing import Optional, Annotated

from pydantic import BaseModel, AfterValidator


# Set here the current version these types support. Minor can be increased
version = "2.3"


class VehicleType(BaseModel):
    vehicle_type_id: str
    form_factor: str
    propulsion_type: str
    name: str


class VehicleTypes(BaseModel):
    vehicle_types: list[VehicleType]


type Float = Annotated[
    float,
    AfterValidator(lambda x: round(x, 6)),
]


class SystemInfo(BaseModel):
    system_id: str
    language: str
    name: str
    feed_contact_email: str
    timezone: str
    operator: Optional[str] = None
    license_url: Optional[str] = None


class StationInfo(BaseModel):
    station_id: str
    name: str
    lat: Float
    lon: Float
    address: Optional[str] = None
    post_code: Optional[str] = None
    rental_methods: Optional[list[str]] = None
    capacity: Optional[int] = None
    rental_uris: Optional[list[dict]] = None


class StationStatus(BaseModel):
    station_id: str
    num_bikes_available: int
    vehicle_types_available: list[VehicleType]
    num_docks_available: int
    is_installed: bool
    is_renting: bool
    is_returning: bool
    last_reported: str


class StationInfoResponse(BaseModel):
    stations: list[StationInfo]


class StationStatusResponse(BaseModel):
    stations: list[StationStatus]


class Response(BaseModel):
    last_updated: str
    ttl: int
    version: str = version
    data: dict
