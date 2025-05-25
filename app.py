import sqlite3
import json
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Erlaubt Anfragen von deinem Vue-Frontend

# Zutatenliste für zufällige Rezepte
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
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabelle für Benutzer erstellen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    # Tabelle für Rezepte anpassen (mit user_id als Fremdschlüssel)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        instructions TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

# Datenbank beim Start initialisieren
init_db()

# Funktion zum Abrufen der DB-Verbindung
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Ermöglicht den Zugriff auf Daten durch Spaltennamen
    return conn

# Alle Zutaten abholen
@app.route("/ingredients", methods=["GET"])
def get_ingredients():
    return jsonify(ingredients)

# Endpoint: Zufälliges Rezept generieren
@app.route("/generate/<int:user_id>", methods=["GET"])
def generate_recipe(user_id):
    # Beispiel Rezeptgenerierung für den User
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

    # Optional: Hier könnte man überprüfen, ob der User existiert, bevor man das Rezept generiert.
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(recipe)

# Alle User abrufen
@app.route("/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])

#Einzelnen User abrufen
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))

# Neuen User registrieren
@app.route("/register", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("name")
    
    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (name) VALUES (?)", (username,))
        conn.commit()
        user_id = conn.execute("SELECT id FROM users WHERE name = ?", (username,)).fetchone()[0]
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    finally:
        conn.close()

    return jsonify({"id": user_id, "name": username})

# Alle Rezepte eines Users abrufen
@app.route("/recipes/<int:user_id>", methods=["GET"])
def get_recipes(user_id):
    conn = get_db_connection()
    recipes = conn.execute("SELECT * FROM recipes WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    # Umwandeln jedes Rezept von sqlite3.Row in ein Dictionary
    recipes_list = []
    for recipe in recipes:
        recipe_dict = dict(recipe)  # Konvertiert das sqlite3.Row in ein Dictionary
        # Umwandeln des gespeicherten JSON-Strings zurück in ein Dictionary für ingredients
        recipe_dict["ingredients"] = json.loads(recipe_dict["ingredients"])
        recipes_list.append(recipe_dict)

    return jsonify(recipes_list)

#Einzelnes Rezept eines Users abrufen
@app.route("/recipes/<int:user_id>/<int:recipe_id>", methods=["GET"])
def get_recipe(user_id, recipe_id):
    conn = get_db_connection()
    recipe = conn.execute("SELECT * FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id)).fetchone()
    conn.close()

    if recipe is None:
        return jsonify({"error": "Recipe not found"}), 404

    # Wandelt die Row in ein Dictionary um
    recipe_dict = dict(recipe)

    # ⚠️ ingredients als JSON-Dict laden!
    if isinstance(recipe_dict.get("ingredients"), str):
        recipe_dict["ingredients"] = json.loads(recipe_dict["ingredients"])

    return jsonify(recipe_dict)

# Rezept speichern
@app.route("/save", methods=["POST"])
def save_recipe():
    data = request.json
    user_id = data.get("user_id")
    title = data.get("title")
    ingredients = data.get("ingredients")
    instructions = data.get("instructions")

    if not user_id or not title or not ingredients or not instructions:
        return jsonify({"error": "Missing data"}), 400

    ingredients_json = json.dumps(ingredients)

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO recipes (user_id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
        (user_id, title, ingredients_json, instructions)
    )
    conn.commit()
    recipe_id = cursor.lastrowid
    conn.close()

    # Sende das neue Rezept zurück, damit das Frontend die ID kennt
    return jsonify({
        "id": recipe_id,
        "user_id": user_id,
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions
    })

# Rezept löschen
@app.route("/delete/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Recipe deleted!"})

if __name__ == "__main__":
    app.run(debug=True)