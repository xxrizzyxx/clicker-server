# SERVER.PY - POLNYJ SERVER DLJA KLIKERA 3.0
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import random
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ===== KONFIG =====
FIREBASE_URL = "https://clicker-game-cb3b4-default-rtdb.europe-west1.firebasedatabase.app/"
ADMIN_PASSWORD = "admin123"
MAX_MONEY = 10**12
MAX_V = 10**6

# ===== BOSSES =====
BOSSES = {
    "goblin": {"hp": 100, "v_reward": 10},
    "orc": {"hp": 500, "v_reward": 25},
    "troll": {"hp": 2000, "v_reward": 50},
    "demon": {"hp": 10000, "v_reward": 100},
    "dragon": {"hp": 50000, "v_reward": 500}
}

# ===== VSPOMOGATELNYE FUNKCII =====
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

def load_world_boss():
    try:
        url = f"{FIREBASE_URL}world_boss.json"
        resp = requests.get(url)
        if resp.status_code == 200 and resp.json():
            return resp.json()
    except:
        pass
    return {"active": False, "hp": 0, "max_hp": 0, "type": "goblin", "damage_log": [], "spawn_time": 0}

def save_world_boss(data):
    try:
        url = f"{FIREBASE_URL}world_boss.json"
        requests.put(url, json.dumps(data))
    except:
        pass

def get_next_price(current):
    if current < 25: return 25
    elif current < 50: return 50
    elif current < 100: return 100
    elif current < 150: return 150
    elif current < 250: return 250
    elif current < 400: return 400
    elif current < 500: return 500
    elif current < 750: return 750
    elif current < 1000: return 1000
    elif current < 1500: return 1500
    elif current < 2000: return 2000
    elif current < 3000: return 3000
    elif current < 5000: return 5000
    else: return int(current * 1.25)

def get_skin_bonus(skin_id):
    skins = {"default": 1.0, "fire": 1.2, "ice": 1.5, "shadow": 2.0, "god": 3.0}
    return skins.get(skin_id, 1.0)

# ===== ENDPOINTY =====

@app.route('/')
def index():
    return "KLIKER 3.0 SERVER RUNNING"

@app.route('/click', methods=['POST'])
def handle_click():
    data = request.json
    player_id = data.get('player_id')
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    combo = data.get('combo', 1)
    last_click = data.get('last_click', 0)
    current_time = time.time()
    
    if current_time - last_click < 0.05:
        return jsonify({"error": "Too fast"}), 429
    
    if current_time - last_click < 1.5:
        combo += 1
    else:
        combo = 1
    
    if combo <= 5:
        combo_mult = 1.0
    elif combo <= 15:
        combo_mult = 1.0 + (combo - 5) * 0.05
    elif combo <= 30:
        combo_mult = 1.5 + (combo - 15) * 0.03
    elif combo <= 60:
        combo_mult = 1.95 + (combo - 30) * 0.02
    elif combo <= 100:
        combo_mult = 2.55 + (combo - 60) * 0.01
    else:
        combo_mult = 2.95 + (combo - 100) * 0.005
    
    money = player.get('money', 0)
    click_power = player.get('click_power', 1)
    total_clicks = player.get('total_clicks', 0)
    level = player.get('level', 1)
    xp = player.get('xp', 0)
    xp_to_next = player.get('xp_to_next', 50)
    prestige_bonus = player.get('prestige_bonus', 1.0)
    current_skin = player.get('current_skin', 'default')
    active_potions = player.get('active_potions', [])
    
    skin_bonus = get_skin_bonus(current_skin)
    potion_bonus = 2.0 if "double" in active_potions else 1.0
    
    income = int(click_power * skin_bonus * prestige_bonus * potion_bonus * combo_mult)
    if income > 1000000:
        income = 1000000
    
    money += income
    total_clicks += 1
    xp += 1
    
    if xp >= xp_to_next:
        xp = 0
        level += 1
        xp_to_next = int(xp_to_next * 1.4)
        click_power += 1
    
    if money > MAX_MONEY:
        money = MAX_MONEY
    if click_power > MAX_CLICK_POWER:
        click_power = MAX_CLICK_POWER
    
    player['money'] = money
    player['click_power'] = click_power
    player['total_clicks'] = total_clicks
    player['level'] = level
    player['xp'] = xp
    player['xp_to_next'] = xp_to_next
    player['combo'] = combo
    player['max_combo'] = max(player.get('max_combo', 0), combo)
    player['last_click'] = current_time
    
    save_player(player_id, player)
    
    return jsonify({
        "success": True,
        "money": money,
        "income": income,
        "combo": combo,
        "combo_mult": round(combo_mult, 2),
        "level": level,
        "xp": xp,
        "xp_to_next": xp_to_next,
        "total_clicks": total_clicks,
        "click_power": click_power,
        "max_combo": player.get('max_combo', 0)
    })

@app.route('/buy_power', methods=['POST'])
def buy_power():
    data = request.json
    player_id = data.get('player_id')
    amount = data.get('amount', 1)
    if amount < 1:
        amount = 1
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    cost = player.get('power_cost', 10)
    total_cost = 0
    temp_cost = cost
    for i in range(amount):
        total_cost += temp_cost
        temp_cost = get_next_price(temp_cost)
    
    if player.get('money', 0) < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    player['money'] = player.get('money', 0) - total_cost
    player['click_power'] = player.get('click_power', 1) + amount
    player['power_cost'] = temp_cost
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": player['money'],
        "click_power": player['click_power'],
        "power_cost": player['power_cost']
    })

