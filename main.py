from core.api import FastMVPEngine
from typing import Optional, Annotated
from sqlmodel import Field, SQLModel
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

# 1. Define your Database Schema
class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: Optional[int] = None

# 2. Inherit for the Table (Database)
class HeroDB(HeroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    secret_name: str

# 3. Inherit for the API (Input)
class HeroAPI(HeroBase):
    pass

# 3. Define a Simple Mapper
# Used to transform incoming API data into Database models
def Hero_mapper(incoming: HeroAPI) -> HeroDB:
    return HeroDB(
        id=1,
        secret_name="computed secret",
        **incoming.model_dump()
    )

# 2. Initialize the FastMVP Engine
# This handles FastAPI instantiation and SQLite engine setup
api = FastMVPEngine("HeroService", "dev_db")
app = api.app

# 4. Fluent Route Registration
# This single chain creates GET (all), POST, GET (by id), and DELETE (by age)
api.register_model(HeroDB, "hero") \
    .get_all(max=100) \
    .post(HeroAPI, Hero_mapper) \
    .get(HeroDB.id, "id") \
    .delete(HeroDB.age, "age")

# 5. Standard FastAPI Extensibility
# FastMVP is non-intrusive; you can still add custom endpoints and security


@app.get("/BLE/start")
async def start_scan(timout: int):
    
    return
