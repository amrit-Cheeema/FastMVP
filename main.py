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
from contextlib import asynccontextmanager



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
    def __init__(self, target: str):
        self.target = target
        self.channel = None
        self.stub = None

    async def connect(self):
        # Use secure_channel(self.target, grpc.ssl_channel_credentials()) if needed
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = greet_pb2_grpc.GreeterStub(self.channel)
        logger.info(f"gRPC connected to {self.target}")

    async def send_req(self, name: str):
        try:
            req = greet_pb2.HelloRequest(name=name)
            # Ensure we call the stub asynchronously
            if self.stub:
                res = await self.stub.SayHello(req)
                
                
                return res
            else:
                logger.error(f"gRPC call failed: No self.stub")
        except grpc.RpcError as e:
            logger.error(f"gRPC call failed: {e.code()} - {e.details()}")
            raise 

    async def close(self):
        if self.channel:
            await self.channel.close()
            logger.info("gRPC connection closed")

# Initialize the object, but don't connect yet!
grpc_service = Microservice('localhost:50051')

@asynccontextmanager
async def lifespan(app):
    # This happens BEFORE the API starts
    await grpc_service.connect()
    yield
    # This happens AFTER the API stops
    await grpc_service.close()
app.router.lifespan_context = lifespan

@app.get("/BLE/start")
async def start_scan():
    try:
        
        response = await grpc_service.send_req(f"Scan-with-")
        print(response)
        return {"message": response.message, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

