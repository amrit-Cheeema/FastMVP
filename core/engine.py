
from typing import Type, List, TypeVar, Sequence, Callable, Dict, Any, Union
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi import HTTPException, status, Depends, Response
from sqlalchemy.exc import IntegrityError
from core.utils import rename_path_argument
from sqlmodel import Session, SQLModel, create_engine, select
from loguru import logger
import sys
from core.modelRouter import ModelRouter

class FastMVPEngine:
    def __init__(self, name: str, db_name: str = "database"):
        self.engine = create_engine(f"sqlite:///{db_name}.db")
        self.app = FastAPI(title=name)
        self.logger = logger.bind(task="api")
        self._setup_logging()
        self._setup_docs()
        self._setup_db()
        
        
        

    def _setup_docs(self):
        # Instead of calling an external module, we define the route here
        @self.app.get("/apiDocs", include_in_schema=False)
        async def custom_docs_ui():
            return HTMLResponse(f"""
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
                <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
                <style>
                    body {{ margin: 0; }}
                    .container {{ height: 100vh; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <elements-api 
                        apiDescriptionUrl="{self.app.openapi_url}" 
                        router="hash"
                        layout="sidebar"
                    />
                </div>
            </body>
            </html>
            """)

    def _setup_logging(self):
        self.logger.remove()

        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        # 1. Console Output (Shows everything INFO and above)
        self.logger.add(
            sys.stderr, 
            format=log_format,
            level="INFO",
            enqueue=True
        )
        
        # 2. General Log File (All events: INFO, WARNING, ERROR, CRITICAL)
        self.logger.add(
            "logs/api.log",
            format=log_format,
            rotation="10 MB",
            retention="7 days",
            level="INFO",
            filter=lambda record: record["extra"].get("task") == "api",
            enqueue=True
        )
        

        # 3. Error Log File (ONLY ERROR and CRITICAL)
        self.logger.add(
            "logs/api_error.log",
            format=log_format,
            rotation="10 MB",
            retention="30 days", # Usually keep errors longer
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["extra"].get("task") == "api",
            level="ERROR",  # This is the key filter
            enqueue=True
        )

        @self.app.middleware("http")
        async def log_and_catch_middleware(request: Request, call_next):
            path = request.url.path
            method = request.method
            if request.client:
                ip = request.client.host

            with self.logger.catch(reraise=True):
                response = await call_next(request)
                
                # Consume body to log it
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                status_code = response.status_code
                # Assign level based on status
                level = "INFO" if status_code < 400 else "ERROR"
                
                self.logger.log(
                    level, 
                    f"IP: {ip} | {method} {path} | Status: {status_code}"
                )

                return Response(
                    content=response_body,
                    status_code=status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )

    def _setup_db(self):
        @self.logger.catch
        @self.app.on_event("startup")
        def on_startup():
            SQLModel.metadata.create_all(self.engine)

    
    def get_session(self):
        with Session(self.engine) as session:
            yield session
    
    def register_model(self, model_class: Type[SQLModel], name: str):
        return ModelRouter(self.app, model_class, name, self.get_session, self.logger)
    