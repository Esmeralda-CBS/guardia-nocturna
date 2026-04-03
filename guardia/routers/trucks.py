from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from typing import Optional
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


def get_active_shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()


@router.get("/camiones")
def list_trucks(request: Request):
    with get_db() as conn:
        trucks = conn.execute("SELECT * FROM trucks ORDER BY name").fetchall()
        active = get_active_shift(conn)
        return templates.TemplateResponse(
            "admin/trucks.html",
            {"request": request, "trucks": trucks, "active_shift": active, "truck_colors": TRUCK_COLORS},
        )


TRUCK_COLORS = [
    ("#fca5a5", "Rojo claro"),
    ("#f9a8d4", "Rosa"),
    ("#93c5fd", "Azul"),
    ("#6ee7b7", "Verde"),
    ("#fde68a", "Amarillo"),
    ("#fdba74", "Naranja"),
    ("#c4b5fd", "Violeta"),
    ("#e5e7eb", "Gris"),
]


@router.post("/camiones/nuevo")
def create_truck(
    name: str = Form(...),
    type_val: Optional[str] = Form(None, alias="type"),
    color: Optional[str] = Form(None),
):
    name = name.strip()
    if name:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO trucks (name, type, color) VALUES (?, ?, ?)",
                (name, type_val or None, color or "#93c5fd"),
            )
    return RedirectResponse("/admin/camiones", status_code=303)


@router.post("/camiones/{truck_id}/color")
def update_truck_color(truck_id: int, color: str = Form(...)):
    with get_db() as conn:
        conn.execute("UPDATE trucks SET color = ? WHERE id = ?", (color, truck_id))
    return RedirectResponse("/admin/camiones", status_code=303)


@router.post("/camiones/{truck_id}/eliminar")
def delete_truck(truck_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM trucks WHERE id = ?", (truck_id,))
    return RedirectResponse("/admin/camiones", status_code=303)
