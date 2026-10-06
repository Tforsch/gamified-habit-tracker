import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Set

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo,
    MenuButtonWebApp,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==============================================================================
# 1. КОНФІГУРАЦІЯ ТА СХОВИЩЕ ДАНИХ
# ==============================================================================

ENV_TOKEN = os.getenv("BOT_TOKEN", "8731463697:AAF7ueCUbstPxVHmVDIIVceTzhit2Hjn6J8").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://tforsch.github.io/gamified-habit-tracker/").strip()

ATOMIZER_FEE = 40  # Вартість тари для розпиву (грн)
DEFAULT_PERFUME_IMG = "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?q=80&w=800&auto=format&fit=crop"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Оперативні структури даних
REGISTERED_USERS: Set[int] = set()
USER_CARTS: Dict[int, List[Dict[str, Any]]] = {}   # user_id -> список товарів
ORDERS_DB: List[Dict[str, Any]] = []               # історія замовлень
USER_BOX_BUILDER: Dict[int, List[str]] = {}        # user_id -> [perfume_id, ...] (до 3)


# ==============================================================================
# 2. FSM СТАНИ
# ==============================================================================

class CheckoutStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_payment = State()


class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()


# ==============================================================================
# 3. КОЛБЕК-ДАТА (CallbackData)
# ==============================================================================

class MainMenuCallback(CallbackData, prefix="menu"):
    target: str


class DecantVolumeCallback(CallbackData, prefix="decant"):
    volume: int


class BrandSelectCallback(CallbackData, prefix="brand"):
    brand_id: str
    mode: str = "full"  # "full" або "decant"
    volume: int = 0


class PerfumeViewCallback(CallbackData, prefix="perf"):
    perfume_id: str
    mode: str = "full"
    volume: int = 0


class CartActionCallback(CallbackData, prefix="cart"):
    action: str  # "view", "add", "remove", "clear", "checkout"
    item_index: int = -1
    perfume_id: str = ""
    mode: str = "full"
    volume: int = 0


class SommelierCallback(CallbackData, prefix="som"):
    step: str      # "start", "g", "o", "v"
    g: str = ""    # gender: m, w, u
    o: str = ""    # occasion: d (день), e (вечір), c (холод/затишок), s (літо/свіжість)
    v: str = ""    # vibe: f (fresh), s (sweet), t (tobacco), w (woody), fl (floral)


class AromaBoxCallback(CallbackData, prefix="box"):
    action: str        # "menu", "brand", "pick", "remove", "finish", "reset"
    brand_id: str = ""
    perfume_id: str = ""


class NotesFilterCallback(CallbackData, prefix="notes"):
    category: str


# ==============================================================================
# 4. БАЗА ДАНИХ (15 Брендів x 6 Ароматів = 90 парфумів)
# ==============================================================================

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

