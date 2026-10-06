import asyncio
import logging
import os
import sys
from typing import Dict, Any, List, Set, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ==============================================================================
# 1. КОНФІГУРАЦІЯ ТА СХОВИЩЕ ДАНИХ
# ==============================================================================

ENV_TOKEN = os.getenv("BOT_TOKEN", "8731463697:AAF7ueCUbstPxVHmVDIIVceTzhit2Hjn6J8").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Можна вказати свій Telegram ID для сповіщень

ATOMIZER_FEE = 40  # Вартість тари для розпиву (грн)
DEFAULT_PERFUME_IMG = "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=800&auto=format&fit=crop"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Оперативні структури даних (In-Memory DB)
REGISTERED_USERS: Set[int] = set()
USER_CARTS: Dict[int, List[Dict[str, Any]]] = {}  # user_id -> список товарів у кошику
ORDERS_DB: List[Dict[str, Any]] = []              # Історія всіх замовлень
USER_BOX_BUILDER: Dict[int, List[str]] = {}       # user_id -> список ID для Aroma Box [max 3]


# ==============================================================================
# 2. FSM СТАНИ (Оформлення замовлення та розсилка)
# ==============================================================================

class CheckoutStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_payment = State()


class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()


# ==============================================================================
# 3. ФАБРИКИ КОЛБЕКІВ (CallbackData)
# ==============================================================================

class MainMenuCallback(CallbackData, prefix="menu"):
    target: str


class DecantVolumeCallback(CallbackData, prefix="decant"):
    volume: int


class BrandSelectCallback(CallbackData, prefix="brand"):
    brand_id: str
    mode: str = "full"
    volume: int = 0


class PerfumeViewCallback(CallbackData, prefix="perf"):
    perfume_id: str
    mode: str
    volume: int = 0


class CartActionCallback(CallbackData, prefix="cart"):
    action: str  # "view", "add", "inc", "dec", "remove", "clear", "checkout"
    item_index: int = -1
    perfume_id: str = ""
    mode: str = "full"
    volume: int = 0


class QuizCallback(CallbackData, prefix="quiz"):
    step: str   # "start", "gender", "occasion", "vibe"
    value: str = ""


class AromaBoxCallback(CallbackData, prefix="box"):
    action: str  # "start", "pick", "remove", "finish", "cancel"
    perfume_id: str = ""


class NotesFilterCallback(CallbackData, prefix="notes"):
    category: str


# ==============================================================================
# 4. БАЗА ДАНИХ (PERFUMES_DB) — 15 Брендів із тегами для Сомельє
# ==============================================================================

