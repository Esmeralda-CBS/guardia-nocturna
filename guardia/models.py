from pydantic import BaseModel
from typing import Optional


class ShiftCreate(BaseModel):
    date: str
    notes: Optional[str] = None


class VolunteerCreate(BaseModel):
    name: str


class BedCreate(BaseModel):
    number: str
    notes: Optional[str] = None


class TruckCreate(BaseModel):
    name: str
    type: Optional[str] = None


class BedAssignmentCreate(BaseModel):
    volunteer_id: int
    bed_id: int


class TruckAssignmentCreate(BaseModel):
    volunteer_id: int
    truck_id: int
    role: str


class TruckAssignmentUpdateRole(BaseModel):
    assignment_id: int
    role: str
