# КОД СЕРВЕРА (ПОЛНАЯ ВЕРСИЯ)
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, time, random, requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ===== КОНФИГ =====
FIREBASE_URL = "https://clicker-game-cb3b4-default-rtdb.europe-west1.firebasedatabase.app/"
ADMIN_PASSWORD = "admin123"
MAX_MONEY = 10**12
MAX_V = 10**6

# ===== БОССЫ =====
BOSSES = {
    "goblin": {"hp": 100, "v_reward": 10, "spawn_time": 60},
    "orc": {"hp": 500, "v_reward": 25, "spawn_time": 120},
    "troll": {"hp": 2000, "v_reward": 50, "spawn_time": 300},
    "demon": {"hp": 10000, "v_reward": 100, "spawn_time": 600},
    "dragon": {"hp": 50000, "v_reward": 500, "spawn_time": 3600}
}

# ===== ДОСТИЖЕНИЯ =====
ACHIEVEMENTS = {
    "first_click": {"name": "First Click", "target": 1, "reward": 10},
    "click_100": {"name": "100 Clicks", "target": 100, "reward": 50},
    "click_1000": {"name": "1000 Clicks", "target": 1000, "reward": 200},
    "millionaire": {"name": "Millionaire", "target": 10**6, "reward": 1000},
    "boss_slayer": {"name": "Boss Slayer", "target": 1, "reward": 500},
}

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def load_player(player_id):
    try:
        resp = requests.get(f"{FIREBASE_URL}players/{player_id}.json")
        if resp.status_code == 200 and resp.json():
            return resp.json()
    except: pass
    return None

def save_player(player_id, data):
    try:
        requests.put(f"{FIREBASE_URL}players/{player_id}.json", json.dumps(data))
        return True
    except: return False

def get_world_boss():
    try:
        resp = requests.get(f"{FIREBASE_URL}world_boss.json")
        if resp.status_code == 200 and resp.json():
            return resp.json()
    except: pass
    return {"active": False, "hp": 0, "max_hp": 0, "type": "goblin", "damage_log": [], "spawn_time": 0}

def save_world_boss(data):
    try:
        requests.put(f"{FIREBASE_URL}world_boss.json", json.dumps(data))
    except: pass

# ===== СЕРВЕРНЫЕ ЭНДПОЙНТЫ =====

@app.route('/')
def index():
    return "KLIKER 3.0 SERVER RUNNING"

# --- КЛИК ---
@app.route('/click', methods=['POST'])
def handle_click():
    data = request.json
    player_id = data.get('player_id')
    if not player_id:
        return jsonify({"error": "No player_id"}), 400
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    # Проверка: не слишком часто?
    last_click = player.get('last_click', 0)
    if time.time() - last_click < 0.05:
        return jsonify({"error": "Too fast"}), 429
    
    # Комбо
    combo = player.get('combo', 1)
    if time.time() - last_click < 1.5:
        combo += 1
    else:
        combo = 1
    combo_mult = min(1.0 + (combo * 0.05), 3.0)
    
    # Бонусы
    skin_bonus = {"default":1.0, "fire":1.2, "ice":1.5, "shadow":2.0, "god":3.0}.get(player.get('current_skin', 'default'), 1.0)
    prestige_bonus = player.get('prestige_bonus', 1.0)
    potion_bonus = 2.0 if "double" in player.get('active_potions', []) else 1.0
    
    income = int(player.get('click_power', 1) * skin_bonus * prestige_bonus * potion_bonus * combo_mult)
    if income > 10**6:
        income = 10**6
    
    # Применяем
    player['money'] = player.get('money', 0) + income
    player['total_clicks'] = player.get('total_clicks', 0) + 1
    player['combo'] = combo
    player['last_click'] = time.time()
    player['xp'] = player.get('xp', 0) + 1
    
    # Уровень
    xp_to_next = player.get('xp_to_next', 50)
    if player['xp'] >= xp_to_next:
        player['xp'] = 0
        player['level'] = player.get('level', 1) + 1
        player['xp_to_next'] = int(xp_to_next * 1.4)
        player['click_power'] = player.get('click_power', 1) + 1
    
    # Максимальное комбо
    if combo > player.get('max_combo', 0):
        player['max_combo'] = combo
    
    # Проверка достижений
    for ach_id, ach in ACHIEVEMENTS.items():
        if not player.get('achievements', {}).get(ach_id, False):
            if (ach_id == "first_click" and player['total_clicks'] >= 1) or \
               (ach_id == "click_100" and player['total_clicks'] >= 100) or \
               (ach_id == "click_1000" and player['total_clicks'] >= 1000) or \
               (ach_id == "millionaire" and player['money'] >= 10**6):
                player['achievements'] = player.get('achievements', {})
                player['achievements'][ach_id] = True
                player['money'] += ach['reward']
    
    save_player(player_id, player)
    
    return jsonify({
        "success": True,
        "money": player['money'],
        "income": income,
        "combo": combo,
        "combo_mult": combo_mult,
        "level": player['level'],
        "xp": player['xp'],
        "xp_to_next": player['xp_to_next'],
        "total_clicks": player['total_clicks'],
        "click_power": player['click_power'],
        "max_combo": player['max_combo'],
        "achievements": player.get('achievements', {})
    })