PERFUMES_DB: Dict[str, Dict[str, Any]] = {
    # 1. Tom Ford
    "tf_tobacco_vanille": {
        "brand_id": "tom_ford",
        "brand": "Tom Ford",
        "name": "Tobacco Vanille",
        "description": "Теплий, величний східний шедевр, натхненний атмосферою англійського джентльменського клубу з прянощами та кубинським тютюном.",
        "top_notes": "Листя тютюну, Пряні акорди",
        "heart_notes": "Боби тонка, Квіти тютюну, Ваніль, Какао",
        "base_notes": "Сухофрукти, Деревні ноти",
        "price_full_bottle": 11500,
        "price_per_ml": 135,
        "gender": "unisex",
        "vibe": "tobacco",
        "occasion": "evening",
        "image_url": "https://images.unsplash.com/photo-1547887537-6158d64c35b3?q=80&w=800&auto=format&fit=crop",
    },
    # 2. Maison Francis Kurkdjian
    "mfk_baccarat_540": {
        "brand_id": "mfk",
        "brand": "Maison Francis Kurkdjian",
        "name": "Baccarat Rouge 540",
        "description": "Легендарна кришталева аура з хвойно-карамельними переливами, цукровою ватою та благородним шафрановим шлейфом.",
        "top_notes": "Шафран, Жасмин",
        "heart_notes": "Сіра амбра, Бурштинове дерево",
        "base_notes": "Ялинова смола, Білий кедр",
        "price_full_bottle": 13200,
        "price_per_ml": 160,
        "gender": "unisex",
        "vibe": "sweet",
        "occasion": "evening",
        "image_url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=800&auto=format&fit=crop",
    },
    # 3. Creed
    "creed_aventus": {
        "brand_id": "creed",
        "brand": "Creed",
        "name": "Aventus",
        "description": "Символ сили, мужності та влади. Витончений димно-фруктовий букет соковитого ананаса, березового диму та мускусу.",
        "top_notes": "Ананас, Бергамот, Чорна смородина, Яблуко",
        "heart_notes": "Береза, Пачулі, Марокканський жасмин, Троянда",
        "base_notes": "Мускус, Дубовий мох, Сіра амбра, Ваніль",
        "price_full_bottle": 14500,
        "price_per_ml": 170,
        "gender": "men",
        "vibe": "woody",
        "occasion": "office",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 4. Kilian
    "kilian_angels_share": {
        "brand_id": "kilian",
        "brand": "Kilian",
        "name": "Angels' Share",
        "description": "П'янкий коньячний акорд, приправлений корицею, праліне та дубовими бочками з витриманим алкоголем.",
        "top_notes": "Коньяк",
        "heart_notes": "Кориця, Боби тонка, Дуб",
        "base_notes": "Праліне, Ваніль, Сандал",
        "price_full_bottle": 9800,
        "price_per_ml": 140,
        "gender": "unisex",
        "vibe": "sweet",
        "occasion": "evening",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 5. Jo Malone
    "jomalone_wood_sage": {
        "brand_id": "jo_malone",
        "brand": "Jo Malone",
        "name": "Wood Sage & Sea Salt",
        "description": "Свіжий вітер скелястого узбережжя, мінеральна морська сіль та землиста свіжість дикої шавлії.",
        "top_notes": "Насіння амбрети",
        "heart_notes": "Морська сіль",
        "base_notes": "Шавлія",
        "price_full_bottle": 5400,
        "price_per_ml": 75,
        "gender": "unisex",
        "vibe": "fresh",
        "occasion": "daily",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 6. Byredo
    "byredo_bal_dafrique": {
        "brand_id": "byredo",
        "brand": "Byredo",
        "name": "Bal d'Afrique",
        "description": "Африканська пристрасть у Парижі 1920-х: сонячний ветивер, солодка фіалка, чорнобривці та теплі цитруси.",
        "top_notes": "Бергамот, Лимон, Неролі, Чорнобривці",
        "heart_notes": "Фіалка, Пелюстки жасмину, Цикламен",
        "base_notes": "Чорна амбра, Мускус, Ветивер, Марокканський кедр",
        "price_full_bottle": 8900,
        "price_per_ml": 115,
        "gender": "unisex",
        "vibe": "floral",
        "occasion": "daily",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 7. Le Labo
    "lelabo_santal_33": {
        "brand_id": "le_labo",
        "brand": "Le Labo",
        "name": "Santal 33",
        "description": "Культовий нішевий сандал з димними шкіряними нотами, листям папірусу та благородним ірисом.",
        "top_notes": "Фіолетова фіалка, Кардамон",
        "heart_notes": "Ірис, Папірус, Амброксан",
        "base_notes": "Кедр, Шкіра, Сандал",
        "price_full_bottle": 11200,
        "price_per_ml": 145,
        "gender": "unisex",
        "vibe": "woody",
        "occasion": "office",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 8. Yves Saint Laurent
    "ysl_black_opium": {
        "brand_id": "ysl",
        "brand": "Yves Saint Laurent",
        "name": "Black Opium",
        "description": "Чуттєвий і зухвалий адреналіновий коктейль із чорної кави, флердоранжу та сексуальної ванілі.",
        "top_notes": "Груша, Рожевий перець, Апельсиновий цвіт",
        "heart_notes": "Кава, Жасмин, Гіркий мигдаль, Лакриця",
        "base_notes": "Ваніль, Пачулі, Кедр, Кашемірове дерево",
        "price_full_bottle": 5800,
        "price_per_ml": 80,
        "gender": "women",
        "vibe": "sweet",
        "occasion": "evening",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 9. Dior
    "dior_sauvage": {
        "brand_id": "dior",
        "brand": "Dior",
        "name": "Sauvage",
        "description": "Радикально свіжий та шляхетний фужер із вибуховим калабрійським бергамотом і шлейфовим амброксаном.",
        "top_notes": "Калабрійський бергамот, Перець",
        "heart_notes": "Сичуанський перець, Лаванда, Рожевий перець, Ветивер",
        "base_notes": "Амброксан, Кедр, Лабданум",
        "price_full_bottle": 5200,
        "price_per_ml": 75,
        "gender": "men",
        "vibe": "fresh",
        "occasion": "daily",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 10. Chanel
    "chanel_bleu_de_chanel": {
        "brand_id": "chanel",
        "brand": "Chanel",
        "name": "Bleu de Chanel",
        "description": "Ода чоловічій свободі та впевненості: глибокий деревно-фужерний баланс цитрусів, м'яти та ладану.",
        "top_notes": "Грейпфрут, Лимон, М'ята, Рожевий перець",
        "heart_notes": "Імбир, Мускатний горіх, Жасмин, Ізо Е Супер",
        "base_notes": "Ладан, Ветивер, Кедр, Сандал, Пачулі",
        "price_full_bottle": 6400,
        "price_per_ml": 90,
        "gender": "men",
        "vibe": "woody",
        "occasion": "office",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 11. Tiziana Terenzi
    "terenzi_kirke": {
        "brand_id": "tiziana_terenzi",
        "brand": "Tiziana Terenzi",
        "name": "Kirke",
        "description": "Магічний фруктовий нектар із солодкої маракуї, персика, малини та фірмового оксамитового мускусу.",
        "top_notes": "Маракуя, Персик, Малина, Листя чорної смородини, Груша",
        "heart_notes": "Конвалія",
        "base_notes": "Геліотроп, Сандал, Ваніль, Пачулі, Мускус",
        "price_full_bottle": 6900,
        "price_per_ml": 95,
        "gender": "women",
        "vibe": "floral",
        "occasion": "daily",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 12. Montale
    "montale_intense_cafe": {
        "brand_id": "montale",
        "brand": "Montale",
        "name": "Intense Cafe",
        "description": "Затишна паризька кав'ярня: аромат свіжозвареної арабіки, ранкової троянди та теплої ванілі.",
        "top_notes": "Квіткові ноти",
        "heart_notes": "Кава, Троянда",
        "base_notes": "Амбра, Білий мускус, Ваніль",
        "price_full_bottle": 4600,
        "price_per_ml": 65,
        "gender": "unisex",
        "vibe": "sweet",
        "occasion": "evening",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 13. Mancera
    "mancera_red_tobacco": {
        "brand_id": "mancera",
        "brand": "Mancera",
        "name": "Red Tobacco",
        "description": "Неймовірно стійкий, гарячий тютюново-пряний еліксир із нотами шафрану, кориці та пахучого уду.",
        "top_notes": "Шафран, Кориця, Ладан, Мускатний горіх, Білий персик",
        "heart_notes": "Пачулі, Жасмин",
        "base_notes": "Тютюн, Амбра, Деревні ноти, Ветивер, Стручки ванілі",
        "price_full_bottle": 5300,
        "price_per_ml": 75,
        "gender": "unisex",
        "vibe": "tobacco",
        "occasion": "evening",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 14. Ex Nihilo
    "ex_nihilo_fleur_narcotique": {
        "brand_id": "ex_nihilo",
        "brand": "Ex Nihilo",
        "name": "Fleur Narcotique",
        "description": "Наркотично привабливий квітковий шлейф півонії, соковитого лічі та білого персика.",
        "top_notes": "Бергамот, Лічі, Персик",
        "heart_notes": "Жасмин, Півонія, Апельсиновий цвіт",
        "base_notes": "Деревні ноти, Мох, Мускус",
        "price_full_bottle": 12800,
        "price_per_ml": 150,
        "gender": "women",
        "vibe": "floral",
        "occasion": "daily",
        "image_url": DEFAULT_PERFUME_IMG,
    },
    # 15. Zarkoperfume
    "zarko_pink_molecule": {
        "brand_id": "zarkoperfume",
        "brand": "Zarkoperfume",
        "name": "Pink Molécule 090.09",
        "description": "Скандинавська естетика: рожеве шампанське, чорна бузина, стиглий абрикос та вершкова молекула.",
        "top_notes": "Бузина, Абрикос, Чорна орхідея, Шампанське",
        "heart_notes": "Молекулярний акорд (без середніх нот)",
        "base_notes": "Махагоні, Вершки, Чорне дерево",
        "price_full_bottle": 4900,
        "price_per_ml": 70,
        "gender": "women",
        "vibe": "floral",
        "occasion": "daily",
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
# 5. ГЕНЕРАЦІЯ КЛАВІАТУР
# ==============================================================================

def get_start_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Головне меню магазину з усіма функціями."""
    builder = InlineKeyboardBuilder()

    # Підрахунок кількості товарів у кошику
    cart_count = len(USER_CARTS.get(user_id, []))
    cart_title = f"🛒 Кошик ({cart_count})" if cart_count > 0 else "🛒 Кошик"

    builder.button(text="💧 На розпив", callback_data=MainMenuCallback(target="decant_select").pack())
    builder.button(text="📦 Цілі парфуми", callback_data=MainMenuCallback(target="brands_select").pack())
    builder.button(text="🧠 Парфумерний сомельє", callback_data=QuizCallback(step="start").pack())
    builder.button(text="🎁 Aroma Box (-15%)", callback_data=AromaBoxCallback(action="start").pack())
    builder.button(text="🔎 Пошук за нотами", callback_data=MainMenuCallback(target="notes_search").pack())
    builder.button(text=cart_title, callback_data=CartActionCallback(action="view").pack())

    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_decant_volumes_keyboard() -> InlineKeyboardMarkup:
    """Вибір об'єму для розпиву."""
    builder = InlineKeyboardBuilder()
    for vol in [3, 5, 10, 15]:
        builder.button(text=f"🧴 {vol} мл", callback_data=DecantVolumeCallback(volume=vol).pack())
    builder.button(text="🔙 Назад у меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_brands_keyboard(mode: str = "full", volume: int = 0) -> InlineKeyboardMarkup:
    """Сітка з 15 брендів."""
    builder = InlineKeyboardBuilder()
    for brand_id, brand_name in BRANDS_REGISTRY.items():
        builder.button(
            text=brand_name,
            callback_data=BrandSelectCallback(brand_id=brand_id, mode=mode, volume=volume).pack()
        )

    back_callback = (
        MainMenuCallback(target="decant_select").pack()
        if mode == "decant"
        else MainMenuCallback(target="root").pack()
    )
    builder.button(text="🔙 Назад", callback_data=back_callback)
    builder.adjust(2)
    return builder.as_markup()


def get_brand_perfumes_keyboard(brand_id: str, mode: str = "full", volume: int = 0) -> InlineKeyboardMarkup:
    """Список парфумів обраного бренду БЕЗ цін на кнопках."""
    builder = InlineKeyboardBuilder()
    filtered = [(p_id, item) for p_id, item in PERFUMES_DB.items() if item["brand_id"] == brand_id]

    for p_id, item in filtered:
        builder.button(
            text=f"✨ {item['name']}",
            callback_data=PerfumeViewCallback(perfume_id=p_id, mode=mode, volume=volume).pack()
        )

    back_callback = (
        DecantVolumeCallback(volume=volume).pack()
        if mode == "decant"
        else MainMenuCallback(target="brands_select").pack()
    )
    builder.button(text="🔙 Назад до брендів", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


def get_perfume_card_keyboard(perfume_id: str, mode: str, volume: int) -> InlineKeyboardMarkup:
    """Кнопки картки товару."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🛍 Додати в кошик",
        callback_data=CartActionCallback(
            action="add",
            perfume_id=perfume_id,
            mode=mode,
            volume=volume
        ).pack()
    )
    builder.button(text="🛒 Перейти в кошик", callback_data=CartActionCallback(action="view").pack())

    brand_id = PERFUMES_DB[perfume_id]["brand_id"]
    builder.button(
        text="🔙 Назад до списку",
        callback_data=BrandSelectCallback(brand_id=brand_id, mode=mode, volume=volume).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


def get_cart_keyboard(cart_items: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Кнопки кошика з можливістю видалення та переходу до оформлення."""
    builder = InlineKeyboardBuilder()

    if cart_items:
        builder.button(text="🚚 Оформити замовлення", callback_data=CartActionCallback(action="checkout").pack())
        for idx, item in enumerate(cart_items):
            builder.button(
                text=f"❌ Видалити №{idx + 1}",
                callback_data=CartActionCallback(action="remove", item_index=idx).pack()
            )
        builder.button(text="🗑 Очистити кошик", callback_data=CartActionCallback(action="clear").pack())

    builder.button(text="🔙 Продовжити покупки", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)
    return builder.as_markup()


def get_notes_categories_keyboard() -> InlineKeyboardMarkup:
    """Категорії нот для швидкого пошуку."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌿 Свіжі & Цитрусові", callback_data=NotesFilterCallback(category="fresh").pack())
    builder.button(text="🍂 Тютюнові & Пряні", callback_data=NotesFilterCallback(category="tobacco").pack())
    builder.button(text="🍨 Солодкі & Ванільні", callback_data=NotesFilterCallback(category="sweet").pack())
    builder.button(text="🪵 Деревні & Сандал", callback_data=NotesFilterCallback(category="woody").pack())
    builder.button(text="🌸 Квіткові & Фруктові", callback_data=NotesFilterCallback(category="floral").pack())
    builder.button(text="🔙 Назад у меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)
    return builder.as_markup()


# ==============================================================================
# 6. ХЕЛПЕРИ ВІДОБРАЖЕННЯ
# ==============================================================================

async def render_text_screen(call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    """Безпечне перемикання між екранами з фото та звичайними повідомленнями."""
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await call.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def format_perfume_caption(item: Dict[str, Any], mode: str, volume: int) -> str:
    """Форматування картки товару: акцент на ароматі, ціна в кінці."""
    if mode == "decant":
        price = (item["price_per_ml"] * volume) + ATOMIZER_FEE
        price_section = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Вартість розпиву:</b> <b>{price} грн</b> "
            f"<i>(за {volume} мл у скляному атомайзері зі спреєм)</i>"
        )
    else:
        price_section = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Вартість флакона:</b> <b>{item['price_full_bottle']} грн</b> "
            f"<i>(новий запечатаний флакон у фірмовій коробці)</i>"
        )

    caption = (
        f"🏷 <b>Бренд:</b> {item['brand']}\n"
        f"📌 <b>Аромат:</b> {item['name']}\n\n"
        f"📖 <b>Опис звучання:</b>\n<i>{item['description']}</i>\n\n"
        f"🎼 <b>Верхні ноти:</b> {item['top_notes']}\n"
        f"💖 <b>Середні ноти:</b> {item['heart_notes']}\n"
        f"🎵 <b>Кінцеві ноти:</b> {item['base_notes']}\n\n"
        f"{price_section}"
    )
    return caption


def format_cart_message(cart_items: List[Dict[str, Any]]) -> str:
    """Генерація тексту вмісту кошика."""
    if not cart_items:
        return "🛒 <b>Ваш кошик порожній.</b>\n\nОберіть аромати в каталозі або створіть власний Aroma Box!"

    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0

    for i, item in enumerate(cart_items, start=1):
        lines.append(
            f"<b>{i}. {item['brand']} — {item['name']}</b>\n"
            f"   • Формат: {item['type_label']}\n"
            f"   • Ціна: <b>{item['price']} грн</b>\n"
        )
        total += item['price']

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"💳 <b>Разом до сплати:</b> <b>{total} грн</b>")
    return "\n".join(lines)


# ==============================================================================
# 7. МАРШРУТИЗАЦІЯ ТА ОСНОВНІ ХЕНДЛЕРИ
# ==============================================================================

dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Стартове привітання та реєстрація користувача."""
    await state.clear()
    REGISTERED_USERS.add(message.from_user.id)

    welcome_text = (
        f"👋 <b>Вітаємо у бутіку нішевої парфумерії, {message.from_user.first_name}!</b>\n\n"
        "У нас ви можете замовити оригінальні цілі флакони або обрати розпив у скляні атомайзери.\n\n"
        "✨ Скористайтеся <b>«Парфумерним сомельє»</b>, якщо вагаєтеся з вибором, "
        "або збережіть до 15% із сетом <b>«Aroma Box»</b>!"
    )
    await message.answer(
        text=welcome_text,
        reply_markup=get_start_keyboard(message.from_user.id),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(MainMenuCallback.filter())
async def handle_main_navigation(call: CallbackQuery, callback_data: MainMenuCallback) -> None:
    """Навігація по розділах головного меню."""
    await call.answer()

    if callback_data.target == "root":
        text = "Головне меню магазину парфумерії:\nОберіть розділ, який вас цікавить:"
        await render_text_screen(call, text, get_start_keyboard(call.from_user.id))

    elif callback_data.target == "decant_select":
        text = (
            "💧 <b>Оберіть бажаний об'єм для розпиву:</b>\n\n"
            "<i>Усі відливанти фасуються у скляні флакони зі спреєм безпосередньо перед відправкою.</i>"
        )
        await render_text_screen(call, text, get_decant_volumes_keyboard())

    elif callback_data.target == "brands_select":
        text = "📦 <b>Оберіть бренд парфуму:</b>\n\n<i>Повні оригінальні флакони у фірмовому пакуванні.</i>"
        await render_text_screen(call, text, get_brands_keyboard(mode="full", volume=0))

    elif callback_data.target == "notes_search":
        text = "🔎 <b>Пошук ароматів за нотами та настроєм:</b>\nОберіть бажаний напрямок звучання:"
        await render_text_screen(call, text, get_notes_categories_keyboard())


@dp.callback_query(DecantVolumeCallback.filter())
async def handle_decant_volume(call: CallbackQuery, callback_data: DecantVolumeCallback) -> None:
    """Вибір об'єму розпиву -> відображення брендів."""
    await call.answer()
    vol = callback_data.volume
    text = f"💧 <b>Розпив ({vol} мл) — Оберіть бренд:</b>\n<i>Оберіть компанію для перегляду ароматів:</i>"
    await render_text_screen(call, text, get_brands_keyboard(mode="decant", volume=vol))


@dp.callback_query(BrandSelectCallback.filter())
async def handle_brand_select(call: CallbackQuery, callback_data: BrandSelectCallback) -> None:
    """Вибір бренду -> список ароматів без цін."""
    await call.answer()
    brand_id = callback_data.brand_id
    brand_name = BRANDS_REGISTRY.get(brand_id, "Бренд")
    mode = callback_data.mode
    volume = callback_data.volume

    prefix = f"💧 Розпив ({volume} мл) — " if mode == "decant" else "📦 "
    text = f"{prefix}<b>Аромати бренду {brand_name}:</b>\n\n<i>Оберіть композицію для знайомства з нотами:</i>"
    await render_text_screen(call, text, get_brand_perfumes_keyboard(brand_id, mode=mode, volume=volume))


@dp.callback_query(PerfumeViewCallback.filter())
async def handle_perfume_card(call: CallbackQuery, callback_data: PerfumeViewCallback) -> None:
    """Показ повної картки парфуму з фото."""
    await call.answer()
    item = PERFUMES_DB.get(callback_data.perfume_id)
    if not item:
        await call.answer("❌ Товар не знайдено", show_alert=True)
        return

    caption = format_perfume_caption(item, callback_data.mode, callback_data.volume)
    keyboard = get_perfume_card_keyboard(callback_data.perfume_id, callback_data.mode, callback_data.volume)

    await call.message.delete()
    await call.message.answer_photo(
        photo=item.get("image_url", DEFAULT_PERFUME_IMG),
        caption=caption,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# ==============================================================================
# 8. МОДУЛЬ КОШИКА (Shopping Cart)
# ==============================================================================

@dp.callback_query(CartActionCallback.filter())
async def handle_cart_actions(call: CallbackQuery, callback_data: CartActionCallback, state: FSMContext) -> None:
    """Керування кошиком: додавання, видалення, перегляд, старт чек-ауту."""
    user_id = call.from_user.id
    if user_id not in USER_CARTS:
        USER_CARTS[user_id] = []

    action = callback_data.action

    if action == "add":
        item = PERFUMES_DB.get(callback_data.perfume_id)
        if not item:
            await call.answer("Помилка додавання", show_alert=True)
            return

        if callback_data.mode == "decant":
            price = (item["price_per_ml"] * callback_data.volume) + ATOMIZER_FEE
            type_label = f"Розпив {callback_data.volume} мл"
        else:
            price = item["price_full_bottle"]
            type_label = "Повний флакон"

        cart_item = {
            "perfume_id": callback_data.perfume_id,
            "brand": item["brand"],
            "name": item["name"],
            "price": price,
            "type_label": type_label,
        }
        USER_CARTS[user_id].append(cart_item)
        await call.answer(f"✅ {item['name']} додано до кошика!", show_alert=False)

    elif action == "view":
        await call.answer()
        cart_text = format_cart_message(USER_CARTS[user_id])
        await render_text_screen(call, cart_text, get_cart_keyboard(USER_CARTS[user_id]))

    elif action == "remove":
        idx = callback_data.item_index
        if 0 <= idx < len(USER_CARTS[user_id]):
            removed = USER_CARTS[user_id].pop(idx)
            await call.answer(f"Видалено: {removed['name']}")
        cart_text = format_cart_message(USER_CARTS[user_id])
        await render_text_screen(call, cart_text, get_cart_keyboard(USER_CARTS[user_id]))

    elif action == "clear":
        USER_CARTS[user_id].clear()
        await call.answer("Кошик очищено!")
        cart_text = format_cart_message([])
        await render_text_screen(call, cart_text, get_cart_keyboard([]))

    elif action == "checkout":
        if not USER_CARTS[user_id]:
            await call.answer("Кошик порожній!", show_alert=True)
            return

        await call.answer()
        await state.set_state(CheckoutStates.waiting_for_name)
        text = (
            "🚚 <b>Оформлення замовлення (Крок 1/3)</b>\n\n"
            "Введіть, будь ласка, ваші <b>Прізвище та Ім'я</b> для доставки Новою Поштою:"
        )
        await render_text_screen(call, text, InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Скасувати", callback_data=CartActionCallback(action="view").pack())
        ]]))


# ==============================================================================
# 9. ЧЕК-АУТ (FSM: Оформлення замовлення з Новою Поштою)
# ==============================================================================

@dp.message(CheckoutStates.waiting_for_name)
async def checkout_name_received(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer("Будь ласка, введіть коректне ім'я та прізвище:")
        return

    await state.update_data(customer_name=full_name)
    await state.set_state(CheckoutStates.waiting_for_phone)

    # Запит телефону з можливістю відправити контакт
    btn = KeyboardButton(text="📱 Поділитися контактом", request_contact=True)
    markup = ReplyKeyboardMarkup(keyboard=[[btn]], resize_keyboard=True, one_time_keyboard=True)

    await message.answer(
        "📞 <b>Крок 2/3: Номер телефону</b>\n\n"
        "Натисніть кнопку нижче або введіть номер вручну (наприклад, 0971234567):",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )


@dp.message(CheckoutStates.waiting_for_phone)
async def checkout_phone_received(message: Message, state: FSMContext) -> None:
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    await state.update_data(customer_phone=phone)
    await state.set_state(CheckoutStates.waiting_for_address)

    await message.answer(
        "📦 <b>Крок 3/3: Доставка Новою Поштою</b>\n\n"
        "Вкажіть ваше <b>Місто та номер відділення</b> (або поштомату):\n"
        "<i>Приклад: Київ, відділення №42</i>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )


@dp.message(CheckoutStates.waiting_for_address)
async def checkout_address_received(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    await state.update_data(customer_address=address)

    data = await state.get_data()
    user_id = message.from_user.id
    items = USER_CARTS.get(user_id, [])
    total = sum(i["price"] for i in items)

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплата на картку / Monobank", callback_data="pay_card")
    builder.button(text="💵 Накладений платіж (при отриманні)", callback_data="pay_cod")
    builder.adjust(1)

    summary = (
        "📋 <b>Перевірка даних замовлення:</b>\n\n"
        f"👤 Отримувач: <b>{data['customer_name']}</b>\n"
        f"📞 Телефон: <b>{data['customer_phone']}</b>\n"
        f"📦 Доставка: <b>{address}</b>\n"
        f"💰 До сплати: <b>{total} грн</b> ({len(items)} тов.)\n\n"
        "Оберіть зручний спосіб оплати:"
    )
    await message.answer(summary, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.in_(["pay_card", "pay_cod"]))
async def finalize_order(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Фіналізація замовлення, генерація номеру та сповіщення."""
    await call.answer()
    data = await state.get_data()
    user_id = call.from_user.id
    items = USER_CARTS.get(user_id, [])
    total = sum(i["price"] for i in items)

    order_id = f"#{len(ORDERS_DB) + 1042}"
    pay_type = "Оплата на картку (Monobank)" if call.data == "pay_card" else "Накладений платіж"

    order_record = {
        "order_id": order_id,
        "user_id": user_id,
        "username": call.from_user.username or "Невідомо",
        "name": data.get("customer_name"),
        "phone": data.get("customer_phone"),
        "address": data.get("customer_address"),
        "items": items.copy(),
        "total": total,
        "payment": pay_type,
    }
    ORDERS_DB.append(order_record)
    USER_CARTS[user_id].clear()
    await state.clear()

    # Повідомлення клієнту
    client_msg = (
        f"🎉 <b>Дякуємо! Ваше замовлення {order_id} успішно прийнято!</b>\n\n"
        f"📦 Доставка: <b>{order_record['address']}</b>\n"
        f"💳 Сума: <b>{total} грн</b> ({pay_type})\n\n"
        f"Менеджер зв'яжеться з вами найближчим часом для відправки ТТН."
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 На головну", callback_data=MainMenuCallback(target="root").pack())
    await render_text_screen(call, client_msg, builder.as_markup())

    # Сповіщення в лог / Адміну
    admin_alert = (
        f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ {order_id}!</b>\n\n"
        f"👤 Клієнт: {order_record['name']} (@{order_record['username']})\n"
        f"📞 Телефон: {order_record['phone']}\n"
        f"📍 Адреса: {order_record['address']}\n"
        f"💰 Сума: <b>{total} грн</b> ({pay_type})\n\n"
        f"🛍 <b>Товари:</b>\n" +
        "\n".join([f"• {it['brand']} — {it['name']} ({it['type_label']}) — {it['price']} грн" for it in items])
    )
    logger.info(f"Замовлення {order_id} оформлено на суму {total} грн.")

    if ADMIN_ID > 0:
        try:
            await bot.send_message(chatId=ADMIN_ID, text=admin_alert, parseMode=ParseMode.HTML)
        except Exception:
            pass


# ==============================================================================
# 10. МОДУЛЬ «ПАРФУМЕРНИЙ СОМЕЛЬЄ» (Quiz)
# ==============================================================================

@dp.callback_query(QuizCallback.filter(F.step == "start"))
async def quiz_start(call: CallbackQuery) -> None:
    """Початок тесту сомельє."""
    await call.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Чоловічий", callback_data=QuizCallback(step="gender", value="men").pack())
    builder.button(text="👩 Жіночий", callback_data=QuizCallback(step="gender", value="women").pack())
    builder.button(text="✨ Унісекс", callback_data=QuizCallback(step="gender", value="unisex").pack())
    builder.button(text="🔙 Назад", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(2, 1, 1)

    text = "🧠 <b>Парфумерний сомельє (Крок 1/3)</b>\n\nДля кого підбираємо аромат?"
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(QuizCallback.filter(F.step == "gender"))
async def quiz_step_occasion(call: CallbackQuery, callback_data: QuizCallback) -> None:
    await call.answer()
    gender = callback_data.value

    builder = InlineKeyboardBuilder()
    builder.button(text="☀️ На кожен день", callback_data=QuizCallback(step="occasion", value=f"{gender}:daily").pack())
    builder.button(text="🌙 Вечірній / Побачення", callback_data=QuizCallback(step="occasion", value=f"{gender}:evening").pack())
    builder.button(text="💼 Статусний / В офіс", callback_data=QuizCallback(step="occasion", value=f"{gender}:office").pack())
    builder.button(text="🔙 Скасувати", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)

    text = "🧠 <b>Парфумерний сомельє (Крок 2/3)</b>\n\nДля якої атмосфери та події шукаєте парфум?"
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(QuizCallback.filter(F.step == "occasion"))
async def quiz_step_vibe(call: CallbackQuery, callback_data: QuizCallback) -> None:
    await call.answer()
    prev = callback_data.value

    builder = InlineKeyboardBuilder()
    builder.button(text="🌿 Свіжий & Морський", callback_data=QuizCallback(step="vibe", value=f"{prev}:fresh").pack())
    builder.button(text="🍨 Солодкий & Ванільний", callback_data=QuizCallback(step="vibe", value=f"{prev}:sweet").pack())
    builder.button(text="🍂 Тютюновий & Пряний", callback_data=QuizCallback(step="vibe", value=f"{prev}:tobacco").pack())
    builder.button(text="🪵 Деревний & Сандал", callback_data=QuizCallback(step="vibe", value=f"{prev}:woody").pack())
    builder.button(text="🌸 Квітковий & Фруктовий", callback_data=QuizCallback(step="vibe", value=f"{prev}:floral").pack())
    builder.adjust(1)

    text = "🧠 <b>Парфумерний сомельє (Крок 3/3)</b>\n\nЯкий напрямок звучання вам найближчий?"
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(QuizCallback.filter(F.step == "vibe"))
async def quiz_result(call: CallbackQuery, callback_data: QuizCallback) -> None:
    await call.answer()
    parts = callback_data.value.split(":")
    gender, occasion, vibe = parts[0], parts[1], parts[2]

    # Алгоритм підбору за схожістю тегів
    matches = []
    for p_id, item in PERFUMES_DB.items():
        score = 0
        if item.get("vibe") == vibe:
            score += 3
        if item.get("occasion") == occasion:
            score += 2
        if item.get("gender") == gender or item.get("gender") == "unisex":
            score += 1
        matches.append((score, p_id, item))

    matches.sort(key=lambda x: x[0], reverse=True)
    top_3 = matches[:3]

    builder = InlineKeyboardBuilder()
    for _, p_id, item in top_3:
        builder.button(
            text=f"✨ {item['brand']} — {item['name']}",
            callback_data=PerfumeViewCallback(perfume_id=p_id, mode="full", volume=0).pack()
        )
    builder.button(text="🔄 Пройти тест знову", callback_data=QuizCallback(step="start").pack())
    builder.button(text="🏠 Головне меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)

    text = (
        "🎯 <b>Персональна рекомендація парфумерного сомельє:</b>\n\n"
        "На основі ваших відповідей ми підібрали ідеальні композиції з нашої колекції:\n"
    )
    for i, (_, _, it) in enumerate(top_3, start=1):
        text += f"\n<b>{i}. {it['brand']} — {it['name']}</b>\n<i>«{it['description'][:70]}...»</i>\n"

    await render_text_screen(call, text, builder.as_markup())


# ==============================================================================
# 11. МОДУЛЬ «AROMA BOX» (Сет розпивів зі знижкою 15%)
# ==============================================================================

@dp.callback_query(AromaBoxCallback.filter(F.action == "start"))
async def box_start(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    USER_BOX_BUILDER[user_id] = []
    await box_render_picker(call, user_id)


async def box_render_picker(call: CallbackQuery, user_id: int) -> None:
    selected = USER_BOX_BUILDER.get(user_id, [])
    count = len(selected)

    builder = InlineKeyboardBuilder()

    if count < 3:
        # Показуємо доступні для додавання аромати
        for p_id, item in PERFUMES_DB.items():
            if p_id not in selected:
                builder.button(
                    text=f"➕ {item['name']}",
                    callback_data=AromaBoxCallback(action="pick", perfume_id=p_id).pack()
                )
    else:
        builder.button(
            text="🎁 Додати Aroma Box у кошик (-15%)",
            callback_data=AromaBoxCallback(action="finish").pack()
        )

    builder.button(text="🔙 Скасувати", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(2)

    selected_names = [PERFUMES_DB[pid]["name"] for pid in selected]
    selected_text = ", ".join(selected_names) if selected_names else "ще не обрано"

    text = (
        f"🎁 <b>Конструктор Aroma Box ({count}/3 обрано)</b>\n\n"
        "Створіть свій сет із <b>3 будь-яких ароматів по 5 мл</b> зі спеціальною знижкою <b>15%</b>!\n\n"
        f"Обрані аромати: <b>{selected_text}</b>\n\n"
        f"{'Оберіть ще аромати зі списку нижче:' if count < 3 else '🎉 Ваш сет готовий! Натисніть кнопку нижче, щоб додати його до кошика.'}"
    )
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(AromaBoxCallback.filter(F.action == "pick"))
async def box_pick_item(call: CallbackQuery, callback_data: AromaBoxCallback) -> None:
    user_id = call.from_user.id
    if user_id not in USER_BOX_BUILDER:
        USER_BOX_BUILDER[user_id] = []

    if len(USER_BOX_BUILDER[user_id]) < 3:
        USER_BOX_BUILDER[user_id].append(callback_data.perfume_id)
        await call.answer("Додано до боксу!")

    await box_render_picker(call, user_id)


@dp.callback_query(AromaBoxCallback.filter(F.action == "finish"))
async def box_finish(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    selected = USER_BOX_BUILDER.get(user_id, [])

    if len(selected) != 3:
        await call.answer("Оберіть рівно 3 аромати!", show_alert=True)
        return

    # Розрахунок вартості з урахуванням знижки 15%
    raw_price = sum((PERFUMES_DB[pid]["price_per_ml"] * 5) + ATOMIZER_FEE for pid in selected)
    discounted_price = int(raw_price * 0.85)

    names = " + ".join([PERFUMES_DB[pid]["name"] for pid in selected])

    if user_id not in USER_CARTS:
        USER_CARTS[user_id] = []

    USER_CARTS[user_id].append({
        "perfume_id": "aroma_box_custom",
        "brand": "Aroma Box Exclusive",
        "name": f"Сет із 3 ароматів ({names})",
        "price": discounted_price,
        "type_label": "3 x 5 мл зі знижкою 15%",
    })

    USER_BOX_BUILDER[user_id].clear()
    await call.answer("🎉 Aroma Box успішно додано до кошика!", show_alert=True)

    cart_text = format_cart_message(USER_CARTS[user_id])
    await render_text_screen(call, cart_text, get_cart_keyboard(USER_CARTS[user_id]))


# ==============================================================================
# 12. МОДУЛЬ «ПОШУК ЗА НОТАМИ»
# ==============================================================================

@dp.callback_query(NotesFilterCallback.filter())
async def filter_by_notes(call: CallbackQuery, callback_data: NotesFilterCallback) -> None:
    await call.answer()
    category = callback_data.category

    filtered = [(pid, it) for pid, it in PERFUMES_DB.items() if it.get("vibe") == category]

    builder = InlineKeyboardBuilder()
    for pid, it in filtered:
        builder.button(
            text=f"✨ {it['brand']} — {it['name']}",
            callback_data=PerfumeViewCallback(perfume_id=pid, mode="full", volume=0).pack()
        )
    builder.button(text="🔙 Назад до вибору нот", callback_data=MainMenuCallback(target="notes_search").pack())
    builder.adjust(1)

    category_titles = {
        "fresh": "🌿 Свіжі, Цитрусові та Морські",
        "tobacco": "🍂 Тютюнові, Пряні та Східні",
        "sweet": "🍨 Солодкі, Ванільні та Гурманські",
        "woody": "🪵 Деревні, Шкіряні та Сандалові",
        "floral": "🌸 Квіткові та Стиглі Фруктові",
    }
    title = category_titles.get(category, "Аромати")

    text = f"🔎 <b>{title}:</b>\n\nОберіть парфум для перегляду піраміди:"
    await render_text_screen(call, text, builder.as_markup())


# ==============================================================================
# 13. АДМІН-ПАНЕЛЬ ТА СТАТИСТИКА (/admin)
# ==============================================================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    total_users = len(REGISTERED_USERS)
    total_orders = len(ORDERS_DB)
    total_revenue = sum(o["total"] for o in ORDERS_DB)

    text = (
        "👑 <b>Панель керування магазином:</b>\n\n"
        f"👥 Зареєстрованих користувачів: <b>{total_users}</b>\n"
        f"📦 Усього замовлень: <b>{total_orders}</b>\n"
        f"💰 Загальна виручка: <b>{total_revenue} грн</b>\n\n"
        "Команди адміністратора:\n"
        "• /broadcast — Надіслати розсилку всім клієнтам бота"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await message.answer("✍️ Введіть текст повідомлення для розсилки (або напишіть 'скасувати'):")


@dp.message(AdminStates.waiting_for_broadcast_text)
async def cmd_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip()
    await state.clear()

    if text.lower() == "скасувати":
        await message.answer("Розсилку скасовано.")
        return

    sent_count = 0
    for uid in REGISTERED_USERS:
        try:
            await bot.send_message(uid, f"📢 <b>Новина від нашого магазину:</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ Розсилку успішно надіслано <b>{sent_count}</b> користувачам!", parse_mode=ParseMode.HTML)


# ==============================================================================
# 14. ТОЧКА ВХОДУ (BOOTSTRAP)
# ==============================================================================

async def main() -> None:
    bot = Bot(token=ENV_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    print("\n" + "=" * 55)
    print(f"🌟 ПОВНОФУНКЦІОНАЛЬНИЙ БОТ @{bot_info.username} ЗАПУЩЕНИЙ!")
    print(f"🔗 Посилання: https://t.me/{bot_info.username}")
    print("=" * 55 + "\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Роботу бота завершено.")
