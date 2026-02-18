from typing import Optional
from sqlmodel import Field, SQLModel

class Logs(SQLModel, table=True):
    id: int
    timestamp: int
    ip: str
    Method: str
    path: str
    status_code: int
    error: str