
from pydantic import BaseModel, ConfigDict, Field, Json


class License(BaseModel):
    name: str
    url: str


class Meta(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    latitude: float
    longitude: float
    company: list[str]
    license: License | None = None


class Extra(BaseModel):
    model_config = ConfigDict(extra="allow")

    online: bool | None = None
    ebikes: int | None = None
    normal_bikes: int | None = None
    cargo: int | None = None
    ecargo: int | None = None
    kid_bikes: int | None = None

    address: str | None = None
    post_code: str | None = None
    payment: list[str] | None = None
    payment_terminal: bool | None = Field(alias="payment-terminal", default=None)
    slots: int | None = None
    rental_uris: dict | None = None

    class Meta:
        vehicle_attrs = ["ebikes", "normal_bikes", "cargo", "ecargo", "kid_bikes"]  # noqa: RUF012


class Stat(BaseModel):
    bikes: int | None = None
    free: int | None = None
    timestamp: str
    extra: Extra

    def vehicle_counts(self):
        counts = [(k, getattr(self.extra, k)) for k in Extra.Meta.vehicle_attrs]
        counts = list(filter(lambda kv: kv[1] is not None, counts))

        # XXX not all pybikes instances with ebikes include 'normal_bikes'
        # assume that if normal_bikes missing and
        # sum(counts) != station.stat.bikes
        # then normal_bikes = station.stat.bikes - sum(counts)
        if 'normal_bikes' not in [k for k, _ in counts]:
            counted_bikes = sum(v for _, v in counts)
            if self.bikes is not None and counted_bikes < self.bikes:
                normal_bikes = self.bikes - counted_bikes
                counts.append(('normal_bikes', normal_bikes))

        return counts



class Station(BaseModel):
    uid: str = Field(alias="hash")
    name: str | None = None
    latitude: float
    longitude: float
    stat: Json[Stat]

    # attr dispatcher to stat
    def __getattr__(self, attr):
        return getattr(self.stat, attr)


class Network(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: str = Field(alias="tag")
    name: str
    meta: Json[Meta]


class VehicleExtra(BaseModel):
    model_config = ConfigDict(extra="allow")
    battery: float | None = None
    online: bool | None = None


class VehicleStat(BaseModel):
    timestamp: str
    extra: VehicleExtra


class Vehicle(BaseModel):
    uid: str = Field(alias="hash")
    latitude: float
    longitude: float
    kind: str
    stat: Json[VehicleStat]
