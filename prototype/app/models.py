from typing import Annotated, Literal
from unicodedata import category, normalize

from pydantic import BaseModel, ConfigDict, Field, field_validator

PositiveID = Annotated[int, Field(strict=True, gt=0)]
AccountNumber = Annotated[int, Field(strict=True, ge=1, le=9007199254740991)]
StaffRole = Literal["trainer", "reception", "admin"]
AccountRole = Literal["client", "trainer", "reception", "admin"]
AccountStatus = Literal["active", "disabled"]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Annotated[str, Field(min_length=1, max_length=80, strict=True)]
    password: Annotated[str, Field(min_length=1, max_length=256, strict=True)]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: Annotated[str, Field(strict=True)]

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value):
        name = value.strip()
        if not 1 <= len(name) <= 80 or any(category(char) in ("Cc", "Cs") for char in value):
            raise ValueError("Enter a display name of 1–80 characters without control characters.")
        return name


class RegistrationInput(ProfileUpdate):
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-z0-9][a-z0-9._-]*$", strict=True)]
    password: Annotated[str, Field(min_length=12, max_length=128, strict=True)]


class StaffRegistration(RegistrationInput):
    role: StaffRole


class AccountVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: AccountNumber


class AccountStatusUpdate(AccountVersionInput):
    status: AccountStatus


class AccountRoleUpdate(AccountVersionInput):
    role: StaffRole


class SessionUser(BaseModel):
    id: PositiveID
    username: str
    role: AccountRole


class SessionView(BaseModel):
    user: SessionUser | None
    csrf_token: str


class LoginView(SessionView):
    user: SessionUser


class AccountView(SessionUser):
    id: AccountNumber
    display_name: str
    status: AccountStatus
    version: AccountNumber


class AccountList(BaseModel):
    items: list[AccountView]


CatalogKind = Literal["trainers", "activities", "rooms"]


def normalize_catalog_name(value):
    return normalize("NFC", value.strip())


class CatalogNameInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(strict=True)]

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        name = normalize_catalog_name(value)
        if not 1 <= len(name) <= 80 or any(category(char) in ("Cc", "Cs") for char in value):
            raise ValueError("Enter a name of 1–80 characters without control characters.")
        return name


class CatalogCreate(CatalogNameInput):
    request_id: Annotated[str, Field(strict=True, pattern=
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]


class CatalogRename(CatalogNameInput, AccountVersionInput):
    pass


class CatalogDeactivate(AccountVersionInput):
    status: Literal["inactive"]


class TrainerLinkUpdate(AccountVersionInput):
    account_id: AccountNumber | None


class CatalogView(BaseModel):
    id: AccountNumber
    name: str
    status: Literal["active", "inactive"]
    version: AccountNumber


class TrainerCatalogView(CatalogView):
    account_id: AccountNumber | None


CatalogEntry = TrainerCatalogView | CatalogView


class CatalogList(BaseModel):
    items: list[CatalogEntry]


class ProfileView(BaseModel):
    id: PositiveID
    username: str
    role: Literal["client"]
    display_name: str


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
