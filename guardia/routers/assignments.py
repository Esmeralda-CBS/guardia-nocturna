from typing import List

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


def get_active_shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()


# ── BED ASSIGNMENTS ──────────────────────────────────────────────────────────

@router.get("/turnos/{shift_id}/camas")
def bed_assignment_screen(request: Request, shift_id: int):
    with get_db() as conn:
        shift = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not shift:
            return RedirectResponse("/turnos", status_code=302)

        active = get_active_shift(conn)
        all_volunteers = conn.execute(
            "SELECT * FROM volunteers WHERE active = 1 ORDER BY name"
        ).fetchall()
        permanent_volunteers = [v for v in all_volunteers if v["permanent"]]
        other_volunteers = [v for v in all_volunteers if not v["permanent"]]
        beds = conn.execute(
            "SELECT * FROM beds ORDER BY CAST(number AS INTEGER), number"
        ).fetchall()

        # Build lookup: bed_id -> volunteer, volunteer_id -> bed
        bed_to_vol = {}
        vol_to_bed = {}
        assignments = conn.execute(
            """SELECT ba.volunteer_id, ba.bed_id, v.name AS volunteer_name
               FROM bed_assignments ba
               JOIN volunteers v ON ba.volunteer_id = v.id
               WHERE ba.shift_id = ?""",
            (shift_id,),
        ).fetchall()
        for a in assignments:
            bed_to_vol[a["bed_id"]] = a["volunteer_name"]
            vol_to_bed[a["volunteer_id"]] = a["bed_id"]

        return templates.TemplateResponse(
            "assignments/beds.html",
            {
                "request": request,
                "shift": shift,
                "active_shift": active,
                "permanent_volunteers": permanent_volunteers,
                "other_volunteers": other_volunteers,
                "beds": beds,
                "bed_to_vol": bed_to_vol,
                "vol_to_bed": vol_to_bed,
            },
        )


@router.post("/turnos/{shift_id}/camas/asignar")
def assign_bed(
    shift_id: int,
    volunteer_id: int = Form(...),
    bed_id: int = Form(...),
):
    with get_db() as conn:
        # Remove any existing assignment for this volunteer in this shift
        conn.execute(
            "DELETE FROM bed_assignments WHERE shift_id = ? AND volunteer_id = ?",
            (shift_id, volunteer_id),
        )
        # Remove any existing assignment for this bed in this shift
        conn.execute(
            "DELETE FROM bed_assignments WHERE shift_id = ? AND bed_id = ?",
            (shift_id, bed_id),
        )
        conn.execute(
            "INSERT INTO bed_assignments (shift_id, volunteer_id, bed_id) VALUES (?, ?, ?)",
            (shift_id, volunteer_id, bed_id),
        )
    return RedirectResponse(f"/turnos/{shift_id}/camas", status_code=303)


@router.post("/turnos/{shift_id}/camas/quitar")
def remove_bed_assignment(
    shift_id: int,
    volunteer_id: int = Form(...),
):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM bed_assignments WHERE shift_id = ? AND volunteer_id = ?",
            (shift_id, volunteer_id),
        )
    return RedirectResponse(f"/turnos/{shift_id}/camas", status_code=303)


# ── TRUCK ASSIGNMENTS ─────────────────────────────────────────────────────────

@router.get("/turnos/{shift_id}/camiones")
def truck_assignment_screen(request: Request, shift_id: int):
    with get_db() as conn:
        shift = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not shift:
            return RedirectResponse("/turnos", status_code=302)

        active = get_active_shift(conn)
        trucks = conn.execute("SELECT * FROM trucks ORDER BY name").fetchall()
        volunteers = conn.execute(
            "SELECT * FROM volunteers WHERE active = 1 ORDER BY name"
        ).fetchall()
        roles = [
            r["name"]
            for r in conn.execute("SELECT name FROM roles ORDER BY sort_order, name").fetchall()
        ]

        # Assignments per truck
        truck_assignments = conn.execute("""
            SELECT ta.id, ta.truck_id, ta.role, ta.volunteer_id, v.name AS volunteer_name
            FROM truck_assignments ta
            JOIN volunteers v ON ta.volunteer_id = v.id
            WHERE ta.shift_id = ?
            ORDER BY ta.truck_id, v.name
        """, (shift_id,)).fetchall()

        # Group by truck_id
        assignments_by_truck = {}
        for a in truck_assignments:
            assignments_by_truck.setdefault(a["truck_id"], []).append(a)

        # Enabled status per truck for this shift (absent row = enabled)
        st_rows = conn.execute(
            "SELECT truck_id, enabled FROM shift_trucks WHERE shift_id = ?", (shift_id,)
        ).fetchall()
        truck_enabled = {r["truck_id"]: bool(r["enabled"]) for r in st_rows}

        return templates.TemplateResponse(
            "assignments/trucks.html",
            {
                "request": request,
                "shift": shift,
                "active_shift": active,
                "trucks": trucks,
                "volunteers": volunteers,
                "assignments_by_truck": assignments_by_truck,
                "roles": roles,
                "truck_enabled": truck_enabled,
            },
        )


@router.post("/turnos/{shift_id}/camiones/asignar")
def assign_truck(
    shift_id: int,
    volunteer_id: int = Form(...),
    truck_id: int = Form(...),
    roles: List[str] = Form(default=[]),
):
    role_str = ",".join(roles)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO truck_assignments (shift_id, volunteer_id, truck_id, role) VALUES (?, ?, ?, ?)",
            (shift_id, volunteer_id, truck_id, role_str),
        )
    return RedirectResponse(f"/turnos/{shift_id}/camiones", status_code=303)


@router.post("/turnos/{shift_id}/camiones/quitar")
def remove_truck_assignment(
    shift_id: int,
    assignment_id: int = Form(...),
):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM truck_assignments WHERE id = ? AND shift_id = ?",
            (assignment_id, shift_id),
        )
    return RedirectResponse(f"/turnos/{shift_id}/camiones", status_code=303)


@router.post("/turnos/{shift_id}/camiones/{truck_id}/toggle")
def toggle_truck(shift_id: int, truck_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT enabled FROM shift_trucks WHERE shift_id = ? AND truck_id = ?",
            (shift_id, truck_id),
        ).fetchone()
        if row is None:
            # Default is enabled; first toggle → disable
            conn.execute(
                "INSERT INTO shift_trucks (shift_id, truck_id, enabled) VALUES (?, ?, 0)",
                (shift_id, truck_id),
            )
        else:
            conn.execute(
                "UPDATE shift_trucks SET enabled = ? WHERE shift_id = ? AND truck_id = ?",
                (0 if row["enabled"] else 1, shift_id, truck_id),
            )
    return RedirectResponse(f"/turnos/{shift_id}/camiones", status_code=303)


@router.post("/turnos/{shift_id}/camiones/rol")
def update_truck_role(
    shift_id: int,
    assignment_id: int = Form(...),
    roles: List[str] = Form(default=[]),
):
    role_str = ",".join(roles)
    with get_db() as conn:
        conn.execute(
            "UPDATE truck_assignments SET role = ? WHERE id = ? AND shift_id = ?",
            (role_str, assignment_id, shift_id),
        )
    return RedirectResponse(f"/turnos/{shift_id}/camiones", status_code=303)