PERFUMES_DB: Dict[str, Dict[str, Any]] = {
    # ---------------- 1. TOM FORD ----------------
    "tf_tobacco_vanille": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Tobacco Vanille",
        "description": "Теплий, величний східний шедевр джентльменського клубу: елітний тютюн, прянощі, боби тонка та солодка ваніль.",
        "top_notes": "Листя тютюну, Східні прянощі", "heart_notes": "Боби тонка, Квіти тютюну, Ваніль, Какао", "base_notes": "Сухофрукти, Деревний акорд",
        "price_full_bottle": 11500, "price_per_ml": 135, "gender": "u", "occasion": "e", "vibe": "t"
    },
    "tf_lost_cherry": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Lost Cherry",
        "description": "Спокусливий, насичений вишневий лікер з гірким мигдалем, турецькою трояндою та п'янким перуанським бальзамом.",
        "top_notes": "Чорна вишня, Лікер, Гіркий мигдаль", "heart_notes": "Вишня гріот, Турецька троянда, Жасмин самбак", "base_notes": "Перуанський бальзам, Боби тонка, Сандал, Ветивер",
        "price_full_bottle": 12800, "price_per_ml": 155, "gender": "w", "occasion": "e", "vibe": "s"
    },
    "tf_bitter_peach": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Bitter Peach",
        "description": "Соковитий, дозрілий на сонці персик, змочений у дорогому ромі та коньяку, із пряним шлейфом пачулі.",
        "top_notes": "Персик, Червоний апельсин, Кардамон", "heart_notes": "Ром, Коньяк, Давана, Жасмин", "base_notes": "Пачулі, Сандал, Ваніль, Боби тонка, Лабданум",
        "price_full_bottle": 12500, "price_per_ml": 150, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "tf_oud_wood": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Oud Wood",
        "description": "Один із найвишуканіших деревних ароматів: димний уд, палісандр, кардамон і вершковий сандал.",
        "top_notes": "Палісандр, Кардамон, Сичуанський перець", "heart_notes": "Удове дерево, Сандал, Ветивер", "base_notes": "Боби тонка, Ваніль, Бурштин",
        "price_full_bottle": 11900, "price_per_ml": 140, "gender": "m", "occasion": "d", "vibe": "w"
    },
    "tf_black_orchid": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Black Orchid",
        "description": "Містичний, сексуальний аромат чорної трюфельної орхідеї, чорного шоколаду, пачулі та ладану.",
        "top_notes": "Чорний трюфель, Іланг-іланг, Бергамот, Чорна смородина", "heart_notes": "Чорна орхідея, Спеції, Лотос", "base_notes": "Пачулі, Ладан, Ваніль, Темний шоколад",
        "price_full_bottle": 7900, "price_per_ml": 95, "gender": "w", "occasion": "e", "vibe": "floral"
    },
    "tf_fucking_fabulous": {
        "brand_id": "tom_ford", "brand": "Tom Ford", "name": "Fucking Fabulous",
        "description": "Відвертий східно-шкіряний аромат гіркого мигдалю, дорогої шкіри, лаванди та пудрового ірису.",
        "top_notes": "Лаванда, Мускатна шавлія", "heart_notes": "Гіркий мигдаль, Шкіра, Корінь ірису", "base_notes": "Шкіра, Боби тонка, Кашмеран, Біла амбра",
        "price_full_bottle": 13500, "price_per_ml": 160, "gender": "u", "occasion": "e", "vibe": "w"
    },

    # ---------------- 2. MAISON FRANCIS KURKDJIAN ----------------
    "mfk_baccarat_540": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "Baccarat Rouge 540",
        "description": "Кришталеве звучання шафрану, солодкої ялинової смоли та мінеральної сірої амбри.",
        "top_notes": "Шафран, Жасмин", "heart_notes": "Сіра амбра, Деревний бурштин", "base_notes": "Ялинова смола, Білий кедр",
        "price_full_bottle": 13200, "price_per_ml": 160, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "mfk_baccarat_extrait": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "Baccarat Rouge 540 Extrait",
        "description": "Концентрована, глибша версія культового аромату з нотами гіркого марокканського мигдалю та мускусу.",
        "top_notes": "Гіркий мигдаль, Шафран", "heart_notes": "Єгипетський жасмин, Кедр", "base_notes": "Сіра амбра, Деревні ноти, Мускус",
        "price_full_bottle": 15800, "price_per_ml": 190, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "mfk_grand_soir": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "Grand Soir",
        "description": "Розкіш паризького вечора: теплий золотистий бурштин, сіамський бензоїн, боби тонка та м'яка ваніль.",
        "top_notes": "Лабданум, Кориандр", "heart_notes": "Сіамський бензоїн, Боби тонка", "base_notes": "Амбра, Ваніль",
        "price_full_bottle": 10900, "price_per_ml": 130, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "mfk_gentle_fluidity_gold": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "Gentle Fluidity Gold",
        "description": "Ніжний, огортаючий шлейф повітряної ванілі, ягід ялівцю, мускатного горіха та мускусу.",
        "top_notes": "Ягоди ялівцю, Мускатний горіх", "heart_notes": "Коріандр", "base_notes": "Ваніль, Мускус, Амбра, Деревні акорди",
        "price_full_bottle": 9900, "price_per_ml": 120, "gender": "w", "occasion": "d", "vibe": "s"
    },
    "mfk_gentle_fluidity_silver": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "Gentle Fluidity Silver",
        "description": "Свіжий, металевий, джин-тоніковий вибух ялівцю, мускату та прохолодного лісового дерева.",
        "top_notes": "Ялівцеві ягоди, Мускатний горіх", "heart_notes": "Коріандр", "base_notes": "Деревні ноти, Мускус, Ваніль",
        "price_full_bottle": 9900, "price_per_ml": 120, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "mfk_724": {
        "brand_id": "mfk", "brand": "Maison Francis Kurkdjian", "name": "724",
        "description": "Аромат чистоти мегаполісу 24/7: білі альдегіди, бергамот, жасмин та білий мускус свіжовипраної білизни.",
        "top_notes": "Альдегіди, Калабрійський бергамот", "heart_notes": "Жасмин, Солодкий горошок, Чубушник", "base_notes": "Білий мускус, Сандал",
        "price_full_bottle": 9800, "price_per_ml": 120, "gender": "u", "occasion": "d", "vibe": "f"
    },

    # ---------------- 3. CREED ----------------
    "creed_aventus": {
        "brand_id": "creed", "brand": "Creed", "name": "Aventus",
        "description": "Еталон чоловічої харизми: соковитий ананас, яблуко, березовий дим, пачулі та сіра амбра.",
        "top_notes": "Ананас, Бергамот, Чорна смородина, Яблуко", "heart_notes": "Береза, Пачулі, Жасмин, Троянда", "base_notes": "Мускус, Дубовий мох, Сіра амбра, Ваніль",
        "price_full_bottle": 14500, "price_per_ml": 170, "gender": "m", "occasion": "d", "vibe": "w"
    },
    "creed_silver_mountain": {
        "brand_id": "creed", "brand": "Creed", "name": "Silver Mountain Water",
        "description": "Кришталева свіжість гірського струмка в Альпах: зелений чай, чорна смородина, бергамот і озоновий мускус.",
        "top_notes": "Бергамот, Мандарин", "heart_notes": "Зелений чай, Чорна смородина", "base_notes": "Мускус, Петитгрейн, Сандал, Гальбанум",
        "price_full_bottle": 12500, "price_per_ml": 150, "gender": "u", "occasion": "s", "vibe": "f"
    },
    "creed_green_irish_tweed": {
        "brand_id": "creed", "brand": "Creed", "name": "Green Irish Tweed",
        "description": "Класика аристократичної Англії: прохолодна скошена трава, вербена, листя фіалки та ірис.",
        "top_notes": "Лимонна вербена, Ірис", "heart_notes": "Листя фіалки", "base_notes": "Сіра амбра, Сандал",
        "price_full_bottle": 11900, "price_per_ml": 140, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "creed_millesime_imperial": {
        "brand_id": "creed", "brand": "Creed", "name": "Millésime Impérial",
        "description": "Сонячний морський бриз Сицилії: морська сіль, свіжі фрукти, цитруси та шляхетний мускус.",
        "top_notes": "Морська сіль, Фруктові ноти", "heart_notes": "Сицилійський лимон, Бергамот, Ірис, Мандарин", "base_notes": "Морські ноти, Мускус, Деревні ноти",
        "price_full_bottle": 12200, "price_per_ml": 145, "gender": "u", "occasion": "s", "vibe": "f"
    },
    "creed_aventus_for_her": {
        "brand_id": "creed", "brand": "Creed", "name": "Aventus for Her",
        "description": "Жіноча версія бестселера: зелене яблуко, рожевий перець, калабрійський бергамот, троянда та персик.",
        "top_notes": "Зелене яблуко, Бергамот, Пачулі, Лимон, Рожевий перець", "heart_notes": "Мускус, Троянда, Сандал, Стиракс", "base_notes": "Чорна смородина, Персик, Бурштин, Іланг-іланг",
        "price_full_bottle": 13900, "price_per_ml": 165, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "creed_viking": {
        "brand_id": "creed", "brand": "Creed", "name": "Viking",
        "description": "Вогняний дух скандинавських морів: калабрійський бергамот, рожевий перець, перцева м'ята та лаванда.",
        "top_notes": "Рожевий перець, Калабрійський бергамот, Сицилійський лимон", "heart_notes": "Перцева м'ята, Болгарська троянда", "base_notes": "Сандал, Ветивер, Пачулі, Лаванда",
        "price_full_bottle": 11500, "price_per_ml": 140, "gender": "m", "occasion": "e", "vibe": "t"
    },

    # ---------------- 4. KILIAN ----------------
    "kilian_angels_share": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Angels' Share",
        "description": "П'янкий акорд дорогого коньяку з дубової бочки, пряна кориця, вершкове праліне та ваніль.",
        "top_notes": "Коньяк", "heart_notes": "Кориця, Боби тонка, Дуб", "base_notes": "Праліне, Ваніль, Сандал",
        "price_full_bottle": 9800, "price_per_ml": 140, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "kilian_love_dont_be_shy": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Love, Don't Be Shy",
        "description": "Улюблений парфум Ріанни: ніжний зефір маршмелоу, апельсиновий цвіт, жимолость та солодкий цукор.",
        "top_notes": "Неролі, Бергамот, Рожевий перець, Коріандр", "heart_notes": "Апельсиновий цвіт, Жасмин, Жимолость, Троянда, Ірис", "base_notes": "Цукор, Ваніль, Карамель, Мускус",
        "price_full_bottle": 10500, "price_per_ml": 150, "gender": "w", "occasion": "e", "vibe": "s"
    },
    "kilian_good_girl_gone_bad": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Good Girl Gone Bad",
        "description": "Квітковий вихор невинності та гріха: медовий османтус, травнева троянда, тубероза та нарцис.",
        "top_notes": "Османтус, Жасмин, Травнева троянда", "heart_notes": "Індійська тубероза, Нарцис", "base_notes": "Амбра, Білий кедр",
        "price_full_bottle": 10500, "price_per_ml": 150, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "kilian_black_phantom": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Black Phantom",
        "description": "Піратський скарб: чорна міцна кава, карибський ром, цукрова тростина, гіркий мигдаль і темний шоколад.",
        "top_notes": "Ром, Цукрова тростина", "heart_notes": "Темний шоколад, Кава, Карамель, Мигдаль", "base_notes": "Геліотроп, Сандал",
        "price_full_bottle": 10800, "price_per_ml": 150, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "kilian_vodka_on_the_rocks": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Vodka on the Rocks",
        "description": "Льодяний крижаний коктейль: морозний кардамон, коріандр, ревінь, конвалія та дубовий мох.",
        "top_notes": "Коріандр, Кардамон, Альдегіди", "heart_notes": "Ревінь, Конвалія, Троянда", "base_notes": "Дубовий мох, Амброксан, Сандал",
        "price_full_bottle": 9900, "price_per_ml": 140, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "kilian_apple_brandy": {
        "brand_id": "kilian", "brand": "Kilian", "name": "Apple Brandy on the Rocks",
        "description": "Нічний Нью-Йорк: хрустке яблуко, витриманий бренді, кедр, мох та ванільні акорди.",
        "top_notes": "Кардамон, Бергамот", "heart_notes": "Яблуко, Бренді, Ром, Ананас, Ваніль", "base_notes": "Амброксан, Кедр",
        "price_full_bottle": 9500, "price_per_ml": 135, "gender": "u", "occasion": "e", "vibe": "s"
    },

    # ---------------- 5. JO MALONE ----------------
    "jm_wood_sage": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "Wood Sage & Sea Salt",
        "description": "Свіжий вітер скелястого узбережжя Британії: морська мінеральна сіль, насіння амбрети та шавлія.",
        "top_notes": "Насіння амбрети", "heart_notes": "Морська сіль", "base_notes": "Шавлія",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "u", "occasion": "d", "vibe": "f"
    },
    "jm_english_pear": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "English Pear & Freesia",
        "description": "Осінній англійський сад: соковита медова груша Вільямс, біла білосніжна фрезія та пачулі.",
        "top_notes": "Груша, Диня", "heart_notes": "Фрезія, Троянда", "base_notes": "Мускус, Пачулі, Ревінь, Амбра",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "jm_peony_blush": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "Peony & Blush Suede",
        "description": "Розкішні квітучі півонії, хрустке соковите червоне яблуко, жасмин та ніжна рожева замша.",
        "top_notes": "Червоне яблуко", "heart_notes": "Півонія, Жасмин, Гвоздика, Троянда", "base_notes": "Замша",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "jm_blackberry_bay": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "Blackberry & Bay",
        "description": "Спогади дитинства про збирання ожини: терпкий сік темних ягід, свіже листя лавра та білий кедр.",
        "top_notes": "Ожина", "heart_notes": "Листя лавра", "base_notes": "Кедр, Ветивер",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "u", "occasion": "d", "vibe": "f"
    },
    "jm_myrrh_tonka": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "Myrrh & Tonka",
        "description": "Східна глибина колекції Intense: лавандовий старт, дорогоцінна смола мірри та мигдальні боби тонка.",
        "top_notes": "Лаванда", "heart_notes": "Омманська мірра", "base_notes": "Боби тонка, Ваніль, Мигдаль",
        "price_full_bottle": 6800, "price_per_ml": 95, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "jm_lime_basil": {
        "brand_id": "jo_malone", "brand": "Jo Malone", "name": "Lime Basil & Mandarin",
        "description": "Фірмова класика бренду: карибський лайм, соковитий мандарин, перцевий базилік та білий чебрець.",
        "top_notes": "Лайм, Мандарин, Бергамот", "heart_notes": "Базилік, Бузок, Ірис, Чебрець", "base_notes": "Пачулі, Ветивер",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "u", "occasion": "s", "vibe": "f"
    },

    # ---------------- 6. BYREDO ----------------
    "byredo_bal_dafrique": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Bal d'Afrique",
        "description": "Сонячний Париж 20-х років: солодкий ветивер, чорнобривці, бергамот, фіалка та мускус.",
        "top_notes": "Бергамот, Лимон, Неролі, Чорнобривці", "heart_notes": "Фіалка, Жасмин, Цикламен", "base_notes": "Чорна амбра, Мускус, Ветивер, Марокканський кедр",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "u", "occasion": "d", "vibe": "floral"
    },
    "byredo_gypsy_water": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Gypsy Water",
        "description": "Магія циганської свободи біля вогнища: соснові голки, ялівець, цитруси, ладан і тепла ваніль.",
        "top_notes": "Бергамот, Лимон, Перець, Ялівець", "heart_notes": "Ладан, Соснові голки, Корінь ірису", "base_notes": "Амбра, Ваніль, Сандал",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "u", "occasion": "d", "vibe": "w"
    },
    "byredo_blanche": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Blanche",
        "description": "Апогей білого кольору та чистоти: біла троянда, альдегіди, півонія, неролі та шовковистий сандал.",
        "top_notes": "Альдегіди, Біла троянда, Рожевий перець", "heart_notes": "Півонія, Фіалка, Апельсиновий цвіт", "base_notes": "Мускус, Сандал",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "w", "occasion": "d", "vibe": "f"
    },
    "byredo_mojave_ghost": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Mojave Ghost",
        "description": "Квітка-привид пустелі Мохаве: ямайська саподіла, мускусна амбрета, магнолія, фіалка та кедр.",
        "top_notes": "Саподіла, Амбрета", "heart_notes": "Магнолія, Фіалка, Сандал", "base_notes": "Сіра амбра, Кедр",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "u", "occasion": "d", "vibe": "floral"
    },
    "byredo_rose_of_no_mans": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Rose of No Man's Land",
        "description": "Шляхетна, прохолодна турецька троянда, прикрашена рожевим перцем, малиновим цвітом та білою амброю.",
        "top_notes": "Рожевий перець, Пелюстки турецької троянди", "heart_notes": "Цвіт малини, Абсолют турецької троянди", "base_notes": "Папірус, Біла амбра",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "byredo_young_rose": {
        "brand_id": "byredo", "brand": "Byredo", "name": "Young Rose",
        "description": "Сучасна, бунтівна ода молодості: сичуанський гострий перець, амбрета, дамаська троянда та ірис.",
        "top_notes": "Сичуанський перець, Амбрета", "heart_notes": "Дамаська троянда, Корінь ірису", "base_notes": "Мускус, Амброксан",
        "price_full_bottle": 8900, "price_per_ml": 115, "gender": "w", "occasion": "d", "vibe": "floral"
    },

    # ---------------- 7. LE LABO ----------------
    "lelabo_santal_33": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "Santal 33",
        "description": "Легенда нішевого Нью-Йорка: австралійський сандал, димна шкіра, листя папірусу, кедр та фіалка.",
        "top_notes": "Фіалка, Кардамон", "heart_notes": "Ірис, Папірус, Амброксан", "base_notes": "Кедр, Шкіра, Сандал",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "d", "vibe": "w"
    },
    "lelabo_the_noir_29": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "The Noir 29",
        "description": "Поетична ода чорному благородному чаю: соковитий інжир, лавровий лист, чорний чай, тютюн і кедр.",
        "top_notes": "Бергамот, Інжир, Лавр", "heart_notes": "Кедр, Ветивер, Мускус", "base_notes": "Сіно, Тютюн, Чорний чай",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "e", "vibe": "t"
    },
    "lelabo_another_13": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "Another 13",
        "description": "Гіпнотична синтетична молекула амброксану, соковита хрустка груша, яблуко, жасмин та мох.",
        "top_notes": "Груша, Яблуко, Цитруси", "heart_notes": "Амброксан, Саліцилати, Жасмин", "base_notes": "Ізо Е Супер, Мускус, Мох",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "d", "vibe": "f"
    },
    "lelabo_rose_31": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "Rose 31",
        "description": "Нетипова троянда для чоловіків та сміливих жінок: троянда центіфолія, зігріваючий кмин, ветивер і уд.",
        "top_notes": "Троянда, Кмин", "heart_notes": "Троянда, Ветивер, Кедр", "base_notes": "Мускус, Гуаяк, Уд, Лабданум",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "e", "vibe": "floral"
    },
    "lelabo_bergamote_22": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "Bergamote 22",
        "description": "Іскристий бергамотовий спалах з петитгрейном, грейпфрутом, бурштином, мускусом і ветивером.",
        "top_notes": "Бергамот, Грейпфрут", "heart_notes": "Петитгрейн, Апельсиновий цвіт", "base_notes": "Ветивер, Кедр, Мускус, Амбра",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "s", "vibe": "f"
    },
    "lelabo_baie_19": {
        "brand_id": "le_labo", "brand": "Le Labo", "name": "Baie 19",
        "description": "Запах землі після літнього дощу (петрикор): вологе листя, ялівець, пачулі та зелені ягоди.",
        "top_notes": "Сухе листя, Ягоди ялівцю", "heart_notes": "Пачулі, Зелені ноти", "base_notes": "Амброксан, Мускус",
        "price_full_bottle": 11200, "price_per_ml": 145, "gender": "u", "occasion": "d", "vibe": "f"
    },

    # ---------------- 8. YVES SAINT LAURENT ----------------
    "ysl_black_opium": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Black Opium",
        "description": "Адреналіновий коктейль із чорної міцної кави, білих квітів жасмину, груші та спокусливої ванілі.",
        "top_notes": "Груша, Рожевий перець, Апельсиновий цвіт", "heart_notes": "Кава, Жасмин, Гіркий мигдаль", "base_notes": "Ваніль, Пачулі, Кедр, Кашемірове дерево",
        "price_full_bottle": 5800, "price_per_ml": 80, "gender": "w", "occasion": "e", "vibe": "s"
    },
    "ysl_libre": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Libre",
        "description": "Квінтесенція жіночої свободи: французька лаванда, марокканський апельсиновий цвіт і мадагаскарська ваніль.",
        "top_notes": "Лаванда, Мандарин, Чорна смородина, Петитгрейн", "heart_notes": "Лаванда, Апельсиновий цвіт, Жасмин", "base_notes": "Мадагаскарська ваніль, Мускус, Кедр, Сіра амбра",
        "price_full_bottle": 5900, "price_per_ml": 80, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "ysl_y_edp": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Y Eau de Parfum",
        "description": "Сучасний чоловічий фужер: соковите яблуко, пряний свіжий імбир, шавлія, ягоди ялівцю та боби тонка.",
        "top_notes": "Яблуко, Імбир, Бергамот", "heart_notes": "Шавлія, Ягоди ялівцю, Герань", "base_notes": "Бурштинове дерево, Боби тонка, Кедр, Ветивер",
        "price_full_bottle": 5500, "price_per_ml": 75, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "ysl_tuxedo": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Tuxedo",
        "description": "Ексклюзивна бутікова лінійка: димні пачулі, матове темне листя, коріандр, чорний перець та сіра амбра.",
        "top_notes": "Листя фіалки, Бергамот, Коріандр", "heart_notes": "Троянда, Чорний перець, Конвалія", "base_notes": "Пачулі, Сіра амбра, Бурбонська ваніль",
        "price_full_bottle": 10500, "price_per_ml": 135, "gender": "u", "occasion": "e", "vibe": "w"
    },
    "ysl_babycat": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Babycat",
        "description": "Рідкісний гурманський шедевр: бурбонська ваніль, замша, олібанум, елемі та чорний перець.",
        "top_notes": "Рожевий перець, Чорний перець, Елемі", "heart_notes": "Олібанум, Шафран", "base_notes": "Бурбонська ваніль, Замша, Кедр",
        "price_full_bottle": 11900, "price_per_ml": 150, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "ysl_mon_paris": {
        "brand_id": "ysl", "brand": "Yves Saint Laurent", "name": "Mon Paris",
        "description": "Закоханість у Парижі: стигла полуниця, малина, груша, калабрійський бергамот, півонія та дурман.",
        "top_notes": "Полуниця, Малина, Груша, Калабрійський бергамот", "heart_notes": "Дурман, Півонія, Апельсиновий цвіт, Жасмин", "base_notes": "Білий мускус, Пачулі, Кедр, Амброксан",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "w", "occasion": "d", "vibe": "floral"
    },

    # ---------------- 9. DIOR ----------------
    "dior_sauvage": {
        "brand_id": "dior", "brand": "Dior", "name": "Sauvage",
        "description": "Шляхетний та зухвалий фужер: вибуховий калабрійський бергамот, сичуанський перець та амброксан.",
        "top_notes": "Калабрійський бергамот, Перець", "heart_notes": "Сичуанський перець, Лаванда, Рожевий перець, Ветивер", "base_notes": "Амброксан, Кедр, Лабданум",
        "price_full_bottle": 5200, "price_per_ml": 75, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "dior_sauvage_elixir": {
        "brand_id": "dior", "brand": "Dior", "name": "Sauvage Elixir",
        "description": "Надпотужна нічна концентрація: пряна кориця, мускатний горіх, кардамон, лаванда та лакриця.",
        "top_notes": "Мускатний горіх, Кориця, Кардамон, Грейпфрут", "heart_notes": "Лаванда", "base_notes": "Лакриця, Сандал, Амбра, Пачулі, Ветивер",
        "price_full_bottle": 7400, "price_per_ml": 110, "gender": "m", "occasion": "e", "vibe": "t"
    },
    "dior_gris_dior": {
        "brand_id": "dior", "brand": "Dior", "name": "Gris Dior",
        "description": "Ексклюзивна лінійка Maison Christian Dior: елегантна троянда, дубовий мох, пачулі, бергамот і кедр.",
        "top_notes": "Бергамот, Грейпфрут", "heart_notes": "Троянда, Жасмин, Полуниця", "base_notes": "Пачулі, Дубовий мох, Сандал, Бурштин, Кедр",
        "price_full_bottle": 11500, "price_per_ml": 140, "gender": "u", "occasion": "d", "vibe": "floral"
    },
    "dior_fahrenheit": {
        "brand_id": "dior", "brand": "Dior", "name": "Fahrenheit",
        "description": "Легендарна шкіряно-фіалкова класика: лист фіалки, мускатний горіх, кедр, глід та шкіряний бензин.",
        "top_notes": "Мускатний горіх, Лаванда, Кедр, Ромашка, Бергамот", "heart_notes": "Листя фіалки, Мускатний горіх, Кедр, Сандал", "base_notes": "Шкіра, Ветивер, Мускус, Бурштин, Пачулі",
        "price_full_bottle": 5300, "price_per_ml": 75, "gender": "m", "occasion": "d", "vibe": "w"
    },
    "dior_miss_dior": {
        "brand_id": "dior", "brand": "Dior", "name": "Miss Dior",
        "description": "Романтичний букет кохання: грасська троянда, конвалія, ірис, півонія та ніжний рожевий перець.",
        "top_notes": "Ірис, Півонія, Конвалія", "heart_notes": "Троянда, Персик, Абрикос", "base_notes": "Ваніль, Мускус, Боби тонка, Бензоїн, Сандал",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "dior_homme_intense": {
        "brand_id": "dior", "brand": "Dior", "name": "Homme Intense",
        "description": "Оксамитовий вечірній пудровий ірис, лаванда, тепла амбрета, вірджинський кедр та груша.",
        "top_notes": "Лаванда", "heart_notes": "Ірис, Амбрета, Груша", "base_notes": "Вірджинський кедр, Ветивер",
        "price_full_bottle": 5600, "price_per_ml": 80, "gender": "m", "occasion": "e", "vibe": "w"
    },

    # ---------------- 10. CHANEL ----------------
    "chanel_bleu_de_chanel": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Bleu de Chanel",
        "description": "Еталон чоловічої свободи: грейпфрут, м'ята, рожевий перець, ладан, ветивер та білий кедр.",
        "top_notes": "Грейпфрут, Лимон, М'ята, Рожевий перець", "heart_notes": "Імбир, Мускатний горіх, Жасмин, Ізо Е Супер", "base_notes": "Ладан, Ветивер, Кедр, Сандал, Пачулі",
        "price_full_bottle": 6400, "price_per_ml": 90, "gender": "m", "occasion": "d", "vibe": "w"
    },
    "chanel_coco_mademoiselle": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Coco Mademoiselle",
        "description": "Свіжий та чуттєвий східний шипр: іскристий апельсин, турецька троянда, жасмин і чисті пачулі.",
        "top_notes": "Апельсин, Мандарин, Бергамот, Апельсиновий цвіт", "heart_notes": "Турецька троянда, Жасмин, Мімоза, Іланг-іланг", "base_notes": "Пачулі, Білий мускус, Ваніль, Ветивер, Боби тонка",
        "price_full_bottle": 6600, "price_per_ml": 95, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "chanel_chance_eau_tendre": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Chance Eau Tendre",
        "description": "Ніжний та оптимістичний фруктово-квітковий акорд: айва, грейпфрут, гіацинт, жасмин та ірис.",
        "top_notes": "Айва, Грейпфрут", "heart_notes": "Гіацинт, Жасмин", "base_notes": "Мускус, Ірис, Вірджинський кедр, Бурштин",
        "price_full_bottle": 6500, "price_per_ml": 95, "gender": "w", "occasion": "s", "vibe": "floral"
    },
    "chanel_allure_homme_sport": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Allure Homme Sport",
        "description": "Свіжа енергія руху: морські ноти, апельсин, червоний мандарин, атласький кедр і білий мускус.",
        "top_notes": "Апельсин, Морські ноти, Альдегіди, Червоний мандарин", "heart_notes": "Перець, Неролі, Кедр", "base_notes": "Боби тонка, Ваніль, Білий мускус, Бурштин, Ветивер",
        "price_full_bottle": 6200, "price_per_ml": 90, "gender": "m", "occasion": "d", "vibe": "f"
    },
    "chanel_sycomore": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Sycomore (Les Exclusifs)",
        "description": "Один із найкращих ветиверів у світі: димний благородний ветивер, кипарис, ялівець, сандал і тютюн.",
        "top_notes": "Рожевий перець, Альдегіди", "heart_notes": "Ветивер, Ялівець, Кипарис", "base_notes": "Тютюн, Сандал, Фіалка",
        "price_full_bottle": 14900, "price_per_ml": 180, "gender": "u", "occasion": "e", "vibe": "w"
    },
    "chanel_coromandel": {
        "brand_id": "chanel", "brand": "Chanel", "name": "Coromandel (Les Exclusifs)",
        "description": "Барокова розкіш китайського лаку: білий шоколад, пачулі, бензоїн, ладан, ірис і цитруси.",
        "top_notes": "Гіркий апельсин, Неролі, Цитруси", "heart_notes": "Пачулі, Корінь ірису, Троянда, Жасмин", "base_notes": "Білий шоколад, Бензоїн, Ладан, Ваніль, Деревні ноти",
        "price_full_bottle": 14900, "price_per_ml": 180, "gender": "u", "occasion": "e", "vibe": "s"
    },

    # ---------------- 11. TIZIANA TERENZI ----------------
    "terenzi_kirke": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Kirke",
        "description": "Екзотичний фруктовий нектар богині Цірцеї: маракуя, персик, малина, смородина та фірмовий мускус.",
        "top_notes": "Маракуя, Персик, Малина, Листя чорної смородини, Груша", "heart_notes": "Конвалія", "base_notes": "Геліотроп, Сандал, Ваніль, Пачулі, Мускус",
        "price_full_bottle": 6900, "price_per_ml": 95, "gender": "u", "occasion": "s", "vibe": "floral"
    },
    "terenzi_andromeda": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Andromeda",
        "description": "Зоряне сузір'я трав і квітів: іланг-іланг, водяний жасмин, бергамот, солодка груша, білий геліотроп.",
        "top_notes": "Бергамот, Трава, Іланг-іланг, Водяний жасмин", "heart_notes": "Лілія, Листя фіалки, Дамаська троянда, Груша", "base_notes": "Амбра, Ваніль, Кашемірове дерево, Ебенове дерево",
        "price_full_bottle": 6900, "price_per_ml": 95, "gender": "u", "occasion": "d", "vibe": "floral"
    },
    "terenzi_cassiopea": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Cassiopea",
        "description": "Літня ніч під зоряним небом: маракуя, чорна смородина, лимон, чайна троянда, гвоздика та боби тонка.",
        "top_notes": "Маракуя, Чорна смородина, Лимон, Папороть", "heart_notes": "Гвоздика, Конвалія, Чайна троянда", "base_notes": "Сандал, Боби тонка, Мускус",
        "price_full_bottle": 6900, "price_per_ml": 95, "gender": "u", "occasion": "s", "vibe": "floral"
    },
    "terenzi_draco": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Draco",
        "description": "М'який та шляхетний східний акорд: персик, лимон, бергамот, зелений кедр, пачулі, ваніль та груша.",
        "top_notes": "Бергамот, Лимон, Апельсин, Зелені ноти", "heart_notes": "Персик, Жасмин, Кедр, Пачулі, Магнолія", "base_notes": "Ваніль, Боби тонка, Мускус, Груша, Геліотроп",
        "price_full_bottle": 6900, "price_per_ml": 95, "gender": "u", "occasion": "d", "vibe": "s"
    },
    "terenzi_spirito_fiorentino": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Spirito Fiorentino",
        "description": "Червоний флорентійський місяць: шкіра, шафран, жасмин, сіра амбра, дубовий мох та береза.",
        "top_notes": "Шафран, Апельсин, Жасмин, Лілія", "heart_notes": "Сіра амбра, Іланг-іланг, Магнолія, Конвалія", "base_notes": "Шкіра, Береза, Дубовий мох, Сандал, Мускус",
        "price_full_bottle": 7400, "price_per_ml": 105, "gender": "u", "occasion": "e", "vibe": "w"
    },
    "terenzi_ursa": {
        "brand_id": "tiziana_terenzi", "brand": "Tiziana Terenzi", "name": "Ursa",
        "description": "Глибокий аромат північного озера: сухофрукти, пачулі, ром, мускатний горіх, ладан, тютюн і шкіра.",
        "top_notes": "Сухофрукти, Мускатний горіх, Елемі, Ром", "heart_notes": "Пачулі, Олібанум, Ладан, Тютюн, Ветивер", "base_notes": "Шкіра, Уд, Ваніль",
        "price_full_bottle": 7400, "price_per_ml": 105, "gender": "u", "occasion": "e", "vibe": "t"
    },

    # ---------------- 12. MONTALE ----------------
    "montale_intense_cafe": {
        "brand_id": "montale", "brand": "Montale", "name": "Intense Cafe",
        "description": "Затишна кав'ярня в центрі Парижа: свіжозварена арабіка, чайна троянда, тепла амбра та солодка ваніль.",
        "top_notes": "Квіткові ноти", "heart_notes": "Кава, Троянда", "base_notes": "Амбра, Білий мускус, Ваніль",
        "price_full_bottle": 4600, "price_per_ml": 65, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "montale_chocolate_greedy": {
        "brand_id": "montale", "brand": "Montale", "name": "Chocolate Greedy",
        "description": "Мрія ласуна: гарячий шоколад, свіже хрустке печиво, какао, сушена цедра гіркого апельсина та ваніль.",
        "top_notes": "Какао, Боби тонка, Ваніль", "heart_notes": "Гіркий апельсин", "base_notes": "Кава, Сухофрукти",
        "price_full_bottle": 4600, "price_per_ml": 65, "gender": "u", "occasion": "c", "vibe": "s"
    },
    "montale_roses_musk": {
        "brand_id": "montale", "brand": "Montale", "name": "Roses Musk",
        "description": "Найвідоміший бестселер бренду: свіжа ранкова троянда, оксамитовий білий мускус, жасмин та амбра.",
        "top_notes": "Троянда", "heart_notes": "Жасмин", "base_notes": "Мускус, Амбра",
        "price_full_bottle": 4600, "price_per_ml": 65, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "montale_arabians_tonka": {
        "brand_id": "montale", "brand": "Montale", "name": "Arabians Tonka",
        "description": "Дикий та пристрасний східний скакун: боби тонка, шафран, уд, бергамот, троянда, цукрова тростина.",
        "top_notes": "Шафран, Бергамот", "heart_notes": "Удове дерево, Болгарська троянда", "base_notes": "Цукрова тростина, Боби тонка, Бурштин, Білий мускус",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "montale_starry_nights": {
        "brand_id": "montale", "brand": "Montale", "name": "Starry Nights",
        "description": "Зоряне небо східної пустелі: калабрійський бергамот, яблуко, троянда, жасмин, пачулі та пудровий мускус.",
        "top_notes": "Яблуко, Бергамот, Лимон", "heart_notes": "Троянда, Пачулі, Жасмин", "base_notes": "Білий мускус, Бурштин, Пудрові ноти",
        "price_full_bottle": 4600, "price_per_ml": 65, "gender": "u", "occasion": "e", "vibe": "floral"
    },
    "montale_vanilla_cake": {
        "brand_id": "montale", "brand": "Montale", "name": "Vanilla Cake",
        "description": "Апетитний вершковий десерт: мадагаскарська ваніль, тепле молоко, смажений мигдаль, карамель та безе.",
        "top_notes": "Молоко, Мигдаль", "heart_notes": "Карамель, Безе", "base_notes": "Мадагаскарська ваніль",
        "price_full_bottle": 4600, "price_per_ml": 65, "gender": "w", "occasion": "c", "vibe": "s"
    },

    # ---------------- 13. MANCERA ----------------
    "mancera_red_tobacco": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Red Tobacco",
        "description": "Неймовірно стійкий, гарячий тютюново-пряний еліксир із нотами шафрану, кориці та пахучого уду.",
        "top_notes": "Шафран, Кориця, Ладан, Мускатний горіх, Білий персик", "heart_notes": "Пачулі, Жасмин", "base_notes": "Тютюн, Амбра, Деревні ноти, Ветивер, Стручки ванілі",
        "price_full_bottle": 5300, "price_per_ml": 75, "gender": "u", "occasion": "e", "vibe": "t"
    },
    "mancera_cedrat_boise": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Cedrat Boise",
        "description": "Свіжий цитрусово-деревний хіт: сицилійський лимон, чорна смородина, прянощі, шкіра, білий кедр і сандал.",
        "top_notes": "Сицилійський лимон, Чорна смородина, Бергамот, Прянощі", "heart_notes": "Фруктові ноти, Листя пачулі, Водяний жасмин", "base_notes": "Кедр, Шкіра, Сандал, Ваніль, Білий мускус",
        "price_full_bottle": 5100, "price_per_ml": 70, "gender": "u", "occasion": "d", "vibe": "w"
    },
    "mancera_instant_crush": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Instant Crush",
        "description": "Миттєве кохання: імбир, шафран, бергамот, марокканська троянда, жасмин, теплий бурштин і дубовий мох.",
        "top_notes": "Шафран, Імбир, Сицилійський бергамот, Мандарин", "heart_notes": "Марокканська троянда, Єгипетський жасмин, Бурштинове дерево", "base_notes": "Мадагаскарська ваніль, Сандал, Білий мускус, Мох",
        "price_full_bottle": 5200, "price_per_ml": 75, "gender": "u", "occasion": "e", "vibe": "s"
    },
    "mancera_roses_vanille": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Roses Vanille",
        "description": "Солодка чайна троянда в цукровій пудрі: свіжий калабрійський лимон, водна троянда, білий мускус і ваніль.",
        "top_notes": "Калабрійський лимон", "heart_notes": "Троянда, Цукор", "base_notes": "Ваніль, Білий мускус, Кедр",
        "price_full_bottle": 5100, "price_per_ml": 70, "gender": "w", "occasion": "e", "vibe": "s"
    },
    "mancera_amore_caffe": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Amore Caffe",
        "description": "Італійський десерт афогато: чорна кава, амаретто, морозиво, коричневий цукор, ваніль та сіра амбра.",
        "top_notes": "Кава, Лікер Амаретто", "heart_notes": "Морозиво, Ваніль", "base_notes": "Коричневий цукор, Ваніль, Сіра амбра",
        "price_full_bottle": 5400, "price_per_ml": 75, "gender": "u", "occasion": "c", "vibe": "s"
    },
    "mancera_holidays": {
        "brand_id": "mancera", "brand": "Mancera", "name": "Holidays",
        "description": "Атмосфера тропічної відпустки: солодкий кокос, бергамот, квітка тіаре, іланг-іланг, морські ноти та ваніль.",
        "top_notes": "Кокос, Бергамот", "heart_notes": "Квітка тіаре, Іланг-іланг, Морські ноти", "base_notes": "Стручки ванілі, Сандал, Білий мускус",
        "price_full_bottle": 5100, "price_per_ml": 70, "gender": "w", "occasion": "s", "vibe": "floral"
    },

    # ---------------- 14. EX NIHILO ----------------
    "ex_nihilo_fleur_narcotique": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "Fleur Narcotique",
        "description": "Наркотично привабливий квітковий шлейф: соковитий лічі, бергамот, стиглий персик, півонія та жасмин.",
        "top_notes": "Бергамот, Лічі, Персик", "heart_notes": "Жасмин, Півонія, Апельсиновий цвіт", "base_notes": "Деревні ноти, Мох, Мускус",
        "price_full_bottle": 12800, "price_per_ml": 150, "gender": "u", "occasion": "d", "vibe": "floral"
    },
    "ex_nihilo_lust_in_paradise": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "Lust in Paradise",
        "description": "Французька Рив'єра: біла півонія, рожевий перець, лічі, кедр, мускус і теплий сонячний бурштин.",
        "top_notes": "Рожевий перець", "heart_notes": "Біла півонія, Лічі", "base_notes": "Екстракт білого кедра, Мускус, Бурштин",
        "price_full_bottle": 12500, "price_per_ml": 150, "gender": "w", "occasion": "s", "vibe": "floral"
    },
    "ex_nihilo_blue_talisman": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "Blue Talisman",
        "description": "Ювілейний талісман удачі: соковита груша, бергамот, мандарин, апельсиновий цвіт, амброфікс і мускус.",
        "top_notes": "Бергамот, Імбир, Мандарин, Груша", "heart_notes": "Апельсиновий цвіт, Джордживуд", "base_notes": "Акігалавуд, Амброфікс, Мускус",
        "price_full_bottle": 13500, "price_per_ml": 160, "gender": "u", "occasion": "d", "vibe": "f"
    },
    "ex_nihilo_the_hedonist": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "The Hedonist",
        "description": "Філософія чистого задоволення: бергамот, імбир, кедр, акігалавуд, ветивер і боби тонка.",
        "top_notes": "Бергамот, Імбир", "heart_notes": "Кедр, Акігалавуд", "base_notes": "Ветивер, Мускус, Боби тонка",
        "price_full_bottle": 12500, "price_per_ml": 150, "gender": "u", "occasion": "d", "vibe": "w"
    },
    "ex_nihilo_devil_tender": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "Devil Tender",
        "description": "Диявольська ніжність: рожевий грейпфрут, рожевий перець, персик, болгарська троянда, півонія та замша.",
        "top_notes": "Рожевий грейпфрут, Рожевий перець, Персик", "heart_notes": "Троянда, Півонія", "base_notes": "Замша, Білий кедр, Сандал",
        "price_full_bottle": 12500, "price_per_ml": 150, "gender": "w", "occasion": "d", "vibe": "floral"
    },
    "ex_nihilo_atlas_fever": {
        "brand_id": "ex_nihilo", "brand": "Ex Nihilo", "name": "Atlas Fever",
        "description": "Пряна східна подорож: червоні ягоди, ладан, сандал, боби тонка, ваніль та благородний дуб.",
        "top_notes": "Червоні ягоди, Ладан", "heart_notes": "Нарцис", "base_notes": "Сандал, Боби тонка, Ваніль, Дуб, Кедр",
        "price_full_bottle": 13200, "price_per_ml": 155, "gender": "u", "occasion": "e", "vibe": "t"
    },

    # ---------------- 15. ZARKOPERFUME ----------------
    "zarko_pink_molecule": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "Pink Molécule 090.09",
        "description": "Скандинавська естетика: рожеве ігристе шампанське, чорна бузина, стиглий абрикос та вершкова молекула.",
        "top_notes": "Бузина, Абрикос, Чорна орхідея, Шампанське", "heart_notes": "Молекулярний акорд (без середніх нот)", "base_notes": "Махагоні, Вершки, Чорне дерево",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "w", "occasion": "s", "vibe": "floral"
    },
    "zarko_molecule_234_38": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "Molecule 234.38",
        "description": "Персональна аура, що адаптується до вашої шкіри: чиста молекулярна магія тепла та деревної свіжості.",
        "top_notes": "Молекулярний ізомер 234.38", "heart_notes": "Аура шкіри", "base_notes": "Деревні молекули",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "u", "occasion": "d", "vibe": "w"
    },
    "zarko_the_muse": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "The Muse",
        "description": "Ідеальна білосніжна чистота: аромат білого свіжого бавовняного полотна, пудрового мускусу та квітки уду.",
        "top_notes": "Білий бавовник", "heart_notes": "Білий мускус", "base_notes": "Квітка уду",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "w", "occasion": "d", "vibe": "f"
    },
    "zarko_purple_molecule": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "Purple Molecule 070.07",
        "description": "Соковита пітайя (драконячий фрукт), мадагаскарська ваніль, біла амбра та вершковий мускус.",
        "top_notes": "Пітайя (драконячий фрукт)", "heart_notes": "Амбра", "base_notes": "Ваніль, Сандал",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "w", "occasion": "s", "vibe": "floral"
    },
    "zarko_quantum_molecule": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "Quantum Molecule",
        "description": "Квантовий вибух свіжості: бергамот, мандарин, пачулі, біле дерево та світла амбра.",
        "top_notes": "Бергамот, Мандарин, Чорна смородина", "heart_notes": "Жасмин, Пачулі", "base_notes": "Біле дерево, Ваніль, Шоколад",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "u", "occasion": "d", "vibe": "f"
    },
    "zarko_inception": {
        "brand_id": "zarkoperfume", "brand": "Zarkoperfume", "name": "Inception",
        "description": "Аромат, натхненний фільмом Нолана «Початок»: шість паралельних шарів свіжих цитрусів, спецій та океану.",
        "top_notes": "Цитруси, Морські ноти", "heart_notes": "Квіткові ноти, Спеції", "base_notes": "Деревні ноти, Зелені ноти",
        "price_full_bottle": 4900, "price_per_ml": 70, "gender": "m", "occasion": "d", "vibe": "f"
    },
}