# --- ПОКУПКА СИЛЫ ---
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
    for i in range(amount):
        total_cost += cost
        cost = int(cost * 1.25) + 5
    
    if player.get('money', 0) < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    player['money'] -= total_cost
    player['click_power'] = player.get('click_power', 1) + amount
    player['power_cost'] = cost
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": player['money'],
        "click_power": player['click_power'],
        "power_cost": player['power_cost']
    })

# --- ПОКУПКА АВТО ---
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
    for i in range(amount):
        total_cost += cost
        cost = int(cost * 1.3) + 10
    
    if player.get('money', 0) < total_cost:
        return jsonify({"error": "Not enough money"}), 400
    
    player['money'] -= total_cost
    player['auto_clickers'] = player.get('auto_clickers', 0) + amount
    player['auto_cost'] = cost
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": player['money'],
        "auto_clickers": player['auto_clickers'],
        "auto_cost": player['auto_cost']
    })

# --- ПРЕСТИЖ ---
@app.route('/prestige', methods=['POST'])
def do_prestige():
    data = request.json
    player_id = data.get('player_id')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    if player.get('money', 0) < 10**6:
        return jsonify({"error": "Need 1.000.000"}), 400
    
    # Сохраняем прогресс для восстановления
    player['prestige_backup'] = {
        "money": player.get('money', 0),
        "click_power": player.get('click_power', 1),
        "auto_clickers": player.get('auto_clickers', 0),
        "level": player.get('level', 1),
        "xp": player.get('xp', 0),
        "xp_to_next": player.get('xp_to_next', 50)
    }
    
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

# --- ВОССТАНОВЛЕНИЕ ПРОГРЕССА (ЗА V) ---
@app.route('/restore_prestige', methods=['POST'])
def restore_prestige():
    data = request.json
    player_id = data.get('player_id')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    backup = player.get('prestige_backup')
    if not backup:
        return jsonify({"error": "No backup found"}), 400
    
    v_cost = 100
    if player.get('v_coins', 0) < v_cost:
        return jsonify({"error": f"Need {v_cost} V"}), 400
    
    player['v_coins'] -= v_cost
    player['money'] = backup.get('money', 0)
    player['click_power'] = backup.get('click_power', 1)
    player['auto_clickers'] = backup.get('auto_clickers', 0)
    player['level'] = backup.get('level', 1)
    player['xp'] = backup.get('xp', 0)
    player['xp_to_next'] = backup.get('xp_to_next', 50)
    player['prestige_backup'] = None
    
    save_player(player_id, player)
    return jsonify({
        "success": True,
        "money": player['money'],
        "click_power": player['click_power'],
        "auto_clickers": player['auto_clickers'],
        "level": player['level'],
        "v_coins": player['v_coins']
    })

# --- ВЫДАЧА ПРЕДМЕТА (АДМИН) ---
@app.route('/admin_give_item', methods=['POST'])
def admin_give_item():
    data = request.json
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    player_id = data.get('player_id')
    item_type = data.get('item_type')  # money, v_coins, power, auto, material, skin, suffix
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
        player['suffix'] = item_id  # bomsch, bog, pobeditel, etc.
    else:
        return jsonify({"error": "Unknown item type"}), 400
    
    save_player(player_id, player)
    return jsonify({"success": True, "player": player})

# --- БАН / РАЗБАН (АДМИН) ---
@app.route('/admin_ban', methods=['POST'])
def admin_ban():
    data = request.json
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403
    
    player_id = data.get('player_id')
    duration = data.get('duration', 3600)  # в секундах
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    player['banned_until'] = time.time() + duration
    save_player(player_id, player)
    return jsonify({"success": True, "banned_until": player['banned_until']})

# --- МИРОВОЙ БОСС ---
@app.route('/world_boss', methods=['GET'])
def get_boss():
    boss = get_world_boss()
    return jsonify(boss)

@app.route('/attack_boss', methods=['POST'])
def attack_world_boss():
    data = request.json
    player_id = data.get('player_id')
    
    player = load_player(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    boss = get_world_boss()
    if not boss.get('active', False):
        return jsonify({"error": "No boss active"}), 400
    
    damage = player.get('click_power', 1) * 10
    boss['hp'] -= damage
    boss['damage_log'].append({"player": player_id, "damage": damage})
    
    if boss['hp'] <= 0:
        # Босс убит
        boss['active'] = False
        # Награды
        total_damage = sum([x['damage'] for x in boss['damage_log']])
        for entry in boss['damage_log']:
            p = load_player(entry['player'])
            if p:
                share = entry['damage'] / total_damage
                v_reward = int(boss.get('v_reward', 50) * share)
                p['v_coins'] = p.get('v_coins', 0) + v_reward
                save_player(entry['player'], p)
        
        # Сохраняем в историю
        history = {
            "type": boss.get('type', 'goblin'),
            "killed_by": boss['damage_log'][-1]['player'],
            "time": time.time()
        }
        requests.post(f"{FIREBASE_URL}boss_history.json", json.dumps(history))
        save_world_boss({"active": False, "hp": 0, "damage_log": []})
        
        return jsonify({"success": True, "boss_defeated": True, "damage": damage})
    
    save_world_boss(boss)
    return jsonify({"success": True, "damage": damage, "boss_hp": boss['hp']})

# --- СПАВН БОССА (АДМИН ИЛИ ПО РАСПИСАНИЮ) ---
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

# --- АДМИН: ПОИСК ИГРОКА ---
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

# --- ЗАПУСК СЕРВЕРА ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
