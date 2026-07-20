import os
import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==============================================================================
# КОНФИГУРАЦИЯ БОТА И ОПЛАТЫ ЗВЁЗДАМИ (TELEGRAM STARS)
# ==============================================================================
# Вставьте сюда ваш токен бота от @BotFather
BOT_TOKEN = "8733922086:AAEiaKbj-yhRvZ-rkQP2doPEnXmc2Bk1ins"  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обновленная тарифная сетка: все цены умножены на коэффициент 1.2
TARIFS = {
    "1M": {"days": 30, "stars": 36, "prefix": "KEY_1M_", "name": "VPN подписка на 1 месяц"},
    "3M": {"days": 90, "stars": 72, "prefix": "KEY_3M_", "name": "VPN подписка на 3 месяца"},
    "6M": {"days": 180, "stars": 132, "prefix": "KEY_6M_", "name": "VPN подписка на 6 месяцев"},
    "12M": {"days": 365, "stars": 240, "prefix": "KEY_12M_", "name": "VPN подписка на 12 месяцев"}
}

def init_bot_db():
    """Инициализация базы данных продаж на хостинге"""
    db_path = "artefakt_sales.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sold_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            tarif_type TEXT,
            days INTEGER,
            user_id INTEGER,
            purchase_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_secure_key(tarif_code):
    """Генерация ключа для вашего PyQt6 Windows-приложения"""
    prefix = TARIFS[tarif_code]["prefix"]
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{prefix}{random_str}"
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Главный экран"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2)
    
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\n"
        "Что вас интересует?"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_support")
async def handle_support(callback: types.CallbackQuery):
    """Экран техподдержки с экранированием юзернейма"""
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Назад", callback_data="back_to_start")
    
    support_text = (
        "👨‍💻 **Служба поддержки Artefakt VPN**\n\n"
        "Если у вас возникли вопросы по оплате или работе клиента, напишите администратору:\n\n"
        "👉 **Личный контакт:** @artefakt\_tg"
    )
    await callback.message.edit_text(support_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_tarifs")
async def show_tarifs(callback: types.CallbackQuery):
    """Витрина планов со звёздами (текст кнопок обновлен под новые цены)"""
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐️ 1 месяц — 36 XTR", callback_data="buy_1M")
    builder.button(text="⭐️ 3 месяца — 72 XTR", callback_data="buy_3M")
    builder.button(text="⭐️ 6 месяцев — 132 XTR", callback_data="buy_6M")
    builder.button(text="⭐️ 12 месяцев — 240 XTR", callback_data="buy_12M")
    builder.button(text="⬅ Назад в меню", callback_data="back_to_start")
    builder.adjust(1)
    
    await callback.message.edit_text("📋 **Выберите подходящий тарифный план для покупки за Звёзды:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_start")
async def handle_back(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2)
    await callback.message.edit_text("👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\nЧто вас интересует?", reply_markup=builder.as_markup(), parse_mode="Markdown")
@dp.callback_query(F.data.startswith("buy_"))
async def handle_purchase(callback: types.CallbackQuery):
    """Выставление официального счета Telegram Stars напрямую в чат"""
    await callback.answer()
    raw_data = callback.data.split("_")
    tarif_code = raw_data[1] if len(raw_data) > 1 else None
    
    if not tarif_code or tarif_code not in TARIFS: return
    
    stars_price = TARIFS[tarif_code]["stars"]
    name = TARIFS[tarif_code]["name"]
    
    # Отправляем инвойс встроенным методом Telegram (без сторонних платежек!)
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=name,
        description=f"Активационный ключ подписки для ПК-приложения Artefakt VPN на {TARIFS[tarif_code]['days']} дней.",
        payload=f"payload_{tarif_code}",
        provider_token="", # Для Telegram Stars это поле ОСТАЕТСЯ ПУСТЫМ!
        currency="XTR",   # Код валюты Telegram Stars
        prices=[types.LabeledPrice(label=name, amount=stars_price)]
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    """Обязательное автоматическое подтверждение готовности принять платеж от Telegram"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    """Событие успешной оплаты: вызывается автоматически самим Telegram сразу после списания звёзд"""
    payload = message.successful_payment.invoice_payload
    tarif_code = payload.split("_")[1]
    
    if tarif_code not in TARIFS: return

    generated_key = generate_secure_key(tarif_code)
    days_count = TARIFS[tarif_code]["days"]
    
    from datetime import datetime
    conn = sqlite3.connect("artefakt_sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sold_keys (license_key, tarif_type, days, user_id, purchase_date) VALUES (?, ?, ?, ?, ?)",
                       (str(generated_key), str(tarif_code), int(days_count), int(message.from_user.id), datetime.now().isoformat()))
        conn.commit()
    except Exception as e:
        print(f"Ошибка сохранения ключа: {e}")
    conn.close()
    
    # Выдаем ключ пользователю. Оплата 100% автоматическая, никаких кнопок проверки нажимать не нужно!
    await message.answer(
        f"🎉 **Оплата звёздами успешно принята!**\n\n"
        f"📋 Ваш персональный лицензионный ключ на **{days_count} дней**:\n"
        f"`{generated_key}`\n\n"
        f"💡 Скопируйте его кликом по тексту выше и вставьте в настройки ПК-клиента Artefakt VPN. Спасибо за покупку!",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    init_bot_db()
    print("🤖 Бот на официальной платежной системе Telegram Stars запущен на BotHost...")
    dp.run_polling(bot)
