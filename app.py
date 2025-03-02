from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import random

app = Flask(__name__)
CORS(app)  # Erlaubt Anfragen von deinem Vue-Frontend

DATA_FILE = "recipes.json"

# Zutaten-Kategorien
# ingredients = {
#     "vegetables": ["Spinach", "Carrots", "Broccoli", "Peppers"],
#     "proteins": ["Chicken", "Tofu", "Beef", "Beans"],
#     "carbs": ["Rice", "Pasta", "Quinoa", "Potatoes"],
#     "fats": ["Olive oil", "Butter", "Avocado", "Nuts"]
# }
with open('ingredients.json', 'r') as ifile:
    ingredients = json.load(ifile)

# Rezepte aus Datei laden
def load_recipes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# Rezepte speichern
def save_recipes(recipes):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(recipes, file, indent=2)

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
    new_recipe = request.json
    recipes = load_recipes()
    
    # Überschreiben falls der Name bereits existiert
    recipes = [r for r in recipes if r["title"] != new_recipe["title"]]
    recipes.append(new_recipe)
    
    save_recipes(recipes)
    return jsonify({"message": "Rezept gespeichert"}), 200

# Endpoint: Gespeicherte Rezepte laden
@app.route("/load", methods=["GET"])
def load_saved_recipes():
    recipes = load_recipes()
    return jsonify(recipes)

# Endpoint: Rezept löschen
@app.route("/delete", methods=["POST"])
def delete_recipe():
    data = request.json
    recipes = load_recipes()

    # Filtere das zu löschende Rezept heraus
    updated_recipes = [r for r in recipes if r["title"] != data["title"]]

    if len(updated_recipes) != len(recipes):
        save_recipes(updated_recipes)
        return jsonify({"message": "Rezept gelöscht"}), 200
    else:
        return jsonify({"message": "Rezept nicht gefunden"}), 404

if __name__ == "__main__":
    app.run(debug=True)