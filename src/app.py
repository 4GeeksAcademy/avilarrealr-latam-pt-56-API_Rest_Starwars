"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Planet, Character, FavoritePlanet, FavoriteCharacter
# from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints


@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/people', methods=['GET'])
def get_all_characters():

    characters = Character.query.all()

    data = [c.serialize() for c in characters]

    return jsonify(data), 200


@app.route('/planets', methods=['GET'])
def get_all_planets():
    planets = Planet.query.all()

    data = [p.serialize() for p in planets]

    return jsonify(data), 200


@app.route('/people/<int:people_id>', methods=['GET'])
def get_single_character(people_id):

    character = Character.query.get(people_id)

    if character is None:
        return jsonify({"msg": "Character not found"}), 404

    return jsonify(character.serialize()), 200


@app.route('/planets/<int:planet_id>', methods=['GET'])
def get_single_planet(planet_id):

    planet = Planet.query.get(planet_id)

    if planet is None:
        return jsonify({"msg": "Planet not found"}), 404

    return jsonify(planet.serialize()), 200


@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    data = [u.serialize() for u in users]
    return jsonify(data), 200


@app.route('/users/favorites/<int:user_id>', methods=['GET'])
def get_user_favorites(user_id):

    user = User.query.get(user_id)
    if user is None:
        return jsonify({"msg": "Simulated user not found"}), 404

    planet_favs = [fav.serialize() for fav in user.favoritePlanets]
    character_favs = [fav.serialize() for fav in user.favoriteCharacters]

    return jsonify({
        "user_id": user.id,
        "favorite_planets": planet_favs,
        "favorite_characters": character_favs
    }), 200


@app.route('/planets', methods=['POST'])
def create_new_planet():
    body = request.get_json()

    if body is None:
        return jsonify({"msg": "Request body must be JSON"}), 400
    if 'name' not in body or 'description' not in body:
        return jsonify({"msg": "Missing required fields: name and description"}), 400

    new_planet = Planet(
        name=body['name'],
        description=body['description']
    )

    try:
        db.session.add(new_planet)
        db.session.commit()
        return jsonify(new_planet.serialize()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error creating planet", "error": str(e)}), 500


@app.route('/people', methods=['POST'])
def create_new_character():
    body = request.get_json()

    if body is None:
        return jsonify({"msg": "Request body must be JSON"}), 400

    required_fields = ['name', 'gender', 'planet_id']
    if not all(field in body for field in required_fields):
        return jsonify({"msg": f"Missing required fields: {', '.join(required_fields)}"}), 400

    planet = Planet.query.get(body['planet_id'])
    if planet is None:
        return jsonify({"msg": f"Planet with ID {body['planet_id']} not found"}), 404

    new_character = Character(
        name=body['name'],
        gender=body['gender'],
        planet_id=body['planet_id']
    )

    try:
        db.session.add(new_character)
        db.session.commit()
        return jsonify(new_character.serialize()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error creating character", "error": str(e)}), 500


@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(user_id, planet_id):

    planet = Planet.query.get(planet_id)
    if planet is None:
        return jsonify({"msg": "Planet ID not found"}), 404

    existing_fav = FavoritePlanet.query.filter_by(
        user_id=user_id, planet_id=planet_id).first()
    if existing_fav:
        return jsonify({"msg": "Planet is already a favorite"}), 400

    new_fav = FavoritePlanet(user_id=user_id,
                             planet_id=planet_id, is_active=True)

    try:
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"msg": f"Planet {planet_id} added to favorites"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error adding favorite", "error": str(e)}), 500


@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['POST'])
def add_favorite_character(user_id, people_id):

    character = Character.query.get(people_id)
    if character is None:
        return jsonify({"msg": "Character ID not found"}), 404

    existing_fav = FavoriteCharacter.query.filter_by(
        user_id=user_id, character_id=people_id).first()
    if existing_fav:
        return jsonify({"msg": "Character is already a favorite"}), 400

    new_fav = FavoriteCharacter(
        user_id=user_id, character_id=people_id, is_active=True)

    try:
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"msg": f"Character {people_id} added to favorites"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error adding favorite", "error": str(e)}), 500


@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(user_id, planet_id):

    fav_to_delete = FavoritePlanet.query.filter_by(
        user_id=user_id, planet_id=planet_id).first()

    if fav_to_delete is None:
        return jsonify({"msg": "Favorite not found for this user and planet"}), 404

    try:
        db.session.delete(fav_to_delete)
        db.session.commit()
        return jsonify({"msg": "Favorite planet successfully deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error deleting favorite", "error": str(e)}), 500


@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_character(user_id, people_id):

    fav_to_delete = FavoriteCharacter.query.filter_by(
        user_id=user_id, character_id=people_id).first()

    if fav_to_delete is None:
        return jsonify({"msg": "Favorite not found for this user and character"}), 404

    try:
        db.session.delete(fav_to_delete)
        db.session.commit()
        return jsonify({"msg": "Favorite character successfully deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Error deleting favorite", "error": str(e)}), 500


# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
