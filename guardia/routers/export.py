from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


@router.get("/turnos/{shift_id}/exportar")
def export_shift(request: Request, shift_id: int):
    with get_db() as conn:
        shift = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not shift:
            return RedirectResponse("/turnos", status_code=302)

        bed_assignments = conn.execute("""
            SELECT b.number AS bed_number, v.name AS volunteer_name
            FROM bed_assignments ba
            JOIN volunteers v ON ba.volunteer_id = v.id
            JOIN beds b ON ba.bed_id = b.id
            WHERE ba.shift_id = ?
            ORDER BY CAST(b.number AS INTEGER), b.number
        """, (shift_id,)).fetchall()

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
            "export/print.html",
            {
                "request": request,
                "shift": shift,
                "bed_assignments": bed_assignments,
                "trucks": trucks,
                "assignments_by_truck": assignments_by_truck,
            },
        )
