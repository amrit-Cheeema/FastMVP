from typing import Callable
from core.api import FastMVPEngine
from typing import Optional, Annotated
from sqlmodel import Field, SQLModel
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from core.microservice import Microservice
import sys
from contextlib import asynccontextmanager
from prpc import greet_pb2
from prpc import greet_pb2_grpc


# 1. Define your Database Schema
class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: Optional[int] = None

# 2. Inherit for the Table (Database)
class HeroDB(HeroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    secret_name: str


class HeroAPI(HeroBase):
    pass


def Hero_mapper(incoming: HeroAPI) -> HeroDB:
    return HeroDB(
        id=1,
        secret_name="computed secret",
        **incoming.model_dump()
    )


api = FastMVPEngine("HeroService", "dev_db")
app = api.app


api.register_model(HeroDB, "hero") \
    .get_all(max=100) \
    .post(HeroAPI, Hero_mapper) \
    .get(HeroDB.id, "id") \
    .delete(HeroDB.age, "age")


# Initialize the object, but don't connect yet!
grpc_service = Microservice("greeting servic", "localhost:50051", api, greet_pb2_grpc.GreeterStub)

# @asynccontextmanager
# async def lifespan(app):
#     # This happens BEFORE the API starts
#     await grpc_service.connect()
#     yield
#     # This happens AFTER the API stops
#     await grpc_service.close()
# app.router.lifespan_context = lifespan
grpc_service
@app.get("/BLE/start")
async def start_scan():
    try:
        
        response = await grpc_service.send_req(f"Scan-with-")
        print(response)
        return {"message": response.message, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

