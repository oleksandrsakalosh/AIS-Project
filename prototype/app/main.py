"""HTTP adapters for the local sports-centre application."""
from pathlib import Path
import os
import sqlite3
from typing import Annotated

from fastapi import FastAPI, Request, Response, Path as PathField
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import accounts, auth, booking, catalog, membership, schedule, trainer_schedule
from .db import Database, DEFAULT_DB, utc_now
from .errors import BusinessError, error_body
from .models import (BookingInput, LoginInput, TrainingList, MembershipResponse,
                     ReservationList, MutationResult, RegistrationInput, ProfileUpdate, ProfileView,
                     AccountList, AccountView, AccountRoleUpdate, AccountStatusUpdate,
                     LoginView, SessionView, StaffRegistration, CatalogKind, CatalogList,
                     CatalogEntry, CatalogCreate, CatalogRename, CatalogDeactivate,
                     TrainerCatalogView, TrainerLinkUpdate, TrainingCreate, TrainingEdit,
                     TrainingEditorItem, TrainerScheduleView)

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))
REGISTRATION = "/api/account/registration"
PROFILE = "/api/account/profile"
ADMIN = "/api/admin/accounts"
CATALOG = "/api/admin/catalog"
TRAINER_SCHEDULE = "/api/trainer/schedule"
TRAINER_SCHEDULE_PAGE = "/staff/training-schedule"
CLIENT_ROUTES = ("/memberships/current", "/reservations", PROFILE)
ROLE_LABELS = {"client": "Klient", "trainer": "Tréner", "reception": "Recepcia", "admin": "Administrátor"}
AdminID = Annotated[str, PathField(pattern=r"^[0-9]+$")]


def admin_id_number(value):
    digits = value.lstrip("0")
    if not digits or len(digits) > 16 or int(digits) > 9007199254740991:
        raise BusinessError(422, "validation")
    return int(digits)