@app.route('/buy_auto', methods=['POST'])
def buy_auto():
    data = request.json
    player_id = data.get('player_id')
    amount = data.get('amount', 1)
    if amount < 1:
        amount = 1
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    cost = player.get('auto_cost', 25)
    total_cost = 0
    temp_cost = cost
    for i in range(amount):
        total_cost += temp_cost
        temp_cost = get_next_price(temp_cost)
    
    if player.get('money', 0) < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    player['money'] = player.get('money', 0) - total_cost
    player['auto_clickers'] = player.get('auto_clickers', 0) + amount
    player['auto_cost'] = temp_cost
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": player['money'],
        "auto_clickers": player['auto_clickers'],
        "auto_cost": player['auto_cost']
    })

@app.route('/prestige', methods=['POST'])
def do_prestige():
    data = request.json
    player_id = data.get('player_id')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    if player.get('money', 0) < 1000000:
        return jsonify({"error": "Need 1.000.000"}), 400
    
    player['money'] = 0
    player['prestige_level'] = player.get('prestige_level', 0) + 1
    player['prestige_bonus'] = 1.0 + (player['prestige_level'] * 0.5)
    player['click_power'] = 1
    player['auto_clickers'] = 0
    player['power_cost'] = 10
    player['auto_cost'] = 25
    player['combo'] = 0
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": 0,
        "prestige_level": player['prestige_level'],
        "prestige_bonus": player['prestige_bonus']
    })

@app.route('/attack_boss', methods=['POST'])
def attack_boss():
    data = request.json
    player_id = data.get('player_id')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    boss = load_world_boss()
    if not boss.get('active', False):
        return jsonify({"error": "No boss active"}), 400
    
    damage = player.get('click_power', 1) * 10
    boss['hp'] -= damage
    boss['damage_log'].append({"player": player_id, "damage": damage})
    
    if boss['hp'] <= 0:
        boss['active'] = False
        # Nagrady
        total_damage = sum([x['damage'] for x in boss['damage_log']])
        for entry in boss['damage_log']:
            p = load_player(entry['player'])
            if p:
                share = entry['damage'] / total_damage if total_damage > 0 else 0
                v_reward = int(boss.get('v_reward', 50) * share)
                if v_reward < 1:
                    v_reward = 1
                p['v_coins'] = p.get('v_coins', 0) + v_reward
                save_player(entry['player'], p)
        save_world_boss({"active": False, "hp": 0, "max_hp": 0, "type": "goblin", "damage_log": [], "spawn_time": 0})
        return jsonify({
            "success": True,
            "boss_defeated": True,
            "damage": damage,
            "boss_hp": 0,
            "boss_reward": boss.get('v_reward', 50)
        })
    
    save_world_boss(boss)
    return jsonify({
        "success": True,
        "damage": damage,
        "boss_hp": boss['hp'],
        "boss_defeated": False,
        "boss_reward": 0
    })

@app.route('/spawn_boss', methods=['POST'])
def spawn_boss():
    data = request.json
    password = data.get('password', '')
    boss_type = data.get('boss_type', 'goblin')
    
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    if boss_type not in BOSSES:
        return jsonify({"error": "Invalid boss type"}), 400
    
    boss_data = BOSSES[boss_type]
    boss = {
        "active": True,
        "hp": boss_data["hp"],
        "max_hp": boss_data["hp"],
        "type": boss_type,
        "v_reward": boss_data["v_reward"],
        "spawn_time": time.time(),
        "damage_log": []
    }
    save_world_boss(boss)
    return jsonify({"success": True, "boss": boss})

@app.route('/admin_find', methods=['POST'])
def admin_find():
    data = request.json
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    query = data.get('query', '').lower()
    players = requests.get(f"{FIREBASE_URL}players.json").json() or {}
    results = []
    for pid, pdata in players.items():
        if query in pid.lower() or query in pdata.get('name', '').lower():
            results.append({"id": pid, "name": pdata.get('name', 'Unknown'), "money": pdata.get('money', 0)})
    return jsonify({"results": results[:20]})

@app.route('/admin_give_item', methods=['POST'])
def admin_give_item():
    data = request.json
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    player_id = data.get('player_id')
    item_type = data.get('item_type')
    amount = data.get('amount', 1)
    item_id = data.get('item_id', 'stone')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    if item_type == "money":
        player['money'] = player.get('money', 0) + amount
    elif item_type == "v_coins":
        player['v_coins'] = player.get('v_coins', 0) + amount
    elif item_type == "power":
        player['click_power'] = player.get('click_power', 1) + amount
    elif item_type == "auto":
        player['auto_clickers'] = player.get('auto_clickers', 0) + amount
    elif item_type == "material":
        if item_id not in ["stone", "crystal", "gold", "diamond"]:
            return jsonify({"error": "Invalid material"}), 400
        player['materials'] = player.get('materials', {})
        player['materials'][item_id] = player['materials'].get(item_id, 0) + amount
    elif item_type == "skin":
        if item_id not in ["fire", "ice", "shadow", "god"]:
            return jsonify({"error": "Invalid skin"}), 400
        if item_id not in player.get('unlocked_skins', []):
            player['unlocked_skins'] = player.get('unlocked_skins', []) + [item_id]
    elif item_type == "suffix":
        player['suffix'] = item_id
    else:
        return jsonify({"error": "Unknown item type"}), 400
    
    save_player(player_id, player)
    return jsonify({"success": True, "player": player})

@app.route('/admin_ban', methods=['POST'])
def admin_ban():
    data = request.json
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    player_id = data.get('player_id')
    duration = data.get('duration', 3600)
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    player['banned_until'] = time.time() + duration
    save_player(player_id, player)
    return jsonify({"success": True, "banned_until": player['banned_until']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