# ==============================================================================
# 5. ГЕНЕРАЦІЯ КЛАВІАТУР
# ==============================================================================

def get_start_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Головне меню магазину."""
    builder = InlineKeyboardBuilder()
    cart_count = len(USER_CARTS.get(user_id, []))
    cart_title = f"🛒 Кошик ({cart_count})" if cart_count > 0 else "🛒 Кошик"

    if WEBAPP_URL:
        builder.button(text="👑 Відкрити Web-бутік (Mini App)", web_app=WebAppInfo(url=WEBAPP_URL))

    builder.button(text="💧 На розпив", callback_data=MainMenuCallback(target="decant_select").pack())
    builder.button(text="📦 Цілі парфуми", callback_data=MainMenuCallback(target="brands_select").pack())
    builder.button(text="🧠 Парфумерний сомельє", callback_data=SommelierCallback(step="start").pack())
    builder.button(text="🎁 Aroma Box (-15%)", callback_data=AromaBoxCallback(action="menu").pack())
    builder.button(text="🔎 Пошук за нотами", callback_data=MainMenuCallback(target="notes_search").pack())
    builder.button(text=cart_title, callback_data=CartActionCallback(action="view").pack())

    if WEBAPP_URL:
        builder.adjust(1, 2, 2, 2)
    else:
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
    for b_id, b_name in BRANDS_REGISTRY.items():
        builder.button(
            text=b_name,
            callback_data=BrandSelectCallback(brand_id=b_id, mode=mode, volume=volume).pack()
        )

    back_cb = (
        MainMenuCallback(target="decant_select").pack()
        if mode == "decant"
        else MainMenuCallback(target="root").pack()
    )
    builder.button(text="🔙 Назад", callback_data=back_cb)
    builder.adjust(2)
    return builder.as_markup()


def get_brand_perfumes_keyboard(brand_id: str, mode: str = "full", volume: int = 0) -> InlineKeyboardMarkup:
    """Список парфумів обраного бренду (мінімум 5-6 ароматів, без цін на кнопках)."""
    builder = InlineKeyboardBuilder()
    filtered = [(pid, item) for pid, item in PERFUMES_DB.items() if item["brand_id"] == brand_id]

    for pid, item in filtered:
        builder.button(
            text=f"✨ {item['name']}",
            callback_data=PerfumeViewCallback(perfume_id=pid, mode=mode, volume=volume).pack()
        )

    back_cb = (
        DecantVolumeCallback(volume=volume).pack()
        if mode == "decant"
        else MainMenuCallback(target="brands_select").pack()
    )
    builder.button(text="🔙 Назад до брендів", callback_data=back_cb)
    builder.adjust(1)
    return builder.as_markup()


def get_perfume_card_keyboard(perfume_id: str, mode: str, volume: int) -> InlineKeyboardMarkup:
    """Кнопки картки товару."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🛍 Додати в кошик",
        callback_data=CartActionCallback(action="add", perfume_id=perfume_id, mode=mode, volume=volume).pack()
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
    """Керування кошиком."""
    builder = InlineKeyboardBuilder()
    if cart_items:
        builder.button(text="🚚 Оформити замовлення", callback_data=CartActionCallback(action="checkout").pack())
        for idx, _ in enumerate(cart_items):
            builder.button(
                text=f"❌ Видалити №{idx + 1}",
                callback_data=CartActionCallback(action="remove", item_index=idx).pack()
            )
        builder.button(text="🗑 Очистити кошик", callback_data=CartActionCallback(action="clear").pack())

    builder.button(text="🔙 Продовжити покупки", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)
    return builder.as_markup()


