from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from guardia.database import get_db
from guardia.templates_config import templates

router = APIRouter()


@router.get("/funciones")
def list_roles(request: Request):
    with get_db() as conn:
        roles = conn.execute("SELECT * FROM roles ORDER BY sort_order, name").fetchall()
        active = conn.execute("SELECT * FROM shifts WHERE is_active = 1").fetchone()
        return templates.TemplateResponse(
            "admin/roles.html",
            {"request": request, "roles": roles, "active_shift": active},
        )


@router.post("/funciones/nuevo")
def create_role(name: str = Form(...)):
    name = name.strip()
    if name:
        with get_db() as conn:
            max_order = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM roles").fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO roles (name, sort_order) VALUES (?, ?)",
                (name, max_order + 1),
            )
    return RedirectResponse("/admin/funciones", status_code=303)


@router.post("/funciones/{role_id}/eliminar")
def delete_role(role_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    return RedirectResponse("/admin/funciones", status_code=303)
