from core.api import FastMVPEngine
from typing import Optional
from sqlmodel import Field, SQLModel
import importlib
from sqlmodel import Session, select
from typing import Sequence
from fastapi import Depends, Query

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

class HeroBase(SQLModel):
    secret_name: str
    age: Optional[int] = None

# 2. Inherit for the Table (Database)
class Hero(HeroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)

# 3. Inherit for the API (Input)
class HeroAPI(HeroBase):
    pass

api = FastMVPEngine("My api", "db")
app = api.app

def Hero_mapper(incoming: Hero) -> Hero:
    return incoming
v = api.register_model(Hero, "hero").get_all(max=100).post(Hero, Hero_mapper).get(Hero.id, "id").delete(Hero.age, "age")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}