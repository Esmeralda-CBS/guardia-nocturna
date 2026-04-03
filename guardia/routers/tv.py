from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


@router.get("/turnos/{shift_id}/tv")
def tv_display(request: Request, shift_id: int):
    with get_db() as conn:
        shift = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not shift:
            return RedirectResponse("/turnos", status_code=302)

        # Bed assignments with room info
        bed_assignments = conn.execute("""
            SELECT b.id AS bed_id, b.number AS bed_number, b.room,
                   v.name AS volunteer_name
            FROM beds b
            LEFT JOIN bed_assignments ba ON ba.bed_id = b.id AND ba.shift_id = ?
            LEFT JOIN volunteers v ON ba.volunteer_id = v.id
            ORDER BY CAST(b.room AS INTEGER), b.room, CAST(b.number AS INTEGER), b.number
        """, (shift_id,)).fetchall()

        # Group beds by room
        rooms = {}
        no_room_beds = []
        for b in bed_assignments:
            if b["room"]:
                rooms.setdefault(b["room"], []).append(b)
            else:
                no_room_beds.append(b)

        # Sort rooms numerically where possible
        def room_sort_key(r):
            try:
                return (0, int(r))
            except ValueError:
                return (1, r)

        sorted_rooms = sorted(rooms.keys(), key=room_sort_key)

        # Trucks with their assignments
        trucks = conn.execute("SELECT * FROM trucks ORDER BY name").fetchall()
        truck_assignments = conn.execute("""
            SELECT ta.truck_id, ta.role, v.name AS volunteer_name
            FROM truck_assignments ta
            JOIN volunteers v ON ta.volunteer_id = v.id
            WHERE ta.shift_id = ?
            ORDER BY ta.truck_id, v.name
        """, (shift_id,)).fetchall()

        assignments_by_truck = {}
        for a in truck_assignments:
            assignments_by_truck.setdefault(a["truck_id"], []).append(a)

        return templates.TemplateResponse(
            "tv.html",
            {
                "request": request,
                "shift": shift,
                "rooms": rooms,
                "sorted_rooms": sorted_rooms,
                "no_room_beds": no_room_beds,
                "trucks": trucks,
                "assignments_by_truck": assignments_by_truck,
            },
        )


@router.get("/tv")
def tv_active(request: Request):
    """Redirect to the active shift TV view, or to shift list if none active."""
    with get_db() as conn:
        active = conn.execute("SELECT id FROM shifts WHERE is_active = 1").fetchone()
        if active:
            return RedirectResponse(f"/turnos/{active['id']}/tv", status_code=302)
        return RedirectResponse("/turnos", status_code=302)
