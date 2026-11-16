"""HTTP adapters for POC-BOOKING-API 0.1.1. Run with python -m uvicorn app.main:app."""
from pathlib import Path
import os
import sqlite3
from typing import Annotated

from fastapi import FastAPI, Request, Response, Path as PathField
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, booking, membership, schedule
from .db import Database, DEFAULT_DB, utc_now
from .errors import BusinessError, error_body
from .models import (BookingInput, LoginInput, TrainingList, MembershipResponse,
                     ReservationList, MutationResult)

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def create_app(db_path=None, clock=utc_now):
    application = FastAPI(title="POC-BOOKING-API", version="0.1.1")
    application.state.db = Database(db_path or os.environ.get("POC_DB_PATH", DEFAULT_DB), clock)
    application.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

    @application.middleware("http")
    async def access_boundary(request, call_next):
        path, method = request.url.path, request.method
        protected = path in ("/trainings", "/memberships/current", "/reservations") or path.startswith("/reservations/")
        session_endpoint = path in ("/login", "/logout") and method == "POST"
        try:
            if protected or session_endpoint:
                context = auth.current_session(application.state.db, request.cookies.get(auth.COOKIE))
                request.state.session = context
                user = auth.user_summary(context)
                request.state.user = user
                if protected and user is None:
                    return JSONResponse(error_body("unauthorized"), status_code=401)
                if protected and path != "/trainings" and user["role"] != "client":
                    return JSONResponse(error_body("forbidden"), status_code=403)
                if method not in ("GET", "HEAD", "OPTIONS") and not auth.valid_csrf(context, request.headers.get("X-CSRF-Token")):
                    return JSONResponse(error_body("csrf_invalid"), status_code=403)
            response = await call_next(request)
        except sqlite3.OperationalError:
            response = JSONResponse(error_body("storage_unavailable"), status_code=503)
        except sqlite3.DatabaseError:
            response = JSONResponse(error_body("internal_error"), status_code=500)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        return response

    @application.exception_handler(BusinessError)
    async def business_error(request, exc):
        return JSONResponse(error_body(exc.code), status_code=exc.status)

    @application.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse(error_body("internal_error"), status_code=500)

    @application.get("/health")
    def health():
        with application.state.db.transaction() as conn:
            conn.execute("SELECT value FROM metadata WHERE key='seeded_at'").fetchone()
            conn.execute("SELECT id FROM reservations LIMIT 1").fetchone()
        return {"status": "ok"}

    @application.get("/session")
    def session(request: Request, response: Response):
        context = auth.current_session(application.state.db, request.cookies.get(auth.COOKIE))
        if context is None:
            csrf = auth.create_session(application.state.db, response)
            return {"user": None, "csrf_token": csrf}
        return {"user": auth.user_summary(context), "csrf_token": context["csrf_token"]}

    @application.post("/login")
    def login(data: LoginInput, request: Request, response: Response):
        user = auth.authenticate(application.state.db, data.username, data.password)
        csrf = auth.create_session(application.state.db, response, user["id"], request.state.session["token_hash"])
        return {"user": user, "csrf_token": csrf}

    @application.post("/logout", status_code=204)
    def logout(request: Request):
        with application.state.db.transaction(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (request.state.session["token_hash"],))
        response = Response(status_code=204)
        response.delete_cookie(auth.COOKIE, path="/", httponly=True, samesite="strict")
        return response

    @application.get("/trainings", response_model=TrainingList)
    def get_trainings(request: Request):
        user = request.state.user
        with application.state.db.transaction() as conn:
            return {"items": schedule.trainings(conn, user["id"] if user["role"] == "client" else None)}

    @application.get("/memberships/current", response_model=MembershipResponse)
    def get_membership(request: Request):
        with application.state.db.transaction() as conn:
            return {"membership": membership.membership_view(conn, request.state.user["id"], application.state.db.clock())}

    @application.get("/reservations", response_model=ReservationList)
    def get_reservations(request: Request):
        with application.state.db.transaction() as conn:
            return {"items": schedule.reservation_history(conn, request.state.user["id"])}

    @application.post("/reservations", status_code=201, response_model=MutationResult)
    def post_reservation(data: BookingInput, request: Request):
        if data.id_klienta != request.state.user["id"]:
            raise BusinessError(403, "client_mismatch")
        return booking.create_reservation(application.state.db, request.state.user["id"], data.id_treningu)

    @application.delete("/reservations/{id_rezervacie}", response_model=MutationResult)
    def delete_reservation(id_rezervacie: Annotated[int, PathField(gt=0)], request: Request):
        return booking.cancel_reservation(application.state.db, request.state.user["id"], id_rezervacie)

    def page(request, name, client_only=False):
        context = auth.current_session(application.state.db, request.cookies.get(auth.COOKIE))
        user = auth.user_summary(context)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if client_only and user["role"] != "client":
            return RedirectResponse("/staff", status_code=303)
        return templates.TemplateResponse(request=request, name=name + ".html", context={"user": user, "page": name})

    @application.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/schedule", status_code=303)

    @application.get("/login", include_in_schema=False)
    def login_page(request: Request):
        return templates.TemplateResponse(request=request, name="login.html", context={"user": None, "page": "login"})

    @application.get("/schedule", include_in_schema=False)
    def schedule_page(request: Request):
        return page(request, "schedule")

    @application.get("/my-reservations", include_in_schema=False)
    def reservations_page(request: Request):
        return page(request, "reservations", client_only=True)

    @application.get("/staff", include_in_schema=False)
    def staff_page(request: Request):
        return page(request, "staff")

    return application


app = create_app()
