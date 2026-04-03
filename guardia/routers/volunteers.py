from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


def get_active_shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()


@router.get("/voluntarios")
def list_volunteers(request: Request):
    with get_db() as conn:
        volunteers = conn.execute(
            "SELECT * FROM volunteers ORDER BY active DESC, name"
        ).fetchall()
        active = get_active_shift(conn)
        return templates.TemplateResponse(
            "admin/volunteers.html",
            {"request": request, "volunteers": volunteers, "active_shift": active},
        )


@router.post("/voluntarios/nuevo")
def create_volunteer(name: str = Form(...)):
    name = name.strip()
    if name:
        with get_db() as conn:
            conn.execute("INSERT INTO volunteers (name) VALUES (?)", (name,))
    return RedirectResponse("/admin/voluntarios", status_code=303)


@router.post("/voluntarios/{vol_id}/toggle")
def toggle_volunteer(vol_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE volunteers SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (vol_id,),
        )
    return RedirectResponse("/admin/voluntarios", status_code=303)


@router.post("/voluntarios/{vol_id}/eliminar")
def delete_volunteer(vol_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM volunteers WHERE id = ?", (vol_id,))
    return RedirectResponse("/admin/voluntarios", status_code=303)
