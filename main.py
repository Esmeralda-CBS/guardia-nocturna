import socket
import uvicorn
from fastapi import FastAPI

from guardia.database import init_db
from guardia.routers import shifts, volunteers, beds, trucks, assignments, export, tv

app = FastAPI(title="Guardia Nocturna")


@app.on_event("startup")
def startup():
    init_db()


app.include_router(shifts.router)
app.include_router(volunteers.router, prefix="/admin")
app.include_router(beds.router, prefix="/admin")
app.include_router(trucks.router, prefix="/admin")
app.include_router(assignments.router)
app.include_router(export.router)
app.include_router(tv.router)


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = get_local_ip()
    print("\n" + "=" * 50)
    print("  GUARDIA NOCTURNA")
    print(f"  Local:      http://localhost:8000")
    print(f"  Red local:  http://{ip}:8000")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