def get_notes_categories_keyboard() -> InlineKeyboardMarkup:
    """Категорії нот."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌿 Свіжі, Цитрусові та Морські", callback_data=NotesFilterCallback(category="f").pack())
    builder.button(text="🍂 Тютюнові, Пряні та Східні", callback_data=NotesFilterCallback(category="t").pack())
    builder.button(text="🍨 Солодкі, Ванільні та Гурманські", callback_data=NotesFilterCallback(category="s").pack())
    builder.button(text="🪵 Деревні, Шкіряні та Сандал", callback_data=NotesFilterCallback(category="w").pack())
    builder.button(text="🌸 Квіткові та Стиглі Фрукти", callback_data=NotesFilterCallback(category="floral").pack())
    builder.button(text="🔙 Назад у меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)
    return builder.as_markup()


# ==============================================================================
# 6. ХЕЛПЕРИ ВІДОБРАЖЕННЯ
# ==============================================================================

async def render_text_screen(call: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    """Безпечне перемикання між екранами з обробкою подвійних кліків та помилок Telegram API."""
    try:
        if call.message.photo:
            try:
                await call.message.delete()
            except TelegramBadRequest:
                pass
            await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            try:
                await call.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except TelegramBadRequest as e:
                err_msg = str(e).lower()
                if "message is not modified" in err_msg:
                    pass
                elif "message to edit not found" in err_msg or "message can't be edited" in err_msg:
                    await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                else:
                    logger.warning(f"TelegramBadRequest in edit_text: {e}")
                    await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning(f"Error in render_text_screen: {e}")
        try:
            await call.message.answer(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception:
            pass


def format_perfume_caption(item: Dict[str, Any], mode: str, volume: int) -> str:
    """Картка товару: естетика, піраміда нот і ціна в самому кінці."""
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
    if not cart_items:
        return "🛒 <b>Ваш кошик порожній.</b>\n\nОберіть аромати в каталозі або створіть власний Aroma Box!"

    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0
    for i, it in enumerate(cart_items, start=1):
        lines.append(
            f"<b>{i}. {it['brand']} — {it['name']}</b>\n"
            f"   • Формат: {it['type_label']}\n"
            f"   • Вартість: <b>{it['price']} грн</b>\n"
        )
        total += it['price']

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"💳 <b>Разом до сплати:</b> <b>{total} грн</b>")
    return "\n".join(lines)


# ==============================================================================
# 7. ДИСПЕТЧЕР ТА ХЕНДЛЕРИ КАТАЛОГУ
# ==============================================================================

dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    REGISTERED_USERS.add(message.from_user.id)

    welcome_text = (
        f"👋 <b>Вітаємо у бутіку селективної парфумерії, {message.from_user.first_name}!</b>\n\n"
        "У нас ви знайдете понад 90 оригінальних нішевих шедеврів від 15 культових брендів.\n\n"
        "✨ Скористайтеся <b>«Парфумерним сомельє»</b> для безпомилкового підбору, "
        "або збережіть 15% у конструкторі <b>«Aroma Box»</b>!"
    )
    await message.answer(welcome_text, reply_markup=get_start_keyboard(message.from_user.id), parse_mode=ParseMode.HTML)


@dp.callback_query(MainMenuCallback.filter())
async def handle_main_navigation(call: CallbackQuery, callback_data: MainMenuCallback) -> None:
    await call.answer()
    t = callback_data.target

    if t == "root":
        text = "Головне меню магазину парфумерії:\nОберіть бажаний розділ:"
        await render_text_screen(call, text, get_start_keyboard(call.from_user.id))

    elif t == "decant_select":
        text = (
            "💧 <b>Оберіть бажаний об'єм для розпиву:</b>\n\n"
            "<i>Усі відливанти фасуються у скляні флакони зі спреєм безпосередньо перед відправкою.</i>"
        )
        await render_text_screen(call, text, get_decant_volumes_keyboard())

    elif t == "brands_select":
        text = "📦 <b>Оберіть бренд парфуму:</b>\n\n<i>Повні оригінальні флакони у фірмовому пакуванні.</i>"
        await render_text_screen(call, text, get_brands_keyboard(mode="full", volume=0))

    elif t == "notes_search":
        text = "🔎 <b>Пошук ароматів за нотами та настроєм:</b>\nОберіть напрямок, який вам до смаку:"
        await render_text_screen(call, text, get_notes_categories_keyboard())


@dp.callback_query(DecantVolumeCallback.filter())
async def handle_decant_volume(call: CallbackQuery, callback_data: DecantVolumeCallback) -> None:
    await call.answer()
    vol = callback_data.volume
    text = (
        f"💧 <b>Розпив ({vol} мл) — Оберіть бренд:</b>\n\n"
        f"<i>Оберіть дім парфумерії для знайомства з композиціями:</i>"
    )
    await render_text_screen(call, text, get_brands_keyboard(mode="decant", volume=vol))


@dp.callback_query(BrandSelectCallback.filter())
async def handle_brand_select(call: CallbackQuery, callback_data: BrandSelectCallback) -> None:
    await call.answer()
    b_id = callback_data.brand_id
    b_name = BRANDS_REGISTRY.get(b_id, "Бренд")
    mode = callback_data.mode
    vol = callback_data.volume

    prefix = f"💧 Розпив ({vol} мл) — " if mode == "decant" else "📦 "
    text = f"{prefix}<b>Аромати дому {b_name}:</b>\n\n<i>Оберіть композицію для перегляду нот та піраміди:</i>"
    await render_text_screen(call, text, get_brand_perfumes_keyboard(b_id, mode=mode, volume=vol))


@dp.callback_query(PerfumeViewCallback.filter())
async def handle_perfume_card(call: CallbackQuery, callback_data: PerfumeViewCallback) -> None:
    try:
        await call.answer()
    except TelegramBadRequest:
        pass

    item = PERFUMES_DB.get(callback_data.perfume_id)
    if not item:
        try:
            await call.answer("❌ Товар не знайдено", show_alert=True)
        except TelegramBadRequest:
            pass
        return

    caption = format_perfume_caption(item, callback_data.mode, callback_data.volume)
    keyboard = get_perfume_card_keyboard(callback_data.perfume_id, callback_data.mode, callback_data.volume)

    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass

    try:
        await call.message.answer_photo(
            photo=item.get("image_url", DEFAULT_PERFUME_IMG),
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Помилка надсилання фото картки: {e}, надсилаємо текстом")
        try:
            await call.message.answer(
                text=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as ex:
            logger.error(f"Критична помилка показу картки: {ex}")


# ==============================================================================
# 8. ПАРФУМЕРНИЙ СОМЕЛЬЄ (Чіткий 3-кроковий алгоритм)
# ==============================================================================

@dp.callback_query(SommelierCallback.filter(F.step == "start"))
async def sommelier_start(call: CallbackQuery) -> None:
    await call.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Чоловічий", callback_data=SommelierCallback(step="g", g="m").pack())
    builder.button(text="👩 Жіночий", callback_data=SommelierCallback(step="g", g="w").pack())
    builder.button(text="✨ Унісекс", callback_data=SommelierCallback(step="g", g="u").pack())
    builder.button(text="🔙 Назад у меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(2, 1, 1)

    text = (
        "🧠 <b>Парфумерний сомельє</b> [Крок 1/3]\n\n"
        "Дайте відповідь на 3 простих питання, і штучний інтелект-сомельє "
        "підбере найкращі композиції спеціально під ваші вподобання.\n\n"
        "👉 <b>Для кого підбираємо парфум?</b>"
    )
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(SommelierCallback.filter(F.step == "g"))
async def sommelier_step_occasion(call: CallbackQuery, callback_data: SommelierCallback) -> None:
    await call.answer()
    g = callback_data.g

    builder = InlineKeyboardBuilder()
    builder.button(text="☀️ На щодень & В офіс", callback_data=SommelierCallback(step="o", g=g, o="d").pack())
    builder.button(text="🌙 Вечірній & Побачення", callback_data=SommelierCallback(step="o", g=g, o="e").pack())
    builder.button(text="❄️ Осінь & Зима (Затишний)", callback_data=SommelierCallback(step="o", g=g, o="c").pack())
    builder.button(text="🌊 Весна & Літо (Свіжий)", callback_data=SommelierCallback(step="o", g=g, o="s").pack())
    builder.button(text="🔙 Назад", callback_data=SommelierCallback(step="start").pack())
    builder.adjust(1)

    text = (
        "🧠 <b>Парфумерний сомельє</b> [Крок 2/3]\n\n"
        "👉 <b>Для якої події та сезону шукаєте аромат?</b>"
    )
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(SommelierCallback.filter(F.step == "o"))
async def sommelier_step_vibe(call: CallbackQuery, callback_data: SommelierCallback) -> None:
    await call.answer()
    g, o = callback_data.g, callback_data.o

    builder = InlineKeyboardBuilder()
    builder.button(text="🌿 Свіжі цитруси & Океан", callback_data=SommelierCallback(step="v", g=g, o=o, v="f").pack())
    builder.button(text="🍨 Солодкі десерти & Ваніль", callback_data=SommelierCallback(step="v", g=g, o=o, v="s").pack())
    builder.button(text="🍂 Тютюн, Ром & Прянощі", callback_data=SommelierCallback(step="v", g=g, o=o, v="t").pack())
    builder.button(text="🪵 Шляхетний сандал, Уд & Шкіра", callback_data=SommelierCallback(step="v", g=g, o=o, v="w").pack())
    builder.button(text="🌸 Розкішні квіти & Стиглі фрукти", callback_data=SommelierCallback(step="v", g=g, o=o, v="floral").pack())
    builder.button(text="🔙 Назад", callback_data=SommelierCallback(step="g", g=g).pack())
    builder.adjust(1)

    text = (
        "🧠 <b>Парфумерний сомельє</b> [Крок 3/3]\n\n"
        "👉 <b>Які ноти та характер звучання вам найбільше подобаються?</b>"
    )
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(SommelierCallback.filter(F.step == "v"))
async def sommelier_result(call: CallbackQuery, callback_data: SommelierCallback) -> None:
    await call.answer()
    g, o, v = callback_data.g, callback_data.o, callback_data.v

    # Інтелектуальний підрахунок рейтингу з 90 парфумів
    scored_perfumes = []
    for pid, it in PERFUMES_DB.items():
        score = 0
        if it.get("vibe") == v:
            score += 4
        if it.get("gender") == g or it.get("gender") == "u":
            score += 3
        if it.get("occasion") == o:
            score += 2
        scored_perfumes.append((score, pid, it))

    scored_perfumes.sort(key=lambda x: x[0], reverse=True)
    top_picks = scored_perfumes[:4]

    builder = InlineKeyboardBuilder()
    for _, pid, it in top_picks:
        builder.button(
            text=f"✨ {it['brand']} — {it['name']}",
            callback_data=PerfumeViewCallback(perfume_id=pid, mode="full", volume=0).pack()
        )

    builder.button(text="🔄 Пройти тест знову", callback_data=SommelierCallback(step="start").pack())
    builder.button(text="🏠 Головне меню", callback_data=MainMenuCallback(target="root").pack())
    builder.adjust(1)

    text = (
        "🎯 <b>Персональний вердикт сомельє:</b>\n\n"
        "Ми проаналізували вашу піраміду вподобань і відібрали ці найкращі композиції:\n"
    )
    for idx, (_, _, it) in enumerate(top_picks, start=1):
        text += f"\n<b>{idx}. {it['brand']} — {it['name']}</b>\n<i>«{it['description']}»</i>\n"

    await render_text_screen(call, text, builder.as_markup())


# ==============================================================================
# 9. КОНСТРУКТОР «AROMA BOX» (З панеллю брендів, без довгого списку)
# ==============================================================================

@dp.callback_query(AromaBoxCallback.filter(F.action == "menu"))
async def aroma_box_main(call: CallbackQuery) -> None:
    """Головний екран конструктора Aroma Box: статус та панель брендів."""
    await call.answer()
    uid = call.from_user.id
    if uid not in USER_BOX_BUILDER:
        USER_BOX_BUILDER[uid] = []

    selected = USER_BOX_BUILDER[uid]
    count = len(selected)

    builder = InlineKeyboardBuilder()

    if count < 3:
        # Показуємо охайну панель із 15 брендів (по 2 в ряд)
        for b_id, b_name in BRANDS_REGISTRY.items():
            builder.button(
                text=b_name,
                callback_data=AromaBoxCallback(action="brand", brand_id=b_id).pack()
            )
        builder.button(text="🔙 Назад у меню", callback_data=MainMenuCallback(target="root").pack())
        builder.adjust(2)
    else:
        # Бокс укомплектовано!
        builder.button(
            text="🎁 Додати Aroma Box у кошик (-15%)",
            callback_data=AromaBoxCallback(action="finish").pack()
        )
        builder.button(text="🔄 Скласти заново", callback_data=AromaBoxCallback(action="reset").pack())
        builder.button(text="🔙 Головне меню", callback_data=MainMenuCallback(target="root").pack())
        builder.adjust(1)

    lines = ["🎁 <b>Конструктор Aroma Box (-15%)</b>\n"]
    lines.append("Складіть свій сет із <b>3 будь-яких ароматів по 5 мл</b> зі знижкою 15%!\n")
    lines.append(f"Статус наповнення: <b>{count}/3</b>")

    for i in range(3):
        if i < count:
            it = PERFUMES_DB[selected[i]]
            lines.append(f"  {i+1}. ✅ <b>{it['brand']} — {it['name']}</b> (5 мл)")
        else:
            lines.append(f"  {i+1}. ⏳ <i>[Оберіть бренд нижче для вибору аромату]</i>")

    lines.append("\n" + ("👇 <b>Оберіть бренд парфуму:</b>" if count < 3 else "🎉 <b>Сет готовий до замовлення!</b>"))
    await render_text_screen(call, "\n".join(lines), builder.as_markup())


@dp.callback_query(AromaBoxCallback.filter(F.action == "brand"))
async def aroma_box_select_brand(call: CallbackQuery, callback_data: AromaBoxCallback) -> None:
    """Вибір аромату конкретного бренду для боксу."""
    await call.answer()
    b_id = callback_data.brand_id
    b_name = BRANDS_REGISTRY.get(b_id, "Бренд")
    uid = call.from_user.id
    selected = USER_BOX_BUILDER.get(uid, [])

    builder = InlineKeyboardBuilder()
    filtered = [(pid, it) for pid, it in PERFUMES_DB.items() if it["brand_id"] == b_id]

    for pid, it in filtered:
        if pid not in selected:
            builder.button(
                text=f"➕ {it['name']}",
                callback_data=AromaBoxCallback(action="pick", perfume_id=pid).pack()
            )
        else:
            builder.button(text=f"✓ {it['name']} (вже у сеті)", callback_data="none")

    builder.button(text="🔙 Назад до брендів", callback_data=AromaBoxCallback(action="menu").pack())
    builder.adjust(1)

    text = (
        f"🎁 <b>Aroma Box — Аромати бренду {b_name}:</b>\n\n"
        f"Оберіть бажану композицію для додавання у ваш сет (обрано {len(selected)}/3):"
    )
    await render_text_screen(call, text, builder.as_markup())


@dp.callback_query(F.data == "none")
async def handle_none_callback(call: CallbackQuery) -> None:
    """Обробник кліку на кнопки-індикатори (наприклад, аромат уже додано до сету)."""
    try:
        await call.answer("ℹ️ Цей аромат уже додано до вашого набору!", show_alert=False)
    except TelegramBadRequest:
        pass


@dp.callback_query(AromaBoxCallback.filter(F.action == "pick"))
async def aroma_box_pick(call: CallbackQuery, callback_data: AromaBoxCallback) -> None:
    uid = call.from_user.id
    if uid not in USER_BOX_BUILDER:
        USER_BOX_BUILDER[uid] = []

    pid = callback_data.perfume_id
    if pid and pid not in USER_BOX_BUILDER[uid] and len(USER_BOX_BUILDER[uid]) < 3:
        USER_BOX_BUILDER[uid].append(pid)
        await call.answer(f"✅ {PERFUMES_DB[pid]['name']} додано до сету!")

    await aroma_box_main(call)


@dp.callback_query(AromaBoxCallback.filter(F.action == "reset"))
async def aroma_box_reset(call: CallbackQuery) -> None:
    uid = call.from_user.id
    USER_BOX_BUILDER[uid] = []
    await call.answer("Конструктор скинуто!")
    await aroma_box_main(call)


@dp.callback_query(AromaBoxCallback.filter(F.action == "finish"))
async def aroma_box_finish(call: CallbackQuery) -> None:
    uid = call.from_user.id
    selected = USER_BOX_BUILDER.get(uid, [])

    if len(selected) != 3:
        await call.answer("Оберіть рівно 3 аромати!", show_alert=True)
        return

    raw_sum = sum((PERFUMES_DB[pid]["price_per_ml"] * 5) + ATOMIZER_FEE for pid in selected)
    discounted_sum = int(raw_sum * 0.85)

    names = ", ".join([PERFUMES_DB[pid]["name"] for pid in selected])

    if uid not in USER_CARTS:
        USER_CARTS[uid] = []

    USER_CARTS[uid].append({
        "perfume_id": "aroma_box_bundle",
        "brand": "Ексклюзивний Aroma Box",
        "name": f"Сет із 3 ароматів ({names})",
        "price": discounted_sum,
        "type_label": "3 x 5 мл зі знижкою 15%",
    })

    USER_BOX_BUILDER[uid].clear()
    await call.answer("🎉 Aroma Box успішно додано у кошик!", show_alert=True)

    text = format_cart_message(USER_CARTS[uid])
    await render_text_screen(call, text, get_cart_keyboard(USER_CARTS[uid]))


# ==============================================================================
# 10. ФІЛЬТР ЗА НОТАМИ
# ==============================================================================

@dp.callback_query(NotesFilterCallback.filter())
async def filter_by_notes(call: CallbackQuery, callback_data: NotesFilterCallback) -> None:
    await call.answer()
    cat = callback_data.category

    filtered = [(pid, it) for pid, it in PERFUMES_DB.items() if it.get("vibe") == cat]

    builder = InlineKeyboardBuilder()
    for pid, it in filtered:
        builder.button(
            text=f"✨ {it['brand']} — {it['name']}",
            callback_data=PerfumeViewCallback(perfume_id=pid, mode="full", volume=0).pack()
        )
    builder.button(text="🔙 Назад до категорій", callback_data=MainMenuCallback(target="notes_search").pack())
    builder.adjust(1)

    names = {
        "f": "🌿 Свіжі, Цитрусові та Морські",
        "t": "🍂 Тютюнові, Пряні та Східні",
        "s": "🍨 Солодкі, Ванільні та Гурманські",
        "w": "🪵 Деревні, Шкіряні та Сандал",
        "floral": "🌸 Квіткові та Стиглі Фрукти",
    }
    title = names.get(cat, "Аромати")
    text = f"🔎 <b>{title}:</b>\n\nОберіть композицію для перегляду піраміди:"
    await render_text_screen(call, text, builder.as_markup())


# ==============================================================================
# 11. КОШИК ТА ЧЕК-АУТ З НОВОЮ ПОШТОЮ
# ==============================================================================

@dp.callback_query(CartActionCallback.filter())
async def handle_cart_actions(call: CallbackQuery, callback_data: CartActionCallback, state: FSMContext) -> None:
    uid = call.from_user.id
    if uid not in USER_CARTS:
        USER_CARTS[uid] = []

    act = callback_data.action

    if act == "add":
        it = PERFUMES_DB.get(callback_data.perfume_id)
        if not it:
            await call.answer("Помилка додавання", show_alert=True)
            return

        if callback_data.mode == "decant":
            price = (it["price_per_ml"] * callback_data.volume) + ATOMIZER_FEE
            t_label = f"Розпив {callback_data.volume} мл"
        else:
            price = it["price_full_bottle"]
            t_label = "Повний флакон"

        USER_CARTS[uid].append({
            "perfume_id": callback_data.perfume_id,
            "brand": it["brand"],
            "name": it["name"],
            "price": price,
            "type_label": t_label,
        })
        await call.answer(f"✅ {it['name']} додано до кошика!")

    elif act == "view":
        await call.answer()
        text = format_cart_message(USER_CARTS[uid])
        await render_text_screen(call, text, get_cart_keyboard(USER_CARTS[uid]))

    elif act == "remove":
        idx = callback_data.item_index
        if 0 <= idx < len(USER_CARTS[uid]):
            removed = USER_CARTS[uid].pop(idx)
            await call.answer(f"Видалено: {removed['name']}")
        text = format_cart_message(USER_CARTS[uid])
        await render_text_screen(call, text, get_cart_keyboard(USER_CARTS[uid]))

    elif act == "clear":
        USER_CARTS[uid].clear()
        await call.answer("Кошик очищено!")
        text = format_cart_message([])
        await render_text_screen(call, text, get_cart_keyboard([]))

    elif act == "checkout":
        if not USER_CARTS[uid]:
            await call.answer("Ваш кошик порожній!", show_alert=True)
            return

        await call.answer()
        await state.set_state(CheckoutStates.waiting_for_name)
        text = (
            "🚚 <b>Оформлення замовлення (Крок 1/3)</b>\n\n"
            "Введіть ваші <b>Прізвище та Ім'я</b> для накладної Нової Пошти:"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Скасувати", callback_data=CartActionCallback(action="view").pack())
        await render_text_screen(call, text, builder.as_markup())


@dp.message(CheckoutStates.waiting_for_name)
async def checkout_name_step(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Будь ласка, введіть коректні ПІБ:")
        return

    await state.update_data(customer_name=name)
    await state.set_state(CheckoutStates.waiting_for_phone)

    btn = KeyboardButton(text="📱 Поділитися номером телефону", request_contact=True)
    markup = ReplyKeyboardMarkup(keyboard=[[btn]], resize_keyboard=True, one_time_keyboard=True)

    await message.answer(
        "📞 <b>Крок 2/3: Номер телефону</b>\n\n"
        "Натисніть кнопку нижче або введіть номер вручну:",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )


@dp.message(CheckoutStates.waiting_for_phone)
async def checkout_phone_step(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number if message.contact else message.text.strip()
    await state.update_data(customer_phone=phone)
    await state.set_state(CheckoutStates.waiting_for_address)

    await message.answer(
        "📦 <b>Крок 3/3: Доставка Новою Поштою</b>\n\n"
        "Вкажіть ваше <b>Місто та номер відділення</b> (або поштомату):\n"
        "<i>Приклад: Львів, відділення №15</i>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )


@dp.message(CheckoutStates.waiting_for_address)
async def checkout_address_step(message: Message, state: FSMContext) -> None:
    addr = message.text.strip()
    await state.update_data(customer_address=addr)

    data = await state.get_data()
    uid = message.from_user.id
    items = USER_CARTS.get(uid, [])
    total = sum(i["price"] for i in items)

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплата на картку / Monobank", callback_data="pay_card")
    builder.button(text="💵 Накладений платіж (при отриманні)", callback_data="pay_cod")
    builder.adjust(1)

    summary = (
        "📋 <b>Перевірка замовлення:</b>\n\n"
        f"👤 Отримувач: <b>{data['customer_name']}</b>\n"
        f"📞 Телефон: <b>{data['customer_phone']}</b>\n"
        f"📦 Доставка: <b>{addr}</b>\n"
        f"💰 Разом: <b>{total} грн</b> ({len(items)} поз.)\n\n"
        "Оберіть спосіб оплати:"
    )
    await message.answer(summary, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.in_(["pay_card", "pay_cod"]))
async def finalize_order(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await call.answer()
    data = await state.get_data()
    uid = call.from_user.id
    items = USER_CARTS.get(uid, [])
    total = sum(i["price"] for i in items)

    order_id = f"#{len(ORDERS_DB) + 1042}"
    pay_type = "Оплата на картку (Monobank)" if call.data == "pay_card" else "Накладений платіж"

    record = {
        "order_id": order_id, "user_id": uid, "username": call.from_user.username or "Невідомо",
        "name": data.get("customer_name"), "phone": data.get("customer_phone"),
        "address": data.get("customer_address"), "items": items.copy(),
        "total": total, "payment": pay_type
    }
    ORDERS_DB.append(record)
    USER_CARTS[uid].clear()
    await state.clear()

    client_msg = (
        f"🎉 <b>Дякуємо! Ваше замовлення {order_id} успішно прийнято!</b>\n\n"
        f"📦 Доставка: <b>{record['address']}</b>\n"
        f"💳 Сума: <b>{total} грн</b> ({pay_type})\n\n"
        f"Менеджер уже готує ваше замовлення та незабаром надішле ТТН!"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 На головну", callback_data=MainMenuCallback(target="root").pack())
    await render_text_screen(call, client_msg, builder.as_markup())

    logger.info(f"Замовлення {order_id} оформлено на суму {total} грн.")

    if ADMIN_ID > 0:
        try:
            admin_text = (
                f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ {order_id}!</b>\n\n"
                f"👤 Клієнт: {record['name']} (@{record['username']})\n"
                f"📞 Телефон: {record['phone']}\n"
                f"📍 Адреса: {record['address']}\n"
                f"💰 Сума: <b>{total} грн</b> ({pay_type})\n\n"
                f"🛍 <b>Товари:</b>\n" +
                "\n".join([f"• {it['brand']} — {it['name']} ({it['type_label']}) — {it['price']} грн" for it in items])
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


@dp.message(F.web_app_data)
async def handle_web_app_order(message: Message, bot: Bot) -> None:
    """Обробка замовлення, оформленого через Telegram Mini App."""
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)

        order_id = data.get("order_id", f"#APP-{len(ORDERS_DB) + 1042}")
        name = data.get("customer_name", message.from_user.full_name)
        phone = data.get("customer_phone", "Не вказано")
        address = data.get("customer_address", "Не вказано")
        payment = data.get("payment_method", "Оплата карткою")
        total = data.get("total_amount", 0)
        items = data.get("items", [])

        record = {
            "order_id": order_id,
            "user_id": message.from_user.id,
            "username": message.from_user.username or "Невідомо",
            "name": name,
            "phone": phone,
            "address": address,
            "items": items,
            "total": total,
            "payment": payment
        }
        ORDERS_DB.append(record)
        REGISTERED_USERS.add(message.from_user.id)

        items_summary = "\n".join([
            f"• {it.get('brand', '')} {it.get('name', '')} ({it.get('typeLabel', '')}) — <b>{it.get('price', 0)} грн</b>"
            for it in items
        ])

        client_text = (
            f"👑 <b>Замовлення {order_id} успішно прийнято з Mini App!</b>\n\n"
            f"👤 Отримувач: <b>{name}</b>\n"
            f"📞 Телефон: <b>{phone}</b>\n"
            f"📦 Нова Пошта: <b>{address}</b>\n"
            f"💳 Спосіб оплати: <b>{payment}</b>\n\n"
            f"🛍 <b>Склад замовлення:</b>\n{items_summary}\n\n"
            f"💰 <b>Разом до сплати:</b> <b>{total} грн</b>\n\n"
            f"<i>Менеджер уже бере замовлення в роботу та готує флакони. Дякуємо за вибір L'ÉLIXIR ROYAL!</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Головне меню", callback_data=MainMenuCallback(target="root").pack())
        if WEBAPP_URL:
            builder.button(text="👑 Відкрити бутік знову", web_app=WebAppInfo(url=WEBAPP_URL))
        builder.adjust(1)

        await message.answer(client_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

        if ADMIN_ID > 0:
            try:
                admin_text = (
                    f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ З MINI APP {order_id}!</b>\n\n"
                    f"👤 Клієнт: {name} (@{message.from_user.username or 'без юзернейму'})\n"
                    f"📞 Телефон: {phone}\n"
                    f"📍 Адреса: {address}\n"
                    f"💰 Сума: <b>{total} грн</b> ({payment})\n\n"
                    f"🛍 <b>Товари:</b>\n{items_summary}"
                )
                await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Помилка сповіщення адміна: {e}")

    except Exception as e:
        logger.error(f"Помилка обробки web_app_data: {e}")
        await message.answer("🎉 Ваше замовлення отримано! Менеджер зв'яжеться з вами найближчим часом.")


# ==============================================================================
# 12. АДМІН-ПАНЕЛЬ ТА РОЗСИЛКА
# ==============================================================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    u_count = len(REGISTERED_USERS)
    o_count = len(ORDERS_DB)
    rev = sum(o["total"] for o in ORDERS_DB)

    text = (
        "👑 <b>Панель керування магазином:</b>\n\n"
        f"👥 Зареєстрованих покупців: <b>{u_count}</b>\n"
        f"📦 Всього оформлено замовлень: <b>{o_count}</b>\n"
        f"💰 Оборот: <b>{rev} грн</b>\n\n"
        "Команди:\n"
        "• /broadcast — Створити рекламну розсилку"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await message.answer("✍️ Введіть текст повідомлення для розсилки (або 'скасувати'):")


@dp.message(AdminStates.waiting_for_broadcast_text)
async def cmd_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip()
    await state.clear()

    if text.lower() == "скасувати":
        await message.answer("Розсилку скасовано.")
        return

    sent = 0
    for uid in REGISTERED_USERS:
        try:
            await bot.send_message(uid, f"📢 <b>Новина від нашого магазину:</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ Розсилку надіслано <b>{sent}</b> користувачам!", parse_mode=ParseMode.HTML)


# ==============================================================================
# 13. ТОЧКА ВХОДУ (BOOTSTRAP)
# ==============================================================================

async def main() -> None:
    bot = Bot(token=ENV_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"Не вдалося скинути вебхук: {e}")

    bot_info = await bot.get_me()
    print("\n" + "=" * 55)
    print(f"🌟 ОНОВЛЕНИЙ БОТ @{bot_info.username} ЗАПУЩЕНИЙ!")
    print(f"🔗 Посилання: https://t.me/{bot_info.username}")
    print(f"📦 База: 15 брендів x 6 ароматів = 90 парфумів!")
    if WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="👑 Бутік", web_app=WebAppInfo(url=WEBAPP_URL))
            )
            print(f"📱 Mini App MenuButton встановлено: {WEBAPP_URL}")
        except Exception as e:
            logger.warning(f"Не вдалося встановити MenuButtonWebApp: {e}")
    print("=" * 55 + "\n")

    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except (TelegramNetworkError, ConnectionError, TimeoutError, OSError) as e:
                logger.error(f"Збій мережі ({e}). Перепідключення до Telegram через 5 сек...")
                await asyncio.sleep(5)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Роботу бота завершено.")
