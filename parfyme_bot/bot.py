import asyncio
import logging
import os
import sys
from typing import Dict, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==============================================================================
# 1. КОНФІГУРАЦІЯ ТА НАЛАШТУВАННЯ
# ==============================================================================

# Токен бота (отриманий від @BotFather)
ENV_TOKEN = os.getenv("BOT_TOKEN", "8731463697:AAF7ueCUbstPxVHmVDIIVceTzhit2Hjn6J8").strip()

# Вартість скляного атомайзера для розпиву (грн)
ATOMIZER_FEE = 40

# Фото-заглушка для парфумерії (з Unsplash)
DEFAULT_PERFUME_IMG = "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=800&auto=format&fit=crop"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 2. ФАБРИКИ КОЛБЕКІВ (CallbackData)
# ==============================================================================

class MainMenuCallback(CallbackData, prefix="menu"):
    """Навігація головного меню."""
    target: str  # "root", "decant_select", "brands_select"


class DecantVolumeCallback(CallbackData, prefix="decant"):
    """Вибір об'єму для розпиву (мл)."""
    volume: int  # 3, 5, 10, 15


class BrandSelectCallback(CallbackData, prefix="brand"):
    """Вибір конкретного бренду."""
    brand_id: str


class PerfumeViewCallback(CallbackData, prefix="perf"):
    """
    Перегляд картки аромату.
    mode: 'full' — повний флакон; 'decant' — розпив.
    volume: актуальний тільки при mode == 'decant'.
    """
    perfume_id: str
    mode: str
    volume: int = 0


class OrderCallback(CallbackData, prefix="order"):
    """Оформлення замовлення (кнопка 'Замовити')."""
    perfume_id: str
    mode: str
    volume: int = 0


# ==============================================================================
# 3. БАЗА ДАНИХ (PERFUMES_DB) — 15 Брендів
# ==============================================================================

PERFUMES_DB: Dict[str, Dict[str, Any]] = {
    # 1. Tom Ford
    "tf_tobacco_vanille": {
        "brand_id": "tom_ford",
        "brand": "Tom Ford",
        "name": "Tobacco Vanille",
        "description": "Теплий, пряний, величний східний шедевр, натхненний атмосферою англійського джентльменського клубу.",
        "top_notes": "Листя тютюну, Пряні акорди",
        "heart_notes": "Боби тонка, Квіти тютюну, Ваніль, Какао",
        "base_notes": "Сухофрукти, Деревні ноти",
        "price_full_bottle": 11500,
        "price_per_ml": 135,
        "image_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?q=80&w=800&auto=format&fit=crop",
    },
    # 2. Maison Francis Kurkdjian
    "mfk_baccarat_540": {
        "brand_id": "mfk",
        "brand": "Maison Francis Kurkdjian",
        "name": "Baccarat Rouge 540",
        "description": "Легендарна кришталева аура з хвойно-карамельними переливами та благородним шафрановим шлейфом.",
        "top_notes": "Шафран, Жасмин",
        "heart_notes": "Сіра амбра, Бурштинове дерево",
        "base_notes": "Ялинова смола, Білий кедр",
        "price_full_bottle": 13200,
        "price_per_ml": 160,
        "image_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=800&auto=format&fit=crop",
    },
    # 3. Creed
    "creed_aventus": {
        "brand_id": "creed",
        "brand": "Creed",
        "name": "Aventus",
        "description": "Символ сили, успіху та мужності. Витончений димно-фруктовий букет для харизматичних лідерів.",
        "top_notes": "Ананас, Бергамот, Чорна смородина, Яблуко",
        "heart_notes": "Береза, Пачулі, Марокканський жасмин, Троянда",
        "base_notes": "Мускус, Дубовий мох, Сіра амбра, Ваніль",
        "price_full_bottle": 14500,
        "price_per_ml": 170,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 4. Kilian
    "kilian_angels_share": {
        "brand_id": "kilian",
        "brand": "Kilian",
        "name": "Angels' Share",
        "description": "П'янкий коньячний акорд, приправлений корицею та дубовою бочкою. Аромат затишку і розкоші.",
        "top_notes": "Коньяк",
        "heart_notes": "Кориця, Боби тонка, Дуб",
        "base_notes": "Праліне, Ваніль, Сандал",
        "price_full_bottle": 9800,
        "price_per_ml": 140,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 5. Jo Malone
    "jomalone_wood_sage": {
        "brand_id": "jo_malone",
        "brand": "Jo Malone",
        "name": "Wood Sage & Sea Salt",
        "description": "Свіжий вітер скелястого узбережжя, мінеральна сіль та землиста свіжість шавлії.",
        "top_notes": "Насіння амбрети",
        "heart_notes": "Морська сіль",
        "base_notes": "Шавлія",
        "price_full_bottle": 5400,
        "price_per_ml": 75,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 6. Byredo
    "byredo_bal_dafrique": {
        "brand_id": "byredo",
        "brand": "Byredo",
        "name": "Bal d'Afrique",
        "description": "Любовний лист до африканської культури 1920-х у Парижі: сонячний ветивер, фіалка та цитруси.",
        "top_notes": "Бергамот, Лимон, Неролі, Чорнобривці",
        "heart_notes": "Фіалка, Пелюстки жасмину, Цикламен",
        "base_notes": "Чорна амбра, Мускус, Ветивер, Марокканський кедр",
        "price_full_bottle": 8900,
        "price_per_ml": 115,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 7. Le Labo
    "lelabo_santal_33": {
        "brand_id": "le_labo",
        "brand": "Le Labo",
        "name": "Santal 33",
        "description": "Культовий нішевий сандал з димними шкіряними нотами, фіалкою та пряним кардамоном.",
        "top_notes": "Фіолетова фіалка, Кардамон",
        "heart_notes": "Ірис, Папірус, Амброксан",
        "base_notes": "Кедр, Шкіра, Сандал",
        "price_full_bottle": 11200,
        "price_per_ml": 145,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 8. Yves Saint Laurent
    "ysl_black_opium": {
        "brand_id": "ysl",
        "brand": "Yves Saint Laurent",
        "name": "Black Opium",
        "description": "Чуттєвий і зухвалий адреналіновий коктейль із чорної кави, білих квітів та спокусливої ванілі.",
        "top_notes": "Груша, Рожевий перець, Апельсиновий цвіт",
        "heart_notes": "Кава, Жасмин, Гіркий мигдаль, Лакриця",
        "base_notes": "Ваніль, Пачулі, Кедр, Кашемірове дерево",
        "price_full_bottle": 5800,
        "price_per_ml": 80,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 9. Dior
    "dior_sauvage": {
        "brand_id": "dior",
        "brand": "Dior",
        "name": "Sauvage",
        "description": "Радикально свіжий та шляхетний фужер із вибуховим калабрійським бергамотом і амброксаном.",
        "top_notes": "Калабрійський бергамот, Перець",
        "heart_notes": "Сичуанський перець, Лаванда, Рожевий перець, Ветивер",
        "base_notes": "Амброксан, Кедр, Лабданум",
        "price_full_bottle": 5200,
        "price_per_ml": 75,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 10. Chanel
    "chanel_bleu_de_chanel": {
        "brand_id": "chanel",
        "brand": "Chanel",
        "name": "Bleu de Chanel",
        "description": "Ода чоловічій свободі у глибокому деревно-фужерному звучанні з витонченим французьким шармом.",
        "top_notes": "Грейпфрут, Лимон, М'ята, Рожевий перець",
        "heart_notes": "Імбир, Мускатний горіх, Жасмин, Ізо Е Супер",
        "base_notes": "Ладан, Ветивер, Кедр, Сандал, Пачулі",
        "price_full_bottle": 6400,
        "price_per_ml": 90,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 11. Tiziana Terenzi
    "terenzi_kirke": {
        "brand_id": "tiziana_terenzi",
        "brand": "Tiziana Terenzi",
        "name": "Kirke",
        "description": "Магічний фруктовий нектар із солодкої маракуї, персика та фірмового оксамитового мускусу.",
        "top_notes": "Маракуя, Персик, Малина, Листя чорної смородини, Груша",
        "heart_notes": "Конвалія",
        "base_notes": "Геліотроп, Сандал, Ваніль, Пачулі, Мускус",
        "price_full_bottle": 6900,
        "price_per_ml": 95,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 12. Montale
    "montale_intense_cafe": {
        "brand_id": "montale",
        "brand": "Montale",
        "name": "Intense Cafe",
        "description": "Затишна кав'ярня в серці Парижа: свіжозварена арабіка, чайна троянда та тягуча ваніль.",
        "top_notes": "Квіткові ноти",
        "heart_notes": "Кава, Троянда",
        "base_notes": "Амбра, Білий мускус, Ваніль",
        "price_full_bottle": 4600,
        "price_per_ml": 65,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 13. Mancera
    "mancera_red_tobacco": {
        "brand_id": "mancera",
        "brand": "Mancera",
        "name": "Red Tobacco",
        "description": "Неймовірно стійкий, гарячий тютюново-пряний еліксир із нотами кубинського тютюну та уду.",
        "top_notes": "Шафран, Кориця, Ладан, Мускатний горіх, Білий персик",
        "heart_notes": "Пачулі, Жасмин",
        "base_notes": "Тютюн, Амбра, Деревні ноти, Ветивер, Стручки ванілі",
        "price_full_bottle": 5300,
        "price_per_ml": 75,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 14. Ex Nihilo
    "ex_nihilo_fleur_narcotique": {
        "brand_id": "ex_nihilo",
        "brand": "Ex Nihilo",
        "name": "Fleur Narcotique",
        "description": "Наркотично привабливий квітковий шлейф півонії та соковитого лічі. Аромат сучасної елегантності.",
        "top_notes": "Бергамот, Лічі, Персик",
        "heart_notes": "Жасмин, Півонія, Апельсиновий цвіт",
        "base_notes": "Деревні ноти, Мох, Мускус",
        "price_full_bottle": 12800,
        "price_per_ml": 150,
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 15. Zarkoperfume
    "zarko_pink_molecule": {
        "brand_id": "zarkoperfume",
        "brand": "Zarkoperfume",
        "name": "Pink Molécule 090.09",
        "description": "Скандинавська естетика: рожеве ігристе шампанське, чорна бузина та вершково-деревна молекула.",
        "top_notes": "Бузина, Абрикос, Чорна орхідея, Шампанське",
        "heart_notes": "Молекулярний акорд (без середніх нот)",
        "base_notes": "Махагоні, Вершки, Чорне дерево",
        "price_full_bottle": 4900,
        "price_per_ml": 70,
        "image_url": DEFAULT_PERFUME_IMG,
    },
}

BRANDS_REGISTRY: Dict[str, str] = {
    "tom_ford": "Tom Ford",
    "mfk": "Maison Francis Kurkdjian",
    "creed": "Creed",
    "kilian": "Kilian",
    "jo_malone": "Jo Malone",
    "byredo": "Byredo",
    "le_labo": "Le Labo",
    "ysl": "Yves Saint Laurent",
    "dior": "Dior",
    "chanel": "Chanel",
    "tiziana_terenzi": "Tiziana Terenzi",
    "montale": "Montale",
    "mancera": "Mancera",
    "ex_nihilo": "Ex Nihilo",
    "zarkoperfume": "Zarkoperfume",
}


# ==============================================================================
# 4. ГЕНЕРАЦІЯ КЛАВІАТУР (InlineKeyboardBuilder)
# ==============================================================================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Головне меню: Розпив або Цілі парфуми."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💧 На розпив",
        callback_data=MainMenuCallback(target="decant_select").pack()
    )
    builder.button(
        text="📦 Цілі парфуми",
        callback_data=MainMenuCallback(target="brands_select").pack()
    )
    builder.adjust(2)
    return builder.as_markup()


def get_decant_volumes_keyboard() -> InlineKeyboardMarkup:
    """Вибір об'єму для розпиву + повернення в головне меню."""
    builder = InlineKeyboardBuilder()
    for vol in [3, 5, 10, 15]:
        builder.button(
            text=f"🧴 {vol} мл",
            callback_data=DecantVolumeCallback(volume=vol).pack()
        )
    builder.button(
        text="🔙 Назад",
        callback_data=MainMenuCallback(target="root").pack()
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_decant_perfumes_keyboard(volume: int) -> InlineKeyboardMarkup:
    """Список усіх ароматів з бази для обраного об'єму розпиву."""
    builder = InlineKeyboardBuilder()
    for p_id, item in PERFUMES_DB.items():
        price = (item["price_per_ml"] * volume) + ATOMIZER_FEE
        builder.button(
            text=f"{item['brand']} — {item['name']} ({price} грн)",
            callback_data=PerfumeViewCallback(perfume_id=p_id, mode="decant", volume=volume).pack()
        )
    builder.button(
        text="🔙 Назад до об'ємів",
        callback_data=MainMenuCallback(target="decant_select").pack()
    )
    builder.adjust(1)
    return builder.as_markup()


def get_brands_keyboard() -> InlineKeyboardMarkup:
    """Список із 15 брендів."""
    builder = InlineKeyboardBuilder()
    for brand_id, brand_name in BRANDS_REGISTRY.items():
        builder.button(
            text=brand_name,
            callback_data=BrandSelectCallback(brand_id=brand_id).pack()
        )
    builder.button(
        text="🔙 Назад",
        callback_data=MainMenuCallback(target="root").pack()
    )
    builder.adjust(2)
    return builder.as_markup()


def get_brand_perfumes_keyboard(brand_id: str) -> InlineKeyboardMarkup:
    """Список парфумів вибраного бренду."""
    builder = InlineKeyboardBuilder()
    filtered = [
        (p_id, item) for p_id, item in PERFUMES_DB.items()
        if item["brand_id"] == brand_id
    ]

    for p_id, item in filtered:
        builder.button(
            text=f"{item['name']} ({item['price_full_bottle']} грн)",
            callback_data=PerfumeViewCallback(perfume_id=p_id, mode="full", volume=0).pack()
        )

    builder.button(
        text="🔙 Назад до брендів",
        callback_data=MainMenuCallback(target="brands_select").pack()
    )
    builder.adjust(1)
    return builder.as_markup()


def get_perfume_card_keyboard(perfume_id: str, mode: str, volume: int) -> InlineKeyboardMarkup:
    """Кнопки картки товару: Замовити та Назад."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🛒 Замовити",
        callback_data=OrderCallback(perfume_id=perfume_id, mode=mode, volume=volume).pack()
    )

    if mode == "decant":
        back_callback = DecantVolumeCallback(volume=volume).pack()
    else:
        brand_id = PERFUMES_DB[perfume_id]["brand_id"]
        back_callback = BrandSelectCallback(brand_id=brand_id).pack()

    builder.button(
        text="🔙 Назад до списку",
        callback_data=back_callback
    )
    builder.adjust(1)
    return builder.as_markup()


# ==============================================================================
# 5. ХЕЛПЕРИ ВІДОБРАЖЕННЯ
# ==============================================================================

async def render_text_screen(call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    """Безпечне перемикання між текстовими екранами та повідомленнями з фото."""
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await call.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def format_perfume_caption(item: Dict[str, Any], mode: str, volume: int) -> str:
    """Форматування картки товару згідно з ТЗ."""
    if mode == "decant":
        calculated_price = (item["price_per_ml"] * volume) + ATOMIZER_FEE
        price_line = f"💰 Ціна: <b>{calculated_price}</b> грн. <i>({volume} мл у скляному атомайзері)</i>"
    else:
        price_line = f"💰 Ціна: <b>{item['price_full_bottle']}</b> грн. <i>(новий запечатаний флакон)</i>"

    caption = (
        f"🏷 <b>Бренд:</b> {item['brand']}\n"
        f"📌 <b>Назва:</b> {item['name']}\n\n"
        f"📖 <b>Опис:</b> {item['description']}\n\n"
        f"🎼 <b>Верхні ноти:</b> {item['top_notes']}\n"
        f"💖 <b>Середні ноти:</b> {item['heart_notes']}\n"
        f"🎵 <b>Кінцеві ноти:</b> {item['base_notes']}\n\n"
        f"{price_line}"
    )
    return caption


# ==============================================================================
# 6. МАРШРУТИЗАЦІЯ ТА ОБРОБНИКИ ПОДІЙ
# ==============================================================================

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обробник команди /start."""
    welcome_text = (
        "Вітаємо у нашому магазині парфумерії! Оберіть категорію, яка вас цікавить:"
    )
    await message.answer(
        text=welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(MainMenuCallback.filter())
async def handle_main_navigation(call: CallbackQuery, callback_data: MainMenuCallback) -> None:
    """Навігація по головних гілках."""
    await call.answer()

    if callback_data.target == "root":
        text = "Вітаємо у нашому магазині парфумерії! Оберіть категорію, яка вас цікавить:"
        await render_text_screen(call, text, get_start_keyboard())

    elif callback_data.target == "decant_select":
        text = "Оберіть бажаний об'єм для розпиву:"
        await render_text_screen(call, text, get_decant_volumes_keyboard())

    elif callback_data.target == "brands_select":
        text = "Оберіть бренд парфуму:"
        await render_text_screen(call, text, get_brands_keyboard())


@dp.callback_query(DecantVolumeCallback.filter())
async def handle_decant_volume(call: CallbackQuery, callback_data: DecantVolumeCallback) -> None:
    """Обробка обраного об'єму розпиву -> список парфумів."""
    await call.answer()
    vol = callback_data.volume
    text = f"💧 <b>Список парфумів на розпив ({vol} мл):</b>\nОберіть аромат для перегляду деталей:"
    await render_text_screen(call, text, get_decant_perfumes_keyboard(vol))


@dp.callback_query(BrandSelectCallback.filter())
async def handle_brand_select(call: CallbackQuery, callback_data: BrandSelectCallback) -> None:
    """Обробка обраного бренду -> список ароматів компанії."""
    await call.answer()
    brand_id = callback_data.brand_id
    brand_name = BRANDS_REGISTRY.get(brand_id, "Бренд")
    text = f"📦 <b>Оберіть парфум бренду {brand_name}:</b>"
    await render_text_screen(call, text, get_brand_perfumes_keyboard(brand_id))


@dp.callback_query(PerfumeViewCallback.filter())
async def handle_perfume_card(call: CallbackQuery, callback_data: PerfumeViewCallback) -> None:
    """Вивід картки парфуму з фото та характеристиками."""
    await call.answer()
    item = PERFUMES_DB.get(callback_data.perfume_id)

    if not item:
        await call.answer("❌ Товар не знайдено", show_alert=True)
        return

    caption = format_perfume_caption(item, callback_data.mode, callback_data.volume)
    keyboard = get_perfume_card_keyboard(
        perfume_id=callback_data.perfume_id,
        mode=callback_data.mode,
        volume=callback_data.volume
    )

    await call.message.delete()
    await call.message.answer_photo(
        photo=item.get("image_url", DEFAULT_PERFUME_IMG),
        caption=caption,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(OrderCallback.filter())
async def handle_order_click(call: CallbackQuery, callback_data: OrderCallback) -> None:
    """Обробник натискання кнопки 'Замовити'."""
    item = PERFUMES_DB.get(callback_data.perfume_id)
    if not item:
        await call.answer("❌ Товар недоступний", show_alert=True)
        return

    if callback_data.mode == "decant":
        price = (item["price_per_ml"] * callback_data.volume) + ATOMIZER_FEE
        details = f"{item['name']} ({callback_data.volume} мл) — {price} грн"
    else:
        details = f"{item['name']} (повний флакон) — {item['price_full_bottle']} грн"

    alert_text = (
        f"Товар додано до кошика!\n\n"
        f"🛍 {item['brand']}: {details}\n\n"
        f"Менеджер зв'яжеться з вами найближчим часом для відправки!"
    )
    await call.answer(alert_text, show_alert=True)


# ==============================================================================
# 7. ЗАПУСК БОТА (Entry point)
# ==============================================================================

async def main() -> None:
    token = ENV_TOKEN
    if not token:
        print("\n" + "=" * 50)
        print("🌸 PARFYME BOT — Запуск магазину парфумерії")
        print("=" * 50)
        print("[?] Змінна середовища BOT_TOKEN не знайдена.")
        token = input("👉 Введіть токен бота від @BotFather: ").strip()

    if not token:
        logger.error("Токен не вказано. Завершення роботи.")
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Скидаємо накопичені оновлення
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    print("\n" + "-" * 50)
    print(f"✅ Бот @{bot_info.username} успішно запущений!")
    print(f"🔗 Посилання: https://t.me/{bot_info.username}")
    print("Натисніть Ctrl+C для зупинки.\n" + "-" * 50 + "\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Роботу бота завершено.")
