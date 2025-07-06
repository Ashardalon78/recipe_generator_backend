import os
import json
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

BASE_HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
    "Accept": "application/json",
    "X-Client-Info": "debug-test"
}

def get_headers(user_id=None):
    headers = BASE_HEADERS.copy()
    if user_id is not None:
        headers["user-id"] = str(user_id)
    return headers

app = Flask(__name__)
CORS(app)

with open("ingredients.json", "r") as f:
    ingredients = json.load(f)

@app.route("/ingredients", methods=["GET"])
def get_ingredients():
    return jsonify(ingredients)

@app.route("/generate/<int:user_id>", methods=["GET"])
def generate_recipe(user_id):
    recipe = {
        "title": "Neues Rezept",
        "ingredients": {
            "vegetables": random.choice(ingredients["vegetables"]),
            "proteins": random.choice(ingredients["proteins"]),
            "carbs": random.choice(ingredients["carbs"]),
            "fats": random.choice(ingredients["fats"]),
        },
        "instructions": "Zubereitung..."
    }

    user_res = requests.get(f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}", headers=get_headers())
    if not user_res.ok or not user_res.json():
        return jsonify({"error": "User not found"}), 404

    return jsonify(recipe)

@app.route("/users", methods=["GET"])
def get_users():
    res = requests.get(f"{SUPABASE_URL}/rest/v1/users", headers=get_headers())
    return jsonify(res.json())

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    res = requests.get(f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}", headers=get_headers())
    data = res.json()
    if not data:
        return jsonify({"error": "User not found"}), 404
    return jsonify(data[0])

@app.route("/register", methods=["POST"])
def register_user():
    username = request.json.get("name")
    if not username:
        return jsonify({"error": "Username required"}), 400

    data = {"name": username, "role": "user"}
    res = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=get_headers(), data=json.dumps(data))

    if res.status_code == 409:
        return jsonify({"error": "Username already exists"}), 409
    elif not res.ok:
        return jsonify({"error": "Registration failed"}), 500

    lookup = requests.get(f"{SUPABASE_URL}/rest/v1/users?name=eq.{username}", headers=get_headers())
    return jsonify(lookup.json()[0])

@app.route("/admin/create_coach", methods=["POST"])
def create_coach():
    caller = request.json.get("caller")  # z. B. "Ralf_Admin"
    coach_name = request.json.get("coach_name")

    # Prüfen, ob caller wirklich Admin ist
    res = requests.get(f"{SUPABASE_URL}/rest/v1/users?name=eq.{caller}", headers=get_headers())
    if not res.ok or not res.json():
        return jsonify({"error": "Caller not found"}), 404

    caller_data = res.json()[0]
    if caller_data["role"] != "admin":
        return jsonify({"error": "Not authorized"}), 403

    # Coach anlegen
    coach_data = {"name": coach_name, "role": "coach"}
    insert = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=get_headers(), data=json.dumps(coach_data))

    if insert.status_code == 409:
        return jsonify({"error": "Coach name already exists"}), 409

    return jsonify(insert.json())


@app.route("/recipes/<int:user_id>", methods=["GET"])
def get_recipes(user_id):
    # 🧠 Header-Kopie, damit wir ihn individuell anpassen können
    headers = get_headers(user_id=user_id)
    #headers["user-id"] = str(user_id)
    #headers["Accept"] = "application/json"

    # 🔍 Supabase-Request
    url = f"{SUPABASE_URL}/rest/v1/recipes?user_id=eq.{user_id}"
    res = requests.get(url, headers=headers)

    try:
        recipes = res.json()
    except Exception as e:
        return jsonify({"error": "Invalid JSON from Supabase", "details": str(e)}), 500

    # 🧪 Zutaten-Dekodierung (optional)
    for r in recipes:
        if isinstance(r.get("ingredients"), str):
            try:
                r["ingredients"] = json.loads(r["ingredients"])
            except Exception as e:
                print(f"⚠️ JSON decode error in recipe {r.get('id')}: {e}")

    return jsonify(recipes)


@app.route("/recipes/<int:user_id>/<int:recipe_id>", methods=["GET"])
def get_recipe(user_id, recipe_id):
    url = f"{SUPABASE_URL}/rest/v1/recipes?user_id=eq.{user_id}&id=eq.{recipe_id}"
    res = requests.get(url, headers=get_headers(user_id))
    data = res.json()
    if not data:
        return jsonify({"error": "Recipe not found"}), 404
    recipe = data[0]
    if isinstance(recipe["ingredients"], str):
        recipe["ingredients"] = json.loads(recipe["ingredients"])
    return jsonify(recipe)

@app.route("/filters/<int:user_id>", methods=["GET"])
def get_filter_options(user_id):
    url = f"{SUPABASE_URL}/rest/v1/recipes?user_id=eq.{user_id}&select=ingredients"
    res = requests.get(url, headers=get_headers(user_id))
    rows = res.json()

    categories = {"vegetables": set(), "proteins": set(), "carbs": set(), "fats": set()}
    for row in rows:
        ingr = json.loads(row["ingredients"])
        for cat in categories:
            if cat in ingr:
                categories[cat].add(ingr[cat])

    result = {k: sorted(list(v)) for k, v in categories.items()}
    return jsonify(result)

@app.route("/save", methods=["POST"])
def save_recipe():
    try:
        data = request.get_json()
        print("RECIPE TO SAVE:", data)

        user_id = data.get("user_id")
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/recipes",
            headers=get_headers(user_id),
            data=json.dumps(data),
        )

        print("Supabase response code:", response.status_code)
        print("Supabase response text:", response.text)

        if not response.ok:
            return jsonify({"error": "Saving failed", "details": response.text}), 500

        try:
            response_data = response.json()
        except Exception as e:
            print("JSON parse error:", e)
            return jsonify({"error": "Invalid JSON from Supabase", "raw": response.text}), 500

        return jsonify(response_data[0])

    except Exception as e:
        print("SAVE ERROR:", e)
        return jsonify({"error": "Internal error", "details": str(e)}), 500

@app.route("/delete/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    url = f"{SUPABASE_URL}/rest/v1/recipes?id=eq.{recipe_id}"
    res = requests.delete(url, headers=get_headers())
    print(res.status_code)
    if res.status_code in (200, 204):
        return jsonify({"message": "Recipe deleted!"})
    return jsonify({"error": "Delete failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)

