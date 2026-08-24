from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import random
import requests

app = Flask(__name__)
CORS(app)

FIREBASE_URL = "https://clicker-game-cb3b4-default-rtdb.europe-west1.firebasedatabase.app/"
ADMIN_PASSWORD = "admin123"

def load_player(player_id):
    try:
        url = f"{FIREBASE_URL}players/{player_id}.json"
        resp = requests.get(url)
        if resp.status_code == 200 and resp.json():
            return resp.json()
    except:
        pass
    return None

def save_player(player_id, data):
    try:
        url = f"{FIREBASE_URL}players/{player_id}.json"
        requests.put(url, json.dumps(data))
        return True
    except:
        return False

@app.route('/')
def index():
    return "KLIKER SERVER RABOTAET!"

@app.route('/click', methods=['POST'])
def handle_click():
    data = request.json
    player_id = data.get('player_id')
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player_data = load_player(player_id)
    if not player_data:
        return jsonify({"error": "Player not found"}), 404
    
    money = player_data.get('money', 0)
    click_power = player_data.get('click_power', 1)
    combo = data.get('combo', 1)
    last_click = data.get('last_click', 0)
    current_time = time.time()
    
    if current_time - last_click < 1.5:
        combo += 1
    else:
        combo = 1
    
    combo_mult = 1.0 + (combo * 0.05)
    if combo_mult > 3.0:
        combo_mult = 3.0
    
    income = int(click_power * combo_mult)
    if income > 1000000:
        income = 1000000
    
    money += income
    player_data['money'] = money
    player_data['combo'] = combo
    player_data['last_click'] = current_time
    
    save_player(player_id, player_data)
    
    return jsonify({
        "success": True,
        "money": money,
        "income": income,
        "combo": combo,
        "combo_mult": combo_mult
    })

@app.route('/buy_power', methods=['POST'])
def buy_power():
    data = request.json
    player_id = data.get('player_id')
    amount = data.get('amount', 1)
    
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player_data = load_player(player_id)
    if not player_data:
        return jsonify({"error": "Player not found"}), 404
    
    money = player_data.get('money', 0)
    power_cost = player_data.get('power_cost', 10)
    click_power = player_data.get('click_power', 1)
    
    total_cost = power_cost * amount
    if money < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    money -= total_cost
    click_power += amount
    power_cost = int(power_cost * 1.25) + 5
    
    player_data['money'] = money
    player_data['click_power'] = click_power
    player_data['power_cost'] = power_cost
    
    save_player(player_id, player_data)
    
    return jsonify({
        "success": True,
        "money": money,
        "click_power": click_power,
        "power_cost": power_cost
    })

@app.route('/buy_auto', methods=['POST'])
def buy_auto():
    data = request.json
    player_id = data.get('player_id')
    amount = data.get('amount', 1)
    
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player_data = load_player(player_id)
    if not player_data:
        return jsonify({"error": "Player not found"}), 404
    
    money = player_data.get('money', 0)
    auto_cost = player_data.get('auto_cost', 25)
    auto_clickers = player_data.get('auto_clickers', 0)
    
    total_cost = auto_cost * amount
    if money < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    money -= total_cost
    auto_clickers += amount
    auto_cost = int(auto_cost * 1.3) + 10
    
    player_data['money'] = money
    player_data['auto_clickers'] = auto_clickers
    player_data['auto_cost'] = auto_cost
    
    save_player(player_id, player_data)
    
    return jsonify({
        "success": True,
        "money": money,
        "auto_clickers": auto_clickers,
        "auto_cost": auto_cost
    })

@app.route('/prestige', methods=['POST'])
def do_prestige():
    data = request.json
    player_id = data.get('player_id')
    
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player_data = load_player(player_id)
    if not player_data:
        return jsonify({"error": "Player not found"}), 404
    
    money = player_data.get('money', 0)
    prestige_level = player_data.get('prestige_level', 0)
    
    if money < 1000000:
        return jsonify({"error": "Need 1.000.000"}), 400
    
    money = 0
    prestige_level += 1
    prestige_bonus = 1.0 + (prestige_level * 0.5)
    
    player_data['money'] = money
    player_data['prestige_level'] = prestige_level
    player_data['prestige_bonus'] = prestige_bonus
    player_data['click_power'] = 1
    player_data['auto_clickers'] = 0
    player_data['power_cost'] = 10
    player_data['auto_cost'] = 25
    
    save_player(player_id, player_data)
    
    return jsonify({
        "success": True,
        "money": money,
        "prestige_level": prestige_level,
        "prestige_bonus": prestige_bonus
    })

@app.route('/admin', methods=['POST'])
def admin_action():
    data = request.json
    password = data.get('password')
    action = data.get('action')
    player_id = data.get('player_id')
    field = data.get('field')
    value = data.get('value')
    
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    if action == 'get_player':
        player_data = load_player(player_id)
        if not player_data:
            return jsonify({"error": "Player not found"}), 404
        return jsonify({"data": player_data})
    
    elif action == 'set_field':
        player_data = load_player(player_id)
        if not player_data:
            return jsonify({"error": "Player not found"}), 404
        player_data[field] = value
        save_player(player_id, player_data)
        return jsonify({"success": True})
    
    elif action == 'reset_player':
        reset_data = {
            "money": 0, "click_power": 1, "auto_clickers": 0,
            "total_clicks": 0, "level": 1, "xp": 0,
            "prestige_level": 0, "prestige_bonus": 1.0,
            "power_cost": 10, "auto_cost": 25
        }
        save_player(player_id, reset_data)
        return jsonify({"success": True})
    
    elif action == 'delete_player':
        url = f"{FIREBASE_URL}players/{player_id}.json"
        requests.delete(url)
        return jsonify({"success": True})
    
    elif action == 'add_bonus':
        player_data = load_player(player_id)
        if not player_data:
            return jsonify({"error": "Player not found"}), 404
        player_data[field] = player_data.get(field, 0) + value
        save_player(player_id, player_data)
        return jsonify({"success": True})
    
    return jsonify({"error": "Unknown action"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
