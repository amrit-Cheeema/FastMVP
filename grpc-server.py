import grpc
from concurrent import futures
from prpc import greet_pb2
from prpc import greet_pb2_grpc
from loguru import logger
import sys

# Configure Loguru for the microservice
logger.remove()
logger.add(sys.stderr, format="<magenta>gRPC</magenta> | <level>{level: <8}</level> | {message}", diagnose=True)

class Greeter(greet_pb2_grpc.GreeterServicer):
    
    @logger.catch
    def SayHello(self, request, context):
        user_name = request.name
        logger.info(f"Received request from: {user_name}")
        
        # Simple logic with a safety check
        if not user_name:
            logger.warning("Empty name received!")
            return greet_pb2.HelloReply(message="Hello, stranger!")
            
        return greet_pb2.HelloReply(message=f"Hello, {user_name}! Your request was logged.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    greet_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
    
    port = "[::]:50051"
    server.add_insecure_port(port)
    logger.info(f"gRPC Server starting on {port}")
    
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")