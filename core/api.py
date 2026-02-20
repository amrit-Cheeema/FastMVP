from typing import Type, List, TypeVar, Sequence, Callable, Dict, Any, Union
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi import HTTPException, status, Depends, Response
from sqlalchemy.exc import IntegrityError
from core.utils import rename_path_argument
from sqlmodel import Session, SQLModel, create_engine, select
from loguru import logger
import sys

# T is Database Model (defined at class level)
# S is Request Schema (defined specifically for the post method)
S = TypeVar("S", bound=Any)
T = TypeVar("T", bound=SQLModel)

class ModelRouter:
    """
    Handles dynamic route generation for a specific SQLModel entity.
    
    Attributes:
        app (FastAPI): The FastAPI instance to attach routes to.
        model (Type[T]): The SQLModel class representing the database table.
        name (str): The resource name used in URL paths.
        get_session (Callable): Dependency provider for database sessions.
    """
    def __init__(self, app: FastAPI, model: Type[T], name: str, get_session, logger):
        self.app = app
        self.model = model
        self.name = name
        self.get_session = get_session
        self.routes: List[str] = []
        self.logger = logger
        
    def get(self, lookup_ptr, name: str):
        """
        Registers a GET route to retrieve a single record by a specific field.

        Args:
            lookup_ptr: The model attribute to filter by (e.g., User.id).
            name (str): The name of the path parameter in the URL.
        """
        responses_schema: Dict[Union[int, str], Dict[str, Any]] = {
            404: {
                "description": f"{self.name} not found",
                "content": {"application/json": {}}
            }
        }
        
        async def get(session: Session = Depends(self.get_session), **kwargs):
            lookup_id = kwargs.get(name)
            # lookup_ptr is the model attribute, e.g., self.model.id
            statement = select(self.model).where(lookup_ptr == lookup_id)
            result = session.exec(statement).first()
            
            if not result:
                return Response(content="{}", media_type="application/json", status_code=status.HTTP_404_NOT_FOUND)
                
            return result
        path = f"/models/{self.name}/{{{name}}}"
        rename_path_argument(get, dynamic_name=name)
        self.app.get(path, response_model=self.model, responses=responses_schema)(get)
        return self
    def get_all(self, max:int, offset:int=0, limit:int=100):
        """
        Registers a GET route to retrieve a paginated list of models.

        Args:
            max (int): The absolute maximum number of records allowed per request.
            offset (int, optional): The starting point in the database. Defaults to 0.
            limit (int, optional): The number of records to return. Defaults to 100.

        Returns:
            self: Returns the current instance to allow for method chaining.
        """
        @self.app.get(f"/models/{self.name}", response_model=Sequence[self.model], summary=f"Get All {self.name}s", description=f"Get all {self.name}s in the database. Max number of output = {max}")
        async def get_all(session: Session = Depends(self.get_session), offset: int = offset, limit: int = limit):
            
            if limit > max:
                limit = max
            statement = select(self.model).offset(offset).limit(limit)
            return session.exec(statement).all()
        
        return self

    def post(self, POST: Type[S], request_mapper: Callable[[S], T]):
        """
        Registers a POST route to create a new record.

        Args:
            POST (Type[T]): The Pydantic/SQLModel schema for the request body.
            request_mapper (Callable): Logic to transform the input schema to a DB model.
        """
        @self.app.post(f"/models/{self.name}", response_model=self.model)
        async def create(item: POST, session: Session = Depends(self.get_session)):
            try:
                db_data = request_mapper(item)
                session.add(db_data)
                session.commit()
                session.refresh(db_data)
                return db_data
            except IntegrityError as e:
                session.rollback()
                
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Resource already exists. Unique constraint violation"
                )
            
            except Exception as e:
                session.rollback()
                self.logger.exception("Database transaction failed")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred while creating the record."
                )
        return self
    def delete(self, lookup_ptr, name: str):
        """
        Registers a DELETE route for a specific record.

        Args:
            lookup_ptr: The model attribute to filter by.
            name (str): The name of the path parameter.
        """
        # Docs schema to show the 404 case
        responses_schema: Dict[Union[int, str], Dict[str, Any]] = {
            404: {
                "description": f"{self.name} not found",
                "content": {"application/json": {"example": {}}}
            },
            200: {
                "description": f"Successfully deleted {self.name}",
                "content": {"application/json": {"example": {}}}
            }
        }
        
        async def delete_item(session: Session = Depends(self.get_session), **kwargs):
            """Deletes the first time based on filter"""
            # Find the item first
            lookup_id = kwargs.get(name)
            statement = select(self.model).where(lookup_ptr == lookup_id)
            result = session.exec(statement).first()
            
            # If not found, return 404 with empty body {}
            if not result:
                return Response(
                    content="{}", 
                    media_type="application/json", 
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            try:
                session.delete(result)
                session.commit()
                # Return 200 with empty body {} as requested
                return Response(
                    content="{}", 
                    media_type="application/json", 
                    status_code=status.HTTP_200_OK
                )
            except Exception as e:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error occurred during deletion"
                )
        path = f"/models/{self.name}/{{{name}}}"
        rename_path_argument(delete_item, dynamic_name=name)
        self.app.delete(path, responses=responses_schema)(delete_item)
        return self




class FastMVPEngine:
    def __init__(self, name: str, db_name: str = "database"):
        self.engine = create_engine(f"sqlite:///{db_name}.db")
        self.app = FastAPI(title=name)
        self.logger = logger
        self._setup_logging()
        self._setup_docs()
        self._setup_db()
        self._setup_log_viewer()
        

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
            "app.log",
            format=log_format,
            rotation="10 MB",
            retention="7 days",
            level="INFO",
            enqueue=True
        )

        # 3. Error Log File (ONLY ERROR and CRITICAL)
        self.logger.add(
            "error.log",
            format=log_format,
            rotation="10 MB",
            retention="30 days", # Usually keep errors longer
            backtrace=True,
            diagnose=True,
            level="ERROR",  # This is the key filter
            enqueue=True
        )

        @self.app.middleware("http")
        async def log_and_catch_middleware(request: Request, call_next):
            path = request.url.path
            method = request.method
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

    def _setup_log_viewer(self):
        @self.app.get("/admin/logs", response_class=PlainTextResponse)
        async def view_logs():
            try:
                with open(self.log_file, "r") as f:
                    return f.read()
            except FileNotFoundError:
                return "No logs found yet."
    def get_session(self):
        with Session(self.engine) as session:
            yield session
    
    def register_model(self, model_class: Type[SQLModel], name: str):
        return ModelRouter(self.app, model_class, name, self.get_session, self.logger)