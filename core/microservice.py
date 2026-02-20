
import grpc
import asyncio
from core.api import FastMVPEngine
class Microservice:
    def __init__(self, name: str, target: str, app: FastMVPEngine, stub_class):
        self.name = name
        self.target = target
        self.app = app.app
        self.engine = app
        self.stub_class = stub_class
        self.channel = None
        self.stub = None
        self.healthy = True
        # Register lifecycle events
        @self.app.on_event("startup")
        async def startup():
            await self.connect()

        @self.app.on_event("shutdown")
        async def shutdown():
            if self.channel:
                await self.channel.close()

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = self.stub_class(self.channel)
        try:
            # Short timeout to ensure we don't hang the whole API boot process
            await asyncio.wait_for(self.channel.channel_ready(), timeout=2.0)
            self.engine.logger.info(f"Connected to {self.name} at {self.target}")
            self.healthy = True
        except Exception as e:
            self.engine.logger.error(f"Could not connect to {self.name}: {e}")
            self.healthy = False

    async def send_req(self, name: str):
        try:
            req = greet_pb2.HelloRequest(name=name)
            if self.stub:
                res = await self.stub.SayHello(req)
                return res
            else:
                self.logger.error(f"gRPC call failed: No self.stub")
        
        except grpc.RpcError as e:
            self.logger.error(f"gRPC call failed: {e.code()} - {e.details()}")
            raise 


