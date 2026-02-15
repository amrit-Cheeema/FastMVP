# FastMVP

FastMVP is a lightweight, high-speed routing engine for Python designed specifically for **rapid prototyping**. It bridges the gap between **SQLModel** and **FastAPI**, allowing you to transform database definitions into fully documented, functional REST APIs with almost zero boilerplate.

## The Problem
When prototyping, you often spend 80% of your time writing the same CRUD (Create, Read, Update, Delete) logic for different tables. FastMVP automates this, letting you focus on your unique business logic while the engine handles the plumbing.

## Core Features
* **Fluent API**: Use method chaining to register routes in a single, readable block.
* **Signature Injection**: Dynamically modifies function signatures so that dynamic path parameters (like `/items/{id}`) show up correctly in Swagger/OpenAPI docs.
* **Schema Agnostic**: Works with any SQLModel definition.
* **Integrated Documentation**: Includes a custom Stoplight Elements UI out of the box.

---

## Technical Example: Rapid Setup

The following snippet demonstrates how to define a model and generate a complete API surface in one go.

```python
from core.api import FastMVPEngine
from typing import Optional, Annotated
from sqlmodel import Field, SQLModel
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

# 1. Define your Database Schema
class HeroBase(SQLModel):
    secret_name: str
    age: Optional[int] = None

class Hero(HeroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)

# 2. Initialize the FastMVP Engine
# This handles FastAPI instantiation and SQLite engine setup
api = FastMVPEngine("HeroService", "dev_db")
app = api.app

# 3. Define a Simple Mapper
# Used to transform incoming API data into Database models
def hero_mapper(incoming: Hero) -> Hero:
    return incoming

# 4. Fluent Route Registration
# This single chain creates GET (all), POST, GET (by id), and DELETE (by age)
api.register_model(Hero, "hero") \
    .get_all(max=100) \
    .post(Hero, hero_mapper) \
    .get(Hero.id, "id") \
    .delete(Hero.age, "age")

# 5. Standard FastAPI Extensibility
# FastMVP is non-intrusive; you can still add custom endpoints and security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}