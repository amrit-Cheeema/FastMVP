import grpc

import asyncio
from core.engine import FastMVPEngine
from loguru import logger
import prpc.greet_pb2 as greet_pb2
import prpc.greet_pb2_grpc as greet_pb2_grpc
from typing import Type, Optional

_GLOBAL_OPEN_LOGS = set()
class Microservice:
    def __init__(self, name: str, target: str, app_engine: FastMVPEngine, proto_pb2_grpc__protoStub: Type[greet_pb2_grpc.GreeterStub]):
        self.name = name
        self.target = target
        self.app = app_engine.app
        self.app_engine = app_engine

        
        self.channel: grpc.aio.Channel | None = None
        self.stub_class = proto_pb2_grpc__protoStub

        self.stub: Optional[greet_pb2_grpc.GreeterStub] = None
        self.healthy = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._setup_logging()
        self._register_lifespan()

    def _setup_logging(self):
        self.logger = logger.bind(service=self.name)
        
        info_path = f"logs/grpc_{self.name}.log"
        error_path = f"logs/grpc_error_{self.name}.log"

        # Only add the file if we haven't added it yet in this process
        if info_path not in _GLOBAL_OPEN_LOGS:
            logger.add(
                info_path,
                filter=lambda record: record["extra"].get("service") == self.name,
                level="INFO",
                rotation="10 MB",
                enqueue=True  # Important for Asyncio!
            )
            _GLOBAL_OPEN_LOGS.add(info_path)

        if error_path not in _GLOBAL_OPEN_LOGS:
            logger.add(
                error_path,
                filter=lambda record: record["extra"].get("service") == self.name,
                level="ERROR",
                rotation="50 MB",
                enqueue=True
            )
            _GLOBAL_OPEN_LOGS.add(error_path)

        
    def _register_lifespan(self):
        @self.app.on_event("startup")
        async def startup():
            self.channel = grpc.aio.insecure_channel(self.target)
            # Instantiate the stub ONCE
            self.stub = self.stub_class(self.channel)
            self._monitor_task = asyncio.create_task(self._maintain_connection())

        @self.app.on_event("shutdown")
        async def shutdown():
            if self._monitor_task:
                self._monitor_task.cancel()
            if self.channel:
                await self.channel.close()

    async def _maintain_connection(self):
        while True:
            try:
                if not self.channel:
                    await asyncio.sleep(1)
                    continue
                state = self.channel.get_state(try_to_connect=True)
                
                is_currently_ready = (state == grpc.ChannelConnectivity.READY)
                
                if is_currently_ready != self.healthy:
                    if is_currently_ready:
                        self.logger.info(f"gRPC Service '{self.name}' is ONLINE.")
                    else:
                        self.logger.error(f"gRPC Service '{self.name}' is OFFLINE (State: {state}).")
                    self.healthy = is_currently_ready
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                await asyncio.sleep(10)

    async def send_req(self, name: str) -> Optional[greet_pb2.HelloReply]:
        # proto_p2b__request
        if not self.healthy:
            self.logger.error(f"Cannot send request: {self.name} is currently disconnected.")
            return None           
        res = None
        try:
            if self.stub:
                res = await self.stub.SayHello(
                    greet_pb2.HelloRequest(name=name), 
                    timeout=5.0
                )
                
            return res
        except grpc.RpcError as e:
            self.logger.error(f"gRPC Error: {e.code()}")
            if e.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
                self.healthy = False
            raise