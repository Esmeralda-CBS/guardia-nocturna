from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from typing import Optional
from guardia.database import get_db
from guardia.templates_config import templates
from datetime import date

router = APIRouter()


def get_active_shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()


@router.get("/")
def index(request: Request):
    with get_db() as conn:
        active = get_active_shift(conn)
        if active:
            return RedirectResponse(f"/turnos/{active['id']}", status_code=302)
        return RedirectResponse("/turnos", status_code=302)


@router.get("/turnos")
def list_shifts(request: Request):
    with get_db() as conn:
        shifts = conn.execute(
            "SELECT * FROM shifts ORDER BY date DESC, id DESC"
        ).fetchall()
        active = get_active_shift(conn)
        return templates.TemplateResponse(
            "shifts/list.html",
            {"request": request, "shifts": shifts, "active_shift": active},
        )


@router.get("/turnos/nuevo")
def new_shift_form(request: Request):
    with get_db() as conn:
        active = get_active_shift(conn)
        today = date.today().isoformat()
        return templates.TemplateResponse(
            "shifts/new.html",
            {"request": request, "today": today, "active_shift": active},
        )


@router.post("/turnos/nuevo")
def create_shift(
    date_val: str = Form(..., alias="date"),
    notes: Optional[str] = Form(None),
):
    with get_db() as conn:
        # Deactivate all existing shifts
        conn.execute("UPDATE shifts SET is_active = 0")
        cur = conn.execute(
            "INSERT INTO shifts (date, notes, is_active) VALUES (?, ?, 1)",
            (date_val, notes or None),
        )
        shift_id = cur.lastrowid
    return RedirectResponse(f"/turnos/{shift_id}/camas", status_code=303)


@router.get("/turnos/{shift_id}")
def shift_detail(request: Request, shift_id: int):
    with get_db() as conn:
        shift = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not shift:
            return RedirectResponse("/turnos", status_code=302)

        active = get_active_shift(conn)

        bed_assignments = conn.execute("""
            SELECT ba.id, v.name AS volunteer_name, b.number AS bed_number
            FROM bed_assignments ba
            JOIN volunteers v ON ba.volunteer_id = v.id
            JOIN beds b ON ba.bed_id = b.id
            WHERE ba.shift_id = ?
            ORDER BY CAST(b.number AS INTEGER), b.number
        """, (shift_id,)).fetchall()

        trucks = conn.execute("SELECT * FROM trucks ORDER BY name").fetchall()
        truck_assignment_rows = conn.execute("""
            SELECT ta.id, ta.truck_id, ta.role, v.name AS volunteer_name
            FROM truck_assignments ta
            JOIN volunteers v ON ta.volunteer_id = v.id
            WHERE ta.shift_id = ?
            ORDER BY ta.truck_id, v.name
        """, (shift_id,)).fetchall()

        assignments_by_truck = {}
        for a in truck_assignment_rows:
            assignments_by_truck.setdefault(a["truck_id"], []).append(a)

        return templates.TemplateResponse(
            "shifts/detail.html",
            {
                "request": request,
                "shift": shift,
                "active_shift": active,
                "bed_assignments": bed_assignments,
                "trucks": trucks,
                "assignments_by_truck": assignments_by_truck,
            },
        )


@router.post("/turnos/{shift_id}/activar")
def activate_shift(shift_id: int):
    with get_db() as conn:
        conn.execute("UPDATE shifts SET is_active = 0")
        conn.execute("UPDATE shifts SET is_active = 1 WHERE id = ?", (shift_id,))
    return RedirectResponse(f"/turnos/{shift_id}", status_code=303)


@router.post("/turnos/{shift_id}/cerrar")
def close_shift(shift_id: int):
    with get_db() as conn:
        conn.execute("UPDATE shifts SET is_active = 0 WHERE id = ?", (shift_id,))
    return RedirectResponse(f"/turnos/{shift_id}", status_code=303)


@router.post("/turnos/{shift_id}/eliminar")
def delete_shift(shift_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    return RedirectResponse("/turnos", status_code=303)
