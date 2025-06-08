import psycopg2
from psycopg2 import IntegrityError
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

# Funktion zum Abrufen der DB-Verbindung
def get_db_connection():
    return psycopg2.connect(
        host="db.fahadbyewpapvgjpghmh.supabase.co",
        dbname="postgres",
        user="postgres",
        password="lZIzIXcPVCPTiZDH",
        port=5432
    )

# Alle Zutaten abholen
@app.route("/ingredients", methods=["GET"])
def get_ingredients():
    return jsonify(ingredients)

# Endpoint: Zufälliges Rezept generieren
@app.route("/generate/<int:user_id>", methods=["GET"])
def generate_recipe(user_id):
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

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(recipe)

# Alle User abrufen
@app.route("/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return jsonify([dict(zip(column_names, row)) for row in users])

# Einzelnen User abrufen
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    column_names = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    if row is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(zip(column_names, row)))

# Neuen User registrieren
@app.route("/register", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("name")

    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (name) VALUES (%s)", (username,))
        conn.commit()
        cur.execute("SELECT id FROM users WHERE name = %s", (username,))
        user_id = cur.fetchone()[0]
    except IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    finally:
        cur.close()
        conn.close()

    return jsonify({"id": user_id, "name": username})

# Alle Rezepte eines Users abrufen
@app.route("/recipes/<int:user_id>", methods=["GET"])
def get_recipes(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()

    recipes_list = []
    for row in rows:
        recipe_dict = dict(zip(column_names, row))
        recipe_dict["ingredients"] = json.loads(recipe_dict["ingredients"])
        recipes_list.append(recipe_dict)

    return jsonify(recipes_list)

# Einzelnes Rezept eines Users abrufen
@app.route("/recipes/<int:user_id>/<int:recipe_id>", methods=["GET"])
def get_recipe(user_id, recipe_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recipes WHERE id = %s AND user_id = %s", (recipe_id, user_id))
    row = cur.fetchone()
    column_names = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()

    if row is None:
        return jsonify({"error": "Recipe not found"}), 404

    recipe_dict = dict(zip(column_names, row))

    if isinstance(recipe_dict.get("ingredients"), str):
        recipe_dict["ingredients"] = json.loads(recipe_dict["ingredients"])

    return jsonify(recipe_dict)

# Rezepte gefiltert nach Zutaten abrufen
@app.route("/filters/<int:user_id>", methods=["GET"])
def get_filter_options(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT ingredients FROM recipes WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    categories = {
        "vegetables": set(),
        "proteins": set(),
        "carbs": set(),
        "fats": set()
    }

    for row in rows:
        ingredients = json.loads(row[0])
        for cat in categories:
            value = ingredients.get(cat)
            if value:
                categories[cat].add(value)

    result = {k: sorted(list(v)) for k, v in categories.items()}
    return jsonify(result)

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
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recipes (user_id, title, ingredients, instructions) VALUES (%s, %s, %s, %s)",
        (user_id, title, ingredients_json, instructions)
    )
    conn.commit()
    cur.execute("SELECT LASTVAL()")
    recipe_id = cur.fetchone()[0]
    cur.close()
    conn.close()

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
    cur = conn.cursor()
    cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Recipe deleted!"})

if __name__ == "__main__":
    app.run(debug=True)