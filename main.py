from typing import Callable
from core.api import FastMVPEngine
from typing import Optional, Annotated
from sqlmodel import Field, SQLModel
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from prpc import greet_pb2
from prpc import greet_pb2_grpc
import grpc
from loguru import logger
import sys

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

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    with logger.catch(reraise=True):
        return await call_next(request)

api.register_model(HeroDB, "hero") \
    .get_all(max=100) \
    .post(HeroAPI, Hero_mapper) \
    .get(HeroDB.id, "id") \
    .delete(HeroDB.age, "age")

class Microservice:
    def __init__(self):
        pass
    def get(self, handler: Callable):
        pass

def run():
    # Use 'insecure_channel' for local development
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = greet_pb2_grpc.GreeterStub(channel)
        response = stub.SayHello(greet_pb2.HelloRequest(name="hello"))
        print(response)
        # response = stub.SayHello(request) # Uncomment when server is running

run()

@app.get("/BLE/start")
async def start_scan(timout: int):

    return
