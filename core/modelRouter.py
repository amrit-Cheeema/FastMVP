from typing import Type, List, TypeVar, Sequence, Callable, Dict, Any, Union
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi import HTTPException, status, Depends, Response
from sqlalchemy.exc import IntegrityError
from core.utils import rename_path_argument
from sqlmodel import Session, SQLModel, create_engine, select

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
                raise HTTPException(status_code=404, detail=f"{self.name} not found")
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
        @self.app.post(f"/models/{self.name}", response_model=self.model, summary=f"POST {self.name}", description=f"Creates a New {self.name} in the database")
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
            204: {
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
            if not result:
                raise HTTPException(status_code=404, detail="Not found")
            # If not found, return 404 with empty body {}
            
            try:
                session.delete(result)
                session.commit()
                
                return Response(status_code=status.HTTP_204_NO_CONTENT)
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
