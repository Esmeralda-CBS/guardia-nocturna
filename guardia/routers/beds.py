from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from typing import Optional
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


def get_active_shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()


@router.get("/camas")
def list_beds(request: Request):
    with get_db() as conn:
        beds = conn.execute(
            "SELECT * FROM beds ORDER BY CAST(number AS INTEGER), number"
        ).fetchall()
        active = get_active_shift(conn)
        return templates.TemplateResponse(
            "admin/beds.html",
            {"request": request, "beds": beds, "active_shift": active},
        )


@router.post("/camas/nueva")
def create_bed(
    number: str = Form(...),
    room: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    number = number.strip()
    if number:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO beds (number, room, notes) VALUES (?, ?, ?)",
                (number, room.strip() or None if room else None, notes or None),
            )
    return RedirectResponse("/admin/camas", status_code=303)


@router.post("/camas/{bed_id}/pieza")
def update_bed_room(bed_id: int, room: Optional[str] = Form(None)):
    with get_db() as conn:
        conn.execute(
            "UPDATE beds SET room = ? WHERE id = ?",
            (room.strip() or None if room else None, bed_id),
        )
    return RedirectResponse("/admin/camas", status_code=303)


@router.post("/camas/{bed_id}/eliminar")
def delete_bed(bed_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM beds WHERE id = ?", (bed_id,))
    return RedirectResponse("/admin/camas", status_code=303)