def create_app(db_path=None, clock=utc_now):
    application = FastAPI(title="POC-BOOKING-API", version="0.4.0")
    application.state.db = Database(db_path or os.environ.get("POC_DB_PATH", DEFAULT_DB), clock)
    db = application.state.db
    application.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

    def storage_error(request, status, code):
        if request.method == "GET" and request.url.path in (
            "/login", "/register", "/profile", "/schedule", "/my-reservations", "/staff",
            "/admin/accounts", "/admin/catalog", TRAINER_SCHEDULE_PAGE,
        ):
            return HTMLResponse(
                '<!doctype html><html lang="sk"><meta charset="utf-8"><title>Údaje sú nedostupné</title>'
                '<main><h1>Údaje sa nepodarilo načítať.</h1><a href="">Obnoviť stránku</a></main></html>',
                status_code=status,
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(error_body(code), status_code=status, headers={"Cache-Control": "no-store"})

    @application.middleware("http")
    async def access_boundary(request, call_next):
        path, method = request.url.path, request.method
        catalog_route = path == CATALOG or path.startswith(CATALOG + "/")
        trainer_route = path == TRAINER_SCHEDULE or path.startswith(TRAINER_SCHEDULE + "/")
        admin = catalog_route or path == ADMIN or path.startswith(ADMIN + "/")
        client_only = path in CLIENT_ROUTES or path.startswith("/reservations/")
        protected = admin or client_only or path == "/trainings"
        signup = path == REGISTRATION and method == "POST"
        session_endpoint = path in ("/login", "/logout") and method == "POST"
        request.state.cookie = request.cookies.get(auth.COOKIE)
        try:
            if trainer_route or protected or session_endpoint or signup:
                if trainer_route:
                    with db.transaction() as conn:
                        context, _, _ = trainer_schedule.access(conn, request.state.cookie, db.clock())
                else:
                    context = auth.current_session(db, request.state.cookie)
                if protected:
                    auth.require_access(context, "admin" if admin else "client" if client_only else None)
                if signup and auth.user_summary(context) is not None:
                    raise BusinessError(403, "already_signed_in")
                if method not in ("GET", "HEAD", "OPTIONS"):
                    auth.require_csrf(context, request.headers.get("X-CSRF-Token"))
                if (admin or trainer_route) and method in ("POST", "PUT"):
                    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if media_type != "application/json":
                        raise BusinessError(422, "validation")
                    if catalog_route or trainer_route:
                        # FastAPI reports undecodable JSON bytes as 400. These writes use 422.
                        try:
                            (await request.body()).decode("utf-8")
                        except UnicodeDecodeError as exc:
                            raise BusinessError(422, "validation") from exc
            response = await call_next(request)
        except BusinessError as exc:
            response = JSONResponse(error_body(exc.code), status_code=exc.status)
        except sqlite3.OperationalError:
            response = storage_error(request, 503, "storage_unavailable")
        except sqlite3.DatabaseError:
            response = storage_error(request, 500, "internal_error")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        return response

    @application.exception_handler(BusinessError)
    async def business_error(request, exc):
        return JSONResponse(error_body(exc.code), status_code=exc.status)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if request.url.path in (REGISTRATION, PROFILE) or request.url.path.startswith((ADMIN, CATALOG, TRAINER_SCHEDULE)):
            # FastAPI's default validation response can include submitted values.
            return JSONResponse(error_body("validation"), status_code=422)
        if request.url.path == "/login":
            # Preserve the existing detail envelope while keeping credential input private.
            details = []
            for error in exc.errors():
                location = error["loc"]
                if location not in (("body", "username"), ("body", "password")):
                    location = ("body",)
                details.append({"loc": location, "type": error["type"], "msg": error["msg"]})
            return JSONResponse({"detail": details}, status_code=422)
        return await request_validation_exception_handler(request, exc)

    @application.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return storage_error(request, 500, "internal_error")

    @application.get("/health")
    def health():
        with application.state.db.transaction() as conn:
            conn.execute("SELECT value FROM metadata WHERE key='seeded_at'").fetchone()
            conn.execute("SELECT id FROM reservations LIMIT 1").fetchone()
        return {"status": "ok"}

    @application.get("/session", response_model=SessionView)
    def session(request: Request, response: Response):
        context = auth.current_session(db, request.state.cookie)
        if context is None:
            with db.transaction(write=True) as conn:
                token, csrf = auth.start_session(conn, db.clock())
            auth.set_session_cookie(response, token)
            return {"user": None, "csrf_token": csrf}
        return {"user": auth.user_summary(context), "csrf_token": context["csrf_token"]}

    @application.post("/login", response_model=LoginView)
    def login(data: LoginInput, request: Request, response: Response):
        user, token, csrf = auth.login(db, request.state.cookie, request.headers.get("X-CSRF-Token"),
                                       data.username, data.password)
        auth.set_session_cookie(response, token)
        return {"user": user, "csrf_token": csrf}

    @application.post("/logout", status_code=204)
    def logout(request: Request):
        with db.transaction(write=True) as conn:
            context = auth.session_context(conn, request.state.cookie, db.clock())
            auth.require_csrf(context, request.headers.get("X-CSRF-Token"))
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (context["token_hash"],))
        response = Response(status_code=204)
        response.delete_cookie(auth.COOKIE, path="/", httponly=True, samesite="strict")
        return response

    @application.post(REGISTRATION, status_code=201, include_in_schema=False)
    def register(data: RegistrationInput):
        accounts.register(application.state.db, data.username, data.password, data.display_name)
        return {"username": data.username}

    @application.get(PROFILE, response_model=ProfileView, include_in_schema=False)
    def get_profile(request: Request):
        return accounts.profile(db, request.state.cookie)

    @application.put(PROFILE, response_model=ProfileView, include_in_schema=False)
    def update_profile(data: ProfileUpdate, request: Request):
        return accounts.update_display_name(db, request.state.cookie, data.display_name)

    @application.get(ADMIN, response_model=AccountList)
    def admin_list(request: Request):
        return {"items": accounts.list_accounts(db, request.state.cookie)}

    @application.post(ADMIN, status_code=201, response_model=AccountView)
    def admin_create(data: StaffRegistration, request: Request):
        return accounts.provision_staff(db, request.state.cookie, data)

    @application.put(ADMIN + "/{account_id}/status", response_model=AccountView)
    def admin_status(account_id: AdminID, data: AccountStatusUpdate, request: Request):
        return accounts.change_account(db, request.state.cookie, admin_id_number(account_id),
                                       data.expected_version, status=data.status)

    @application.put(ADMIN + "/{account_id}/role", response_model=AccountView)
    def admin_role(account_id: AdminID, data: AccountRoleUpdate, request: Request):
        return accounts.change_account(db, request.state.cookie, admin_id_number(account_id),
                                       data.expected_version, role=data.role)

    @application.get(CATALOG + "/{kind}", response_model=CatalogList)
    def catalog_list(kind: CatalogKind, request: Request):
        return {"items": catalog.list_entries(db, request.state.cookie, kind)}

    @application.post(CATALOG + "/{kind}", status_code=201, response_model=CatalogEntry)
    def catalog_create(kind: CatalogKind, data: CatalogCreate, request: Request):
        return catalog.create_entry(db, request.state.cookie, kind, data)

    @application.put(CATALOG + "/{kind}/{entry_id}/name", response_model=CatalogEntry)
    def catalog_rename(kind: CatalogKind, entry_id: AdminID, data: CatalogRename, request: Request):
        return catalog.rename_entry(db, request.state.cookie, kind, admin_id_number(entry_id), data)

    @application.put(CATALOG + "/{kind}/{entry_id}/status", response_model=CatalogEntry)
    def catalog_deactivate(kind: CatalogKind, entry_id: AdminID, data: CatalogDeactivate, request: Request):
        return catalog.deactivate_entry(db, request.state.cookie, kind, admin_id_number(entry_id), data)

    @application.put(CATALOG + "/trainers/{entry_id}/account", response_model=TrainerCatalogView)
    def catalog_link(entry_id: AdminID, data: TrainerLinkUpdate, request: Request):
        return catalog.change_trainer_link(db, request.state.cookie, admin_id_number(entry_id), data)

    @application.get(TRAINER_SCHEDULE, response_model=TrainerScheduleView)
    def trainer_snapshot(request: Request):
        return trainer_schedule.snapshot(db, request.state.cookie)

    @application.post(TRAINER_SCHEDULE, status_code=201, response_model=TrainingEditorItem)
    def trainer_create(data: TrainingCreate, request: Request):
        return trainer_schedule.create(db, request.state.cookie, request.headers.get("X-CSRF-Token"), data)

    @application.put(TRAINER_SCHEDULE + "/{id_treningu}", response_model=TrainingEditorItem)
    def trainer_edit(id_treningu: AdminID, data: TrainingEdit, request: Request):
        return trainer_schedule.edit(db, request.state.cookie, request.headers.get("X-CSRF-Token"),
                                     admin_id_number(id_treningu), data)

    @application.get("/trainings", response_model=TrainingList)
    def get_trainings(request: Request):
        with db.transaction() as conn:
            user = auth.authorize(conn, request.state.cookie, db.clock())
            return {"items": schedule.trainings(conn, user["id"] if user["role"] == "client" else None)}

    @application.get("/memberships/current", response_model=MembershipResponse)
    def get_membership(request: Request):
        with db.transaction() as conn:
            now = db.clock()
            user = auth.authorize(conn, request.state.cookie, now, "client")
            return {"membership": membership.membership_view(conn, user["id"], now)}

    @application.get("/reservations", response_model=ReservationList)
    def get_reservations(request: Request):
        with db.transaction() as conn:
            user = auth.authorize(conn, request.state.cookie, db.clock(), "client")
            return {"items": schedule.reservation_history(conn, user["id"])}

    @application.post("/reservations", status_code=201, response_model=MutationResult)
    def post_reservation(data: BookingInput, request: Request):
        return booking.create_reservation(db, request.state.cookie, data.id_klienta, data.id_treningu)

    @application.delete("/reservations/{id_rezervacie}", response_model=MutationResult)
    def delete_reservation(id_rezervacie: Annotated[int, PathField(gt=0)], request: Request):
        return booking.cancel_reservation(db, request.state.cookie, id_rezervacie)

    def page(request, name, audience=None):
        context = auth.current_session(db, request.state.cookie)
        user = auth.user_summary(context)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if audience == "client" and user["role"] != "client":
            return RedirectResponse("/staff", status_code=303)
        if audience in ("staff", "admin", "trainer") and user["role"] == "client":
            return RedirectResponse("/schedule", status_code=303)
        if audience in ("admin", "trainer") and user["role"] != audience:
            return RedirectResponse("/staff", status_code=303)
        return templates.TemplateResponse(request=request, name=name + ".html",
                                          context={"user": user, "page": name, "role_labels": ROLE_LABELS})

    @application.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/schedule", status_code=303)

    @application.get("/login", include_in_schema=False)
    def login_page(request: Request):
        return templates.TemplateResponse(request=request, name="login.html", context={"user": None, "page": "login"})

    @application.get("/register", include_in_schema=False)
    def registration_page(request: Request):
        session = auth.current_session(application.state.db, request.cookies.get(auth.COOKIE))
        user = auth.user_summary(session)
        if user:
            return RedirectResponse("/schedule" if user["role"] == "client" else "/staff", status_code=303)
        return templates.TemplateResponse(request=request, name="register.html", context={"user": None, "page": "register"})

    @application.get("/profile", include_in_schema=False)
    def profile_page(request: Request):
        return page(request, "profile", "client")

    @application.get("/schedule", include_in_schema=False)
    def schedule_page(request: Request):
        return page(request, "schedule")

    @application.get("/my-reservations", include_in_schema=False)
    def reservations_page(request: Request):
        return page(request, "reservations", "client")

    @application.get("/staff", include_in_schema=False)
    def staff_page(request: Request):
        return page(request, "staff", "staff")

    @application.get(TRAINER_SCHEDULE_PAGE, include_in_schema=False)
    def trainer_schedule_page(request: Request):
        return page(request, "trainer-schedule", "trainer")

    @application.get("/admin/accounts", include_in_schema=False)
    def admin_page(request: Request):
        return page(request, "admin", "admin")

    @application.get("/admin/catalog", include_in_schema=False)
    def catalog_page(request: Request):
        return page(request, "catalog", "admin")

    return application


app = create_app()
