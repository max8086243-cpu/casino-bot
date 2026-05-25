import asyncio
import logging
import random
import json
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8674593247:AAEH2X5R5BlHX0NNMnoV4pyYzeD2GY77J5E"
ADMIN_ID = 8548452512
# =================================

from database import init_db, get_user, update_user, add_card_to_collection, get_user_cards_count
from database import get_random_rarity, RARITIES, get_top_balance, get_top_cards_count, get_top_rarest_cards
from database import get_card_image_by_rarity, get_all_card_templates, get_user_cards
from database import add_achievement, check_achievement_exists, get_user_achievements
from database import create_clan, get_clan, get_clan_by_name, add_to_clan, get_clan_members, update_clan_balance
from database import create_trade, get_trade, update_trade_status, get_pending_trades_for_user
from database import is_premium, activate_premium, get_premium_multiplier, get_premium_coin_multiplier
from database import add_rank_points, update_rank_league, get_top_rank_points

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()
bot = None

class AddCardState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_rarity = State()

class TradeState(StatesGroup):
    waiting_for_user = State()
    waiting_for_card = State()

# ========== БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ ==========
def safe_get(user, index, default=0):
    if user and index < len(user):
        val = user[index]
        return val if val is not None else default
    return default

# ========== КЛАВИАТУРЫ ==========
def get_main_menu(user_id):
    premium_text = "PREMIUM" if is_premium(user_id) else "ПРЕМИУМ"
    buttons = [
        [InlineKeyboardButton(text="🎰 КРУТКА", callback_data="spin")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="inventory"),
         InlineKeyboardButton(text="🏆 ТОПЫ", callback_data="top_menu")],
        [InlineKeyboardButton(text="🛒 МАГАЗИН", callback_data="shop")],
        [InlineKeyboardButton(text="🎮 ИГРЫ", callback_data="games_menu")],
        [InlineKeyboardButton(text=f"💎 {premium_text}", callback_data="premium_info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def games_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 ЛОТЕРЕЯ (50 монет)", callback_data="lottery")],
        [InlineKeyboardButton(text="🏅 ДОСТИЖЕНИЯ", callback_data="achievements")],
        [InlineKeyboardButton(text="👥 КЛАНЫ", callback_data="clans_menu")],
        [InlineKeyboardButton(text="🔄 ОБМЕН КАРТ", callback_data="trade_menu")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def shop_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🍀 УДАЧА (10)", callback_data="buy_luck")],
        [InlineKeyboardButton(text="⚡ СКОРОСТЬ (15)", callback_data="buy_speed_small")],
        [InlineKeyboardButton(text="💊 ЗЕЛЬЕ (50)", callback_data="buy_reset")],
        [InlineKeyboardButton(text="🎲 ПЕРЕКРУТ (75)", callback_data="buy_reroll")],
        [InlineKeyboardButton(text="🃏 СЛУЧАЙНАЯ КАРТА (150)", callback_data="buy_random_card")],
        [InlineKeyboardButton(text="🌟 МАГНИТ (200)", callback_data="buy_magnet")],
        [InlineKeyboardButton(text="🍀 УЛЬТРА-УДАЧА (300)", callback_data="buy_ultra_luck")],
        [InlineKeyboardButton(text="⚡ УЛЬТРА-СКОРОСТЬ (300)", callback_data="buy_ultra_speed")],
        [InlineKeyboardButton(text="👑 ЛЕГЕНДАРНЫЙ КЛЮЧ (5000)", callback_data="buy_legendary_key")],
        [InlineKeyboardButton(text="💎 ПРЕМИУМ 7 ДНЕЙ (5000)", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def top_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💰 ПО БАЛЛАМ", callback_data="top_balance")],
        [InlineKeyboardButton(text="🃏 ПО КОЛ-ВУ КАРТ", callback_data="top_cards")],
        [InlineKeyboardButton(text="⭐ ПО РЕДКОСТИ", callback_data="top_rare")],
        [InlineKeyboardButton(text="🏆 ПО РАНКЕДУ", callback_data="top_rank")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def clans_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="➕ СОЗДАТЬ КЛАН", callback_data="clan_create")],
        [InlineKeyboardButton(text="🔍 ВСТУПИТЬ В КЛАН", callback_data="clan_join")],
        [InlineKeyboardButton(text="📋 МОЙ КЛАН", callback_data="clan_info")],
        [InlineKeyboardButton(text="💸 ПОПОЛНИТЬ КАЗНУ", callback_data="clan_donate")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="games_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def trade_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="➕ ПРЕДЛОЖИТЬ ОБМЕН", callback_data="trade_offer")],
        [InlineKeyboardButton(text="📋 МОИ СДЕЛКИ", callback_data="trade_list")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="games_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def check_achievements(user_id, user):
    achievements = []
    total_spins = safe_get(user, 7, 0)
    total_spent = safe_get(user, 8, 0)
    cards_count = get_user_cards_count(user_id)
    premium = is_premium(user_id)
    
    if total_spins >= 100 and not check_achievement_exists(user_id, "Азартный"):
        achievements.append("Азартный")
    if total_spent >= 5000 and not check_achievement_exists(user_id, "Тратящий"):
        achievements.append("Тратящий")
    if cards_count >= 50 and not check_achievement_exists(user_id, "Коллекционер"):
        achievements.append("Коллекционер")
    if premium and not check_achievement_exists(user_id, "Избранный"):
        achievements.append("Избранный")
    
    for ach in achievements:
        add_achievement(user_id, ach)
        await bot.send_message(user_id, f"🏆 ПОЗДРАВЛЯЮ! Получено достижение: {ach}! +500 монет!")
        current_coins = safe_get(user, 2, 0)
        update_user(user_id, coins=current_coins+500)

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    init_db()
    user = get_user(user_id)
    balance = safe_get(user, 1, 0)
    coins = safe_get(user, 2, 0)
    await message.answer(
        f"⭐️ Казино ХС ⭐️\n\n"
        f"💰 БАЛЛЫ: {balance}  |  🪙 МОНЕТЫ: {coins}\n\n"
        f"🔥 КРУТИ КАРТЫ, СОБИРАЙ КОЛЛЕКЦИЮ!",
        reply_markup=get_main_menu(user_id)
    )

@dp.callback_query(F.data == "back")
async def back_to_menu(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    balance = safe_get(user, 1, 0)
    coins = safe_get(user, 2, 0)
    text = (
        f"⭐️ Казино ХС ⭐️\n\n"
        f"💰 БАЛЛЫ: {balance}  |  🪙 МОНЕТЫ: {coins}\n\n"
        f"🔥 КРУТИ КАРТЫ, СОБИРАЙ КОЛЛЕКЦИЮ!"
    )
    try:
        await call.message.edit_text(text, reply_markup=get_main_menu(user_id))
    except Exception:
        await call.message.delete()
        await call.message.answer(text, reply_markup=get_main_menu(user_id))
    await call.answer()

@dp.callback_query(F.data == "games_menu")
async def games_menu(call: CallbackQuery):
    await call.message.edit_text("🎮 ИГРЫ И СОЦИУМ 🎮\n\nВыберите раздел:", reply_markup=games_menu_keyboard())
    await call.answer()

# ========== УПРОЩЁННАЯ, НО РАБОЧАЯ КРУТКА ==========
@dp.callback_query(F.data == "spin")
async def spin_card(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)

    last_spin_str = safe_get(user, 3, None)
    now = datetime.now()
    if last_spin_str:
        try:
            last_spin = datetime.fromisoformat(last_spin_str)
            cooldown = timedelta(hours=3) - timedelta(minutes=safe_get(user, 5, 0))
            if cooldown.total_seconds() < 0:
                cooldown = timedelta(seconds=0)
            if now < last_spin + cooldown:
                remaining = (last_spin + cooldown) - now
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                await call.message.answer(f"❌ КД {hours}ч {minutes}мин. Подождите!")
                await call.answer()
                return
        except:
            pass
    
    luck_active = safe_get(user, 4, 0) > 0
    rarity_name, rarity_data = get_random_rarity(luck_active)
    points_earn = rarity_data["points"]
    coins_earn = rarity_data["coins"]
    emoji = rarity_data["emoji"]
    
    new_balance = safe_get(user, 1, 0) + points_earn
    new_coins = safe_get(user, 2, 0) + coins_earn
    new_last = now.isoformat()
    new_luck = safe_get(user, 4, 0) - 1 if luck_active else 0
    
    update_user(user_id, balance=new_balance, coins=new_coins, last_spin=new_last,
                booster_luck=new_luck)
    
    card_template = get_card_image_by_rarity(rarity_name)
    if not card_template:
        image_url = "https://cdn-icons-png.flaticon.com/512/2933/3933241.png"
        card_display_name = f"Карта {rarity_name}"
    else:
        card_display_name = card_template["name"]
        image_url = card_template["image_url"]
    
    add_card_to_collection(user_id, card_display_name, rarity_name, image_url)
    
    caption = (
        f"🎴 **ВЫПАЛА КАРТА!** {emoji}\n\n"
        f"📝 НАЗВАНИЕ: {card_display_name}\n"
        f"⭐ РЕДКОСТЬ: {rarity_name.upper()}\n"
        f"💰 +{points_earn} БАЛЛОВ\n"
        f"🪙 +{coins_earn} МОНЕТ\n\n"
        f"📊 **ВАШ БАЛАНС:**\n"
        f"💰 {new_balance} БАЛЛОВ  |  🪙 {new_coins} МОНЕТ\n\n"
        f"🃏 КАРТ В КОЛЛЕКЦИИ: {get_user_cards_count(user_id)}"
    )
    
    await call.message.delete()
    try:
        await call.message.answer_photo(photo=image_url, caption=caption, reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    except Exception as e:
        print(f"[ERROR] {e}")
        await call.message.answer(caption, reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    
    await call.answer(f"🎰 +{points_earn} БАЛЛОВ!", show_alert=False)
    
    user_after = get_user(user_id)
    await check_achievements(user_id, user_after)

@dp.callback_query(F.data == "inventory")
async def show_inventory(call: CallbackQuery):
    user = get_user(call.from_user.id)
    luck = safe_get(user, 4, 0)
    speed = safe_get(user, 5, 0)
    cards_count = get_user_cards_count(call.from_user.id)
    
    text = (
        f"📦 **ИНВЕНТАРЬ**\n\n"
        f"🍀 УДАЧА: {luck} шт.\n"
        f"⚡ СКОРОСТЬ: {speed} шт.\n"
        f"🃏 ВСЕГО КАРТ: {cards_count}\n\n"
        f"🔥 ИСПОЛЬЗУЙ БУСТЕРЫ ПЕРЕД КРУТКОЙ!\n"
        f"/use_luck — УДАЧА\n"
        f"/use_speed — СКОРОСТЬ"
    )
    buttons = [[InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back")]]
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    except Exception:
        await call.message.delete()
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "shop")
async def shop(call: CallbackQuery):
    text = (
        f"🛒 **МАГАЗИН КАЗИНО ХС**\n\n"
        f"🍀 УДАЧА (10) — +шанс на редкую карту (1 крутка)\n"
        f"⚡ СКОРОСТЬ (15) — -10 мин КД (1 крутка)\n"
        f"💊 ЗЕЛЬЕ (50) — мгновенный сброс КД\n"
        f"👇 ВЫБЕРИ ТОВАР:"
    )
    await call.message.edit_text(text, reply_markup=shop_keyboard(), parse_mode="Markdown")
    await call.answer()

# ========== ПОКУПКИ ==========
@dp.callback_query(F.data == "buy_luck")
async def buy_luck(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    coins = safe_get(user, 2, 0)
    luck = safe_get(user, 4, 0)
    if coins >= 10:
        update_user(user_id, coins=coins-10, booster_luck=luck+1)
        await call.answer("✅ КУПЛЕНО! УДАЧА В ИНВЕНТАРЕ.", show_alert=True)
        await back_to_menu(call)
    else:
        await call.answer("❌ НЕ ХВАТАЕТ МОНЕТ!", show_alert=True)

@dp.callback_query(F.data == "buy_speed_small")
async def buy_speed_small(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    coins = safe_get(user, 2, 0)
    speed = safe_get(user, 5, 0)
    if coins >= 15:
        update_user(user_id, coins=coins-15, booster_speed=speed+1)
        await call.answer("✅ КУПЛЕНО! УСКОРИТЕЛЬ В ИНВЕНТАРЕ.", show_alert=True)
        await back_to_menu(call)
    else:
        await call.answer("❌ НЕ ХВАТАЕТ МОНЕТ!", show_alert=True)

@dp.callback_query(F.data == "buy_reset")
async def buy_reset(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    coins = safe_get(user, 2, 0)
    if coins >= 50:
        update_user(user_id, coins=coins-50, last_spin="2000-01-01T00:00:00")
        await call.answer("✅ КД СБРОШЕН!", show_alert=True)
        await back_to_menu(call)
    else:
        await call.answer("❌ НЕ ХВАТАЕТ МОНЕТ!", show_alert=True)

# ========== ТОПЫ ==========
@dp.callback_query(F.data == "top_menu")
async def top_menu(call: CallbackQuery):
    await call.message.edit_text("🏆 ВЫБЕРИ ТИП ТОПА 🏆", reply_markup=top_menu_keyboard())
    await call.answer()

@dp.callback_query(F.data == "top_balance")
async def top_balance(call: CallbackQuery):
    top = get_top_balance(10)
    text = "🏆 ТОП ПО БАЛЛАМ 🏆\n\n"
    for i, (uid, bal) in enumerate(top, 1):
        try:
            user = await call.bot.get_chat(uid)
            name = user.first_name
        except:
            name = f"User_{uid}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        text += f"{medal} {i}. {name} - {bal} 💰\n"
    await call.message.edit_text(text, reply_markup=top_menu_keyboard())
    await call.answer()

@dp.callback_query(F.data == "top_cards")
async def top_cards(call: CallbackQuery):
    top = get_top_cards_count(10)
    text = "🏆 ТОП ПО КОЛ-ВУ КАРТ 🏆\n\n"
    for i, (uid, cnt) in enumerate(top, 1):
        try:
            user = await call.bot.get_chat(uid)
            name = user.first_name
        except:
            name = f"User_{uid}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        text += f"{medal} {i}. {name} - {cnt} 🃏\n"
    await call.message.edit_text(text, reply_markup=top_menu_keyboard())
    await call.answer()

@dp.callback_query(F.data == "top_rare")
async def top_rare(call: CallbackQuery):
    top = get_top_rarest_cards(10)
    text = "🏆 ТОП ПО РЕДКОСТИ 🏆\n\n"
    for i, (uid, score) in enumerate(top, 1):
        try:
            user = await call.bot.get_chat(uid)
            name = user.first_name
        except:
            name = f"User_{uid}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        text += f"{medal} {i}. {name} - {score} ⭐\n"
    await call.message.edit_text(text, reply_markup=top_menu_keyboard())
    await call.answer()

@dp.callback_query(F.data == "top_rank")
async def top_rank(call: CallbackQuery):
    try:
        top = get_top_rank_points(10)
        text = "🏆 ТОП ПО РАНКЕДУ 🏆\n\n"
        for i, (uid, points) in enumerate(top, 1):
            try:
                user = await call.bot.get_chat(uid)
                name = user.first_name
            except:
                name = f"User_{uid}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
            text += f"{medal} {i}. {name} - {points} очков\n"
        await call.message.edit_text(text, reply_markup=top_menu_keyboard())
    except:
        await call.message.edit_text("🏆 ТОП ПО РАНКЕДУ 🏆\n\nПока никого нет. Крутите карты, чтобы заработать очки!", reply_markup=top_menu_keyboard())
    await call.answer()

@dp.message(Command("use_luck"))
async def use_luck(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    luck = safe_get(user, 4, 0)
    if luck > 0:
        update_user(user_id, booster_luck=luck-1)
        await message.answer("🍀 УДАЧА АКТИВИРОВАНА!\n\nСледующая крутка будет удачнее!")
    else:
        await message.answer("❌ У ТЕБЯ НЕТ УДАЧИ!\n\nКупи в магазине за 10 монет")

@dp.message(Command("use_speed"))
async def use_speed(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    speed = safe_get(user, 5, 0)
    if speed > 0:
        update_user(user_id, booster_speed=speed-1)
        await message.answer("⚡ УСКОРИТЕЛЬ АКТИВИРОВАН!\n\nКД следующей крутки уменьшится на 10 минут!")
    else:
        await message.answer("❌ НЕТ УСКОРИТЕЛЯ!\n\nКупи в магазине за 15 монет")

# ========== АДМИН-КОМАНДЫ ==========
@dp.message(Command("add_card"))
async def admin_add_card(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ БОТА!")
        return
    await message.answer("📸 ОТПРАВЬ ФОТО КАРТЫ:")
    await state.set_state(AddCardState.waiting_for_photo)

@dp.message(AddCardState.waiting_for_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(image_url=file_id)
    await message.answer("✏️ ВВЕДИ НАЗВАНИЕ КАРТЫ:")
    await state.set_state(AddCardState.waiting_for_name)

@dp.message(AddCardState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    available = [r for r in RARITIES.keys() if not RARITIES[r].get("secret", False)]
    rarities_list = "\n".join([f"• {r}" for r in available])
    await message.answer(f"🎴 ВЫБЕРИ РЕДКОСТЬ:\n\n{rarities_list}\n\nВведи название редкости:")
    await state.set_state(AddCardState.waiting_for_rarity)

@dp.message(AddCardState.waiting_for_rarity)
async def get_rarity(message: Message, state: FSMContext):
    rarity = message.text.lower()
    if rarity not in RARITIES or RARITIES[rarity].get("secret", False):
        available = [r for r in RARITIES.keys() if not RARITIES[r].get("secret", False)]
        await message.answer(f"❌ НЕВЕРНАЯ РЕДКОСТЬ!\n\nДоступны:\n" + "\n".join([f"• {r}" for r in available]))
        return
    data = await state.get_data()
    name = data["name"]
    image_url = data["image_url"]
    from database import sqlite3, DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO card_templates (name, rarity, image_url) VALUES (?, ?, ?)",
                (name, rarity, image_url))
    conn.commit()
    conn.close()
    await message.answer(f"✅ КАРТА ДОБАВЛЕНА!\n\n📝 НАЗВАНИЕ: {name}\n⭐ РЕДКОСТЬ: {rarity}")
    await state.clear()

@dp.message(Command("test_spin"))
async def test_spin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ!")
        return
    all_cards = get_all_card_templates()
    if not all_cards:
        await message.answer("❌ ОШИБКА!\n\nВ боте нет ни одной карты!\nДобавь карты через /add_card")
        return
    random_card = random.choice(all_cards)
    rarity_name = random_card["rarity"]
    rarity_data = RARITIES.get(rarity_name, {"points": 0, "coins": 0, "emoji": "🎴"})
    points_earn = rarity_data["points"]
    coins_earn = rarity_data["coins"]
    emoji = rarity_data["emoji"]
    caption = (
        f"🧪 ТЕСТОВАЯ КРУТКА\n\n"
        f"🎴 КАРТА: {random_card['name']}\n"
        f"⭐ РЕДКОСТЬ: {rarity_name.upper()} {emoji}\n"
        f"💰 +{points_earn} БАЛЛОВ\n"
        f"🪙 +{coins_earn} МОНЕТ\n\n"
        f"⚡ БУСТЕРЫ НЕ ПОТРАЧЕНЫ\n"
        f"📝 КАРТА НЕ ДОБАВЛЕНА В КОЛЛЕКЦИЮ"
    )
    try:
        await message.answer_photo(photo=random_card["image_url"], caption=caption)
    except Exception as e:
        await message.answer(f"❌ ОШИБКА: Не удалось отправить фото\n\n{caption}")

@dp.message(Command("list_cards"))
async def list_all_cards(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ!")
        return
    templates = get_all_card_templates()
    if not templates:
        await message.answer("📭 НЕТ ДОБАВЛЕННЫХ КАРТ\n\nИспользуй /add_card")
        return
    text = "📋 СПИСОК КАРТ В БОТЕ\n\n"
    for card in templates:
        emoji = RARITIES.get(card["rarity"], {}).get("emoji", "🎴")
        text += f"{emoji} {card['name']}\n"
        text += f"   ⭐ {card['rarity']} (ID: {card['id']})\n\n"
    text += f"📌 ВСЕГО: {len(templates)} КАРТ"
    await message.answer(text)

@dp.message(Command("del_card"))
async def delete_card(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ БОТА!")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ КАК УДАЛИТЬ КАРТУ:\n\n/del_card ID_карты\n\nСначала узнай ID карты через /list_cards")
        return
    try:
        card_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID ДОЛЖЕН БЫТЬ ЧИСЛОМ!")
        return
    from database import sqlite3, DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name, rarity FROM card_templates WHERE id = ?", (card_id,))
    card = cur.fetchone()
    if not card:
        conn.close()
        await message.answer(f"❌ КАРТА С ID {card_id} НЕ НАЙДЕНА!\n\nИспользуй /list_cards чтобы увидеть все карты")
        return
    card_name, rarity = card
    cur.execute("DELETE FROM card_templates WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    emoji = RARITIES.get(rarity, {}).get("emoji", "🎴")
    await message.answer(f"✅ КАРТА УДАЛЕНА!\n\n{emoji} {card_name}\n⭐ Редкость: {rarity}\n🆔 ID: {card_id}\n\n⚠️ Карта больше не будет выпадать игрокам")

@dp.message(Command("reset_top"))
async def reset_top(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ БОТА!")
        return
    from database import sqlite3, DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = 0, coins = 0, rank_points = 0, rank_league = 'Железо'")
    cur.execute("DELETE FROM cards")
    conn.commit()
    conn.close()
    await message.answer("✅ ТОП ОБНУЛЁН!\n\n📊 БАЛАНСЫ: 0\n🃏 КАРТЫ: УДАЛЕНЫ\n🏆 РАНКЕД: СБРОШЕН")

@dp.message(Command("reset_balance"))
async def reset_balance(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ БОТА!")
        return
    from database import sqlite3, DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = 0, coins = 0")
    conn.commit()
    conn.close()
    await message.answer("✅ БАЛАНСЫ ОБНУЛЕНЫ!")

@dp.message(Command("list_users"))
async def list_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ ТОЛЬКО СОЗДАТЕЛЬ БОТА!")
        return
    from database import sqlite3, DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, balance, coins, rank_points, rank_league FROM users ORDER BY balance DESC LIMIT 20")
    users = cur.fetchall()
    conn.close()
    if not users:
        await message.answer("📭 НЕТ ИГРОКОВ В БОТЕ")
        return
    text = "👥 СПИСОК ИГРОКОВ\n\n"
    for i, (uid, bal, coins, rp, league) in enumerate(users, 1):
        try:
            user = await message.bot.get_chat(uid)
            name = user.first_name
        except:
            name = f"User_{uid}"
        text += f"{i}. {name}\n"
        text += f"   💰 {bal}  |  🪙 {coins}\n"
        text += f"   🏆 {league} ({rp} очков)\n\n"
    await message.answer(text)

# ========== ЗАПУСК ==========
async def main():
    global bot
    bot = Bot(token=BOT_TOKEN)
    init_db()
    await bot.delete_webhook()
    print("🎰 КАЗИНО ХС БОТ ЗАПУЩЕН!")
    print("⭐ ВЕРСИЯ: УПРОЩЁННАЯ (РАБОЧАЯ)")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())