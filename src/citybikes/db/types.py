from typing import Optional

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
    license: Optional[License] = None


class Extra(BaseModel):
    model_config = ConfigDict(extra="allow")

    online: Optional[bool] = None
    ebikes: Optional[int] = None
    normal_bikes: Optional[int] = None
    cargo: Optional[int] = None
    ecargo: Optional[int] = None
    kid_bikes: Optional[int] = None

    address: Optional[str] = None
    post_code: Optional[str] = None
    payment: Optional[list[str]] = None
    payment_terminal: Optional[bool] = Field(alias="payment-terminal", default=None)
    slots: Optional[int] = None
    rental_uris: Optional[dict] = None

    class Meta:
        vehicle_attrs = ["ebikes", "normal_bikes", "cargo", "ecargo", "kid_bikes"]

    def vehicle_counts(self):
        counts = [(k, getattr(self, k)) for k in Extra.Meta.vehicle_attrs]
        counts = filter(lambda kv: kv[1] is not None, counts)
        return list(counts)


class Stat(BaseModel):
    bikes: Optional[int] = None
    free: Optional[int] = None
    timestamp: str
    extra: Extra


class Station(BaseModel):
    uid: str = Field(alias="hash")
    name: Optional[str] = None
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
