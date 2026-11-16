from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

PositiveID = Annotated[int, Field(strict=True, gt=0)]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Annotated[str, Field(min_length=1, max_length=80, strict=True)]
    password: Annotated[str, Field(min_length=1, max_length=256, strict=True)]


class BookingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_klienta: PositiveID
    id_treningu: PositiveID


class TrainingView(BaseModel):
    id_treningu: int
    aktivita: str
    trener: str
    priestor: str
    starts_at: str
    ends_at: str
    kapacita: int
    obsadene: int
    volne_miesta: int
    moja_rezervacia_id: int | None


class TrainingList(BaseModel):
    items: list[TrainingView]


class MembershipView(BaseModel):
    id_clenstva: int
    typ: str
    stav: Literal["active", "pending", "expired"]
    valid_from: str
    valid_until: str


class MembershipResponse(BaseModel):
    membership: MembershipView | None


class ReservationView(BaseModel):
    id_rezervacie: int
    id_treningu: int
    stav: Literal["confirmed", "cancelled"]
    created_at: str
    cancelled_at: str | None
    training: TrainingView


class ReservationList(BaseModel):
    items: list[ReservationView]


class MutationResult(BaseModel):
    id_rezervacie: int
    stav: Literal["confirmed", "cancelled"]
