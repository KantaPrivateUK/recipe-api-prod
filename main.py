import sqlite3
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
DB_NAME = "recipes.db"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": "Recipe creation failed!", "detail": str(exc)},
    )

class RecipeCreate(BaseModel):
    title: str
    making_time: str
    serves: str
    ingredients: str
    cost: int

class RecipeResponse(RecipeCreate):
    id: int
    created_at: str
    updated_at: str


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS recipes")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        making_time TEXT NOT NULL,
        serves TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        cost INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    initial_data = [
        (1, 'チキンカレー', '45分', '4人', '玉ねぎ,肉,スパイス', 1000, '2016-01-10 12:10:12', '2016-01-10 12:10:12'),
        (2, 'オムライス', '30分', '2人', '玉ねぎ,卵,スパイス,醤油', 700, '2016-01-11 13:10:12', '2016-01-11 13:10:12')
    ]
    cursor.executemany("""
    INSERT INTO recipes (id, title, making_time, serves, ingredients, cost, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, initial_data)
    
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = dict_factory
    return conn

def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# API
# 1. GET /recipes
@app.get("/recipes")
def get_recipes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    conn.close()
    return {"recipes": recipes}

# 2. POST /recipes
@app.post("/recipes")
def create_recipe(recipe: RecipeCreate):
    conn = get_db()
    cursor = conn.cursor()
    now = get_current_time()
    
    try:
        cursor.execute("""
            INSERT INTO recipes (title, making_time, serves, ingredients, cost, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (recipe.title, recipe.making_time, recipe.serves, recipe.ingredients, recipe.cost, now, now))
        conn.commit()
        new_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (new_id,))
        new_recipe = cursor.fetchone()
        
        return {
            "message": "Recipe successfully created!",
            "recipe": [new_recipe]
        }
    finally:
        conn.close()

# 3. GET /recipes/{id}
@app.get("/recipes/{recipe_id}")
def get_recipe_detail(recipe_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    conn.close()
    
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    return {
        "message": "Recipe details by id",
        "recipe": [recipe]
    }

# 4. PATCH /recipes/{id}
@app.patch("/recipes/{recipe_id}")
def update_recipe(recipe_id: int, recipe_update: RecipeCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    existing = cursor.fetchone()
    
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")

    now = get_current_time()
    try:
        cursor.execute("""
            UPDATE recipes 
            SET title=?, making_time=?, serves=?, ingredients=?, cost=?, updated_at=?
            WHERE id=?
        """, (recipe_update.title, recipe_update.making_time, recipe_update.serves, 
              recipe_update.ingredients, recipe_update.cost, now, recipe_id))
        conn.commit()
        
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        updated_recipe = cursor.fetchone()
        
        return {
            "message": "Recipe successfully updated!",
            "recipe": [updated_recipe]
        }
    finally:
        conn.close()

# 5. DELETE /recipes/{id}
@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return {"message": "Recipe successfully removed!"}