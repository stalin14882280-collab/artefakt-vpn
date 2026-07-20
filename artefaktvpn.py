import os
import sqlite3
import random
import string
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==============================================================================
# КОНФИГУРАЦИЯ БОТА И ПЛАТЕЖНОЙ СИСТЕМЫ CRYPTO PAY
# ==============================================================================
# Вставьте сюда ваш токен бота от @BotFather (например: "723456789:ABC...")
BOT_TOKEN = "8733922086:AAEiaKbj-yhRvZ-rkQP2doPEnXmc2Bk1ins"  

# 🪙 БОЕВОЙ ТОКЕН CRYPTO PAY УСПЕШНО ИНТЕГРИРОВАН
CRYPTO_PAY_TOKEN = "611765:AAza7J4I0y5aQgCEz2FGi4QUymjXMvXnbfs"
# ==============================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Тарифная сетка с ценами в рублях (автоматически конвертируется в USDT при покупке)
TARIFS = {
    "1M": {"days": 30, "price": 59, "prefix": "KEY_1M_", "name": "VPN 1 Месяц"},
    "3M": {"days": 90, "price": 119, "prefix": "KEY_3M_", "name": "VPN 3 Месяца"},
    "6M": {"days": 180, "price": 219, "prefix": "KEY_6M_", "name": "VPN 6 Месяцев"},
    "12M": {"days": 365, "price": 400, "prefix": "KEY_12M_", "name": "VPN 12 Месяцев"}
}

def create_crypto_invoice(amount, desc):
    """Метод автоматического выставления счета в USDT по актуальному курсу рубля"""
    try:
        # Узнаем текущий курс доллара к рублю, чтобы цена была точной
        rate_res = requests.get("https://coingecko.com", timeout=5).json()
        usdt_in_rub = rate_res.get("tether", {}).get("rub", 90.0)
        
        # Переводим рубли в USDT (например, 59 рублей -> ~0.65 USDT)
        crypto_amount = round(float(amount) / usdt_in_rub, 2)
        if crypto_amount < 0.01: crypto_amount = 0.01

        url = "https://cryptobutton.com"
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {
            "asset": "USDT",
            "amount": str(crypto_amount),
            "description": str(desc)
        }
        res = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if res.get("ok"):
            return res["result"]["pay_url"], res["result"]["invoice_id"]
    except Exception as e:
        print(f"Ошибка кассы: {e}")
    return None, None
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветственное окно главного меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2) # Кнопки встанут красиво в один горизонтальный ряд
    
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\n"
        "What interests you?"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_support")
async def handle_support(callback: types.CallbackQuery):
    """Экран с контактами администратора саппорта"""
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Назад", callback_data="back_to_start")
    
    support_text = (
        "👨‍💻 **Служба поддержки Artefakt VPN**\n\n"
        "Если у вас возникли вопросы по оплате или работе клиента, напишите администратору:\n\n"
        "👉 **Личный контакт:** @artefakt_tg"
    )
    await callback.message.edit_text(support_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_tarifs")
async def show_tarifs(callback: types.CallbackQuery):
    """Экран вывода витрины цен подписок"""
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ 1 месяц — 59₽", callback_data="buy_1M")
    builder.button(text="🛍️ 3 месяца — 119₽", callback_data="buy_3M")
    builder.button(text="🛍️ 6 месяцев — 219₽", callback_data="buy_6M")
    builder.button(text="🛍️ 12 месяцев — 400₽", callback_data="buy_12M")
    builder.button(text="⬅ Назад в меню", callback_data="back_to_start")
    builder.adjust(1) # Выстраиваем тарифы вертикально в список
    
    await callback.message.edit_text("📋 **Выберите подходящий тарифный план для покупки:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_start")
async def handle_back(callback: types.CallbackQuery):
    """Кнопка возврата в корневой раздел"""
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2)
    await callback.message.edit_text("👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\nЧто вас интересует?", reply_markup=builder.as_markup(), parse_mode="Markdown")
@dp.callback_query(F.data.startswith("buy_"))
async def handle_purchase(callback: types.CallbackQuery):
    """Выставление счета в Crypto Pay"""
    raw_data = callback.data.split("_")
    tarif_code = raw_data[1] if len(raw_data) > 1 else None
    
    if not tarif_code or tarif_code not in TARIFS: return
    
    price = TARIFS[tarif_code]["price"]
    name = TARIFS[tarif_code]["name"]
    
    pay_url, invoice_id = create_crypto_invoice(price, name)
    
    if not pay_url:
        await callback.answer("❌ Ошибка связи с Crypto Pay API. Попробуйте позже.", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🪙 Оплатить в CryptoBot", url=pay_url)
    builder.button(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}_{tarif_code}")
    builder.button(text="⬅ Назад", callback_data="menu_tarifs")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"💸 **Счет в системе Crypto Pay готов!**\n\n"
        f"📦 **Товар:** {name}\n"
        f"💰 **Стоимость в рублях:** {price}₽\n\n"
        f"Нажмите кнопку ниже для перехода в безопасное окно оплаты Telegram. После подтверждения перевода вернитесь сюда и нажмите кнопку проверки.",
        reply_markup=builder.as_markup(), parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_status(callback: types.CallbackQuery):
    """Автоматическая верификация транзакции через официальное API"""
    _, invoice_id, tarif_code = callback.data.split("_")
    
    is_paid = False
    try:
        url = "https://cryptobutton.com"
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {"invoice_ids": str(invoice_id)}
        res = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if res.get("ok") and len(res["result"]["items"]) > 0:
            if res["result"]["items"][0]["status"] == "paid":
                is_paid = True
    except: pass

    if not is_paid:
        await callback.answer("❌ Оплата еще не зафиксирована сетью. Оплатите счет или попробуйте еще раз через мгновение.", show_alert=True)
        return

    generated_key = generate_secure_key(tarif_code)
    days_count = TARIFS[tarif_code]["days"]
    
    from datetime import datetime
    conn = sqlite3.connect("artefakt_sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sold_keys (license_key, tarif_type, days, user_id, purchase_date) VALUES (?, ?, ?, ?, ?)",
                       (str(generated_key), str(tarif_code), int(days_count), int(callback.from_user.id), datetime.now().isoformat()))
        conn.commit()
    except:
        await callback.answer("Ключ для этой сессии уже выдавался.", show_alert=True)
        conn.close()
        return
    conn.close()
    
    await callback.answer("🎉 Платеж успешно подтвержден!", show_alert=True)
    await callback.message.answer(
        f"✅ **Спасибо! Оплата зачислена автоматически.**\n\n"
        f"📋 Ваш персональный лицензионный ключ на **{days_count} дней**:\n"
        f"`{generated_key}`\n\n"
        f"💡 Скопируйте его кликом по тексту и вставьте в настройки ПК-клиента Artefakt VPN.", parse_mode="Markdown"
    )

def init_bot_db():
    conn = sqlite3.connect("artefakt_sales.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sold_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT, license_key TEXT UNIQUE,
            tarif_type TEXT, days INTEGER, user_id INTEGER, purchase_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_secure_key(tarif_code):
    prefix = TARIFS[tarif_code]["prefix"]
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{prefix}{random_str}"

if __name__ == "__main__":
    init_bot_db()
    print("🤖 Анонимный бот на Crypto Pay успешно запущен на BotHost...")
    dp.run_polling(bot)
