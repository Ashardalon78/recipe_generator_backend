import sqlite3
import json
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Erlaubt Anfragen von deinem Vue-Frontend

# DATA_FILE = "recipes.json"

with open('ingredients.json', 'r') as ifile:
    ingredients = json.load(ifile)

# Speicherort innerhalb des Projektordners
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Holt den Ordner von app.py
DB_DIR = os.path.join(BASE_DIR, "data")  # /data liegt jetzt im Projektordner
DB_PATH = os.path.join(DB_DIR, "recipes.db")  # Finaler Pfad zur SQLite-Datei

# Stelle sicher, dass das Verzeichnis existiert
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)
    print(f"Verzeichnis {DB_DIR} wurde erstellt!")

print(DB_DIR)

def init_db():
    """Erstellt die Tabelle, falls sie nicht existiert."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            ingredients TEXT,
            instructions TEXT
        )
    """)
    conn.commit()
    conn.close()

# Datenbank beim Start initialisieren
init_db()

# # Rezepte aus Datei laden
# def load_recipes():
#     if not os.path.exists(DATA_FILE):
#         return []
#     with open(DATA_FILE, "r", encoding="utf-8") as file:
#         return json.load(file)

# # Rezepte speichern
# def save_recipes(recipes):
#     with open(DATA_FILE, "w", encoding="utf-8") as file:
#         json.dump(recipes, file, indent=2)

# Endpoint: Zufälliges Rezept generieren
@app.route("/generate", methods=["GET"])
def generate_recipe():
    recipe = {
        "title": "Neues Rezept",
        "ingredients": {
            "vegetables": random.choice(ingredients["vegetables"]),
            "proteins": random.choice(ingredients["proteins"]),
            "carbs": random.choice(ingredients["carbs"]),
            "fats": random.choice(ingredients["fats"])
        },
        "instructions": "Zubereitung..."
    }
    return jsonify(recipe)

# Endpoint: Rezept speichern
@app.route("/save", methods=["POST"])
def save_recipe():
    data = request.json
    title = data.get("title", "Rezept")
    ingredients = str(data.get("ingredients", {}))  # Dict als String speichern
    instructions = data.get("instructions", "")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
                   (title, ingredients, instructions))
    conn.commit()
    conn.close()

    return jsonify({"message": "Rezept gespeichert!"}), 201

# Endpoint: Gespeicherte Rezepte laden
@app.route("/load", methods=["GET"])
def load_saved_recipes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, ingredients, instructions FROM recipes")
    recipes = [{"id": row[0], "title": row[1], "ingredients": eval(row[2]), "instructions": row[3]} for row in cursor.fetchall()]
    conn.close()

    return jsonify(recipes)

# Endpoint: Rezept löschen
@app.route("/delete/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Rezept gelöscht!"})

if __name__ == "__main__":
    app.run(debug=True)