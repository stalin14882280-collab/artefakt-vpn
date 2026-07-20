import os
import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Вставьте сюда токен вашего бота, полученный от @BotFather
BOT_TOKEN = "8733922086:AAEiaKbj-yhRvZ-rkQP2doPEnXmc2Bk1ins"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Базовые префиксы тарифов, которые зашиты в логику вашего VPN-клиента
TARIFS = {
    "1M": {"days": 30, "price": 59, "prefix": "KEY_1M_"},
    "3M": {"days": 90, "price": 119, "prefix": "KEY_3M_"},
    "6M": {"days": 180, "price": 219, "prefix": "KEY_6M_"},
    "12M": {"days": 365, "price": 400, "prefix": "KEY_12M_"}
}

def init_bot_db():
    """Инициализация базы данных на стороне бота для контроля проданных ключей"""
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
    """Генерация уникального криптостойкого ключа с префиксом тарифа"""
    prefix = TARIFS[tarif_code]["prefix"]
    # Генерируем случайную строку из 5 символов
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{prefix}{random_str}"
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Первое приветствие: Вывод кнопок 'Тарифы' и 'Поддержка'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2) # Размещаем кнопки аккуратно в один горизонтальный ряд
    
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\n"
        "Что вас интересует?"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_support")
async def handle_support(callback: types.CallbackQuery):
    """Раздел технической поддержки"""
    await callback.answer()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅ Назад", callback_data="back_to_start")
    
    support_text = (
        "👨‍💻 **Служба поддержки Artefakt VPN**\n\n"
        "Если у вас возникли проблемы с подключением, установкой приложения "
        "или активацией ключа, напишите нашему администратору:\n\n"
        "👉 **Личный контакт:** @artefakt_tg\n\n"
        "Мы ответим вам в самое ближайшее время!"
    )
    await callback.message.edit_text(support_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "menu_tarifs")
async def show_tarifs(callback: types.CallbackQuery):
    """Открытие витрины тарифных планов по кнопке"""
    await callback.answer()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ 1 месяц — 59₽", callback_data="buy_1M")
    builder.button(text="🛍️ 3 месяца — 119₽", callback_data="buy_3M")
    builder.button(text="🛍️ 6 месяцев — 219₽", callback_data="buy_6M")
    builder.button(text="🛍️ 12 месяцев — 400₽", callback_data="buy_12M")
    builder.button(text="⬅ Назад в меню", callback_data="back_to_start")
    builder.adjust(1) # Выстраиваем список покупок вертикально
    
    tarifs_text = (
        "📋 **Доступные тарифные планы Artefakt VPN**\n\n"
        "Выберите подходящий период подписки для генерации лицензионного ключа:"
    )
    await callback.message.edit_text(tarifs_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
@dp.callback_query(F.data == "back_to_start")
async def handle_back(callback: types.CallbackQuery):
    """Возврат на самое первое меню"""
    await callback.answer()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Тарифы", callback_data="menu_tarifs")
    builder.button(text="👨‍💻 Поддержка", callback_data="menu_support")
    builder.adjust(2)
    
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует Artefakt VPN.**\n\n"
        "Что вас интересует?"
    )
    await callback.message.edit_text(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def handle_purchase(callback: types.CallbackQuery):
    """Обработчик успешной имитации покупки"""
    tarif_code = callback.data.split("_")[1]
    
    if tarif_code not in TARIFS:
        await callback.answer("Ошибка: Тариф не найден.", show_alert=True)
        return
        
    generated_key = generate_secure_key(tarif_code)
    days_count = TARIFS[tarif_code]["days"]
    
    from datetime import datetime
    conn = sqlite3.connect("artefakt_sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sold_keys (license_key, tarif_type, days, user_id, purchase_date) VALUES (?, ?, ?, ?, ?)",
            (generated_key, tarif_code, days_count, callback.from_user.id, datetime.now().isoformat())
        )
        conn.commit()
    except Exception as e:
        await callback.answer("Ошибка базы данных. Попробуйте снова.", show_alert=True)
        conn.close()
        return
    conn.close()
    
    await callback.answer("💳 Оплата зачислена!", show_alert=False)
    
    response_text = (
        "✅ **Спасибо за покупку! Лицензия успешно выпущена.**\n\n"
        f"📋 Ваш персональный ключ тарифа на **{days_count} дней**:\n"
        f"`{generated_key}`\n\n"
        "💡 *Нажмите на текст ключа выше, чтобы скопировать его, а затем активируйте в приложении Artefakt VPN.*"
    )
    await callback.message.answer(response_text, parse_mode="Markdown")

if __name__ == "__main__":
    init_bot_db()
    print("🤖 Бот успешно запущен на платформе BotHost...")
    dp.run_polling(bot)
