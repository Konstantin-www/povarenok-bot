import os
import json
import asyncio
import logging
import aiohttp
import re
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get"8872185584:AAG7DZtkhL0tsXYkqCTC1XH_oKLEhUZIDz8"
SPOONACULAR_API_KEY = os.environ.get"ff2074b38a1a47a5bc8132a80e3ba538"
YANDEX_API_KEY = os.environ.get"AQVNyxYCuPqzNZo7EJsPQlGWouQLkpoozqiSYTP_"

# Для локального запуска — раскомментируй и вставь свои ключи:
# TELEGRAM_TOKEN = ""
# SPOONACULAR_API_KEY = ""
# YANDEX_API_KEY = ""

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан! Установи переменную окружения.")
if not SPOONACULAR_API_KEY:
    raise ValueError("SPOONACULAR_API_KEY не задан! Установи переменную окружения.")
if not YANDEX_API_KEY:
    raise ValueError("YANDEX_API_KEY не задан! Установи переменную окружения.")

SPOONACULAR_BASE = "https://api.spoonacular.com"
YANDEX_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

INGREDIENTS, CHOOSE_RECIPE = range(2)

translation_cache = {}

RU_TO_EN = {
    "курица": "chicken", "куриная": "chicken", "куриное": "chicken", "куриные": "chicken",
    "говядина": "beef", "говяжья": "beef", "говяжий": "beef",
    "свинина": "pork", "свиная": "pork", "свиной": "pork",
    "баранина": "lamb", "ягненок": "lamb",
    "индейка": "turkey", "утка": "duck", "кролик": "rabbit",
    "рыба": "fish", "лосось": "salmon", "тунец": "tuna", "треска": "cod",
    "креветки": "shrimp", "креветка": "shrimp",
    "помидор": "tomato", "помидоры": "tomato", "томат": "tomato", "томаты": "tomato",
    "огурец": "cucumber", "огурцы": "cucumber",
    "перец": "pepper", "перцы": "pepper", "болгарский": "pepper",
    "лук": "onion", "лук репчатый": "onion", "красный лук": "onion",
    "чеснок": "garlic",
    "морковь": "carrot", "морковка": "carrot",
    "картофель": "potato", "картошка": "potato",
    "кабачок": "zucchini", "кабачки": "zucchini",
    "баклажан": "eggplant", "баклажаны": "eggplant",
    "капуста": "cabbage", "брокколи": "broccoli", "цветная": "cauliflower",
    "шпинат": "spinach", "салат": "lettuce", "салат листовой": "lettuce",
    "грибы": "mushroom", "гриб": "mushroom", "шампиньоны": "mushroom",
    "авокадо": "avocado",
    "кукуруза": "corn",
    "горошек": "peas", "горох": "peas",
    "фасоль": "beans", "стручковая фасоль": "green beans",
    "тыква": "pumpkin", "свекла": "beetroot", "редис": "radish",
    "сельдерей": "celery", "спаржа": "asparagus",
    "яблоко": "apple", "яблоки": "apple",
    "банан": "banana", "бананы": "banana",
    "лимон": "lemon", "лайм": "lime", "апельсин": "orange",
    "клубника": "strawberry", "малина": "raspberry", "черника": "blueberry",
    "виноград": "grapes", "ананас": "pineapple", "манго": "mango",
    "молоко": "milk", "сливки": "cream", "сметана": "sour cream",
    "йогурт": "yogurt", "кефир": "yogurt",
    "сыр": "cheese", "творог": "cottage cheese", "моцарелла": "mozzarella",
    "пармезан": "parmesan", "чеддер": "cheddar", "фета": "feta",
    "масло": "butter", "сливочное масло": "butter", "маргарин": "margarine",
    "яйцо": "egg", "яйца": "egg", "яйцо куриное": "egg",
    "рис": "rice", "гречка": "buckwheat", "гречневая": "buckwheat",
    "макароны": "pasta", "спагетти": "spaghetti", "лапша": "noodles",
    "паста": "pasta", "фарфалле": "pasta", "пенне": "penne",
    "мука": "flour", "пшеничная мука": "flour",
    "хлеб": "bread", "батон": "bread", "багет": "baguette",
    "чечевица": "lentil", "нут": "chickpea", "бобы": "beans",
    "миндаль": "almond", "грецкий": "walnut", "грецкие": "walnut",
    "кунжут": "sesame", "семечки": "sunflower seeds",
    "соль": "salt", "перец черный": "black pepper", "перец молотый": "pepper",
    "сахар": "sugar", "мед": "honey",
    "оливковое масло": "olive oil", "растительное масло": "vegetable oil",
    "соевый соус": "soy sauce", "томатная паста": "tomato paste",
    "горчица": "mustard", "кетчуп": "ketchup", "майонез": "mayonnaise",
    "вода": "water", "лед": "ice",
    "кокосовое молоко": "coconut milk", "кокос": "coconut",
    "шоколад": "chocolate", "какао": "cocoa",
    "ваниль": "vanilla", "корица": "cinnamon",
    "петрушка": "parsley", "укроп": "dill", "базилик": "basil",
    "кинза": "coriander", "cilantro": "coriander",
    "имбирь": "ginger", "куркума": "turmeric", "паприка": "paprika",
    "тесто": "dough", "слоеное тесто": "puff pastry",
    "тортилья": "tortilla", "лаваш": "flatbread",
    "консервы": "canned", "тунец консервированный": "canned tuna",
    "колбаса": "sausage", "ветчина": "ham", "бекон": "bacon",
    "сосиски": "sausage", "фарш": "minced meat", "фарш говяжий": "beef mince",
    "вино": "wine", "белое вино": "white wine", "красное вино": "red wine",
    "пиво": "beer", "коньяк": "brandy", "ром": "rum",
    "сок": "juice", "лимонный сок": "lemon juice", "лаймовый сок": "lime juice",
}


def clean_ingredients(text):
    raw = [i.strip() for i in text.split(",") if i.strip()]
    cleaned = []
    for item in raw:
        clean = re.sub(r"\d+[\s\.]?(г|кг|шт|л|мл|ч\.л\.|ст\.л\.|грамм|грамма|штук|штуки|литр|миллилитр|g|kg|pcs|ml|l|tsp|tbsp|grams|gram|pieces|liters|milliliters)?", "", item).strip()
        if clean:
            cleaned.append(clean)
    return cleaned


def translate_ingredients_ru_to_en(text):
    raw = clean_ingredients(text)
    translated = []
    for item in raw:
        item_lower = item.lower()
        if item_lower in RU_TO_EN:
            translated.append(RU_TO_EN[item_lower])
        else:
            translated.append(item)
    return translated


async def translate_text(session, text):
    if not text or len(text.strip()) < 2:
        return text
    if text in translation_cache:
        return translation_cache[text]
    try:
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "sourceLanguageCode": "en",
            "targetLanguageCode": "ru",
            "texts": [text],
        }
        async with session.post(YANDEX_TRANSLATE_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                translations = data.get("translations", [])
                if translations:
                    result = translations[0].get("text", text)
                    translation_cache[text] = result
                    return result
            else:
                logger.warning(f"Yandex translate error: {resp.status}")
    except Exception as e:
        logger.warning(f"Yandex translation failed: {e}")
    return text


async def translate_batch(session, texts):
    if not texts:
        return texts
    to_translate = []
    indices = []
    for i, text in enumerate(texts):
        if text in translation_cache:
            texts[i] = translation_cache[text]
        else:
            to_translate.append(text)
            indices.append(i)
    if not to_translate:
        return texts
    try:
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "sourceLanguageCode": "en",
            "targetLanguageCode": "ru",
            "texts": to_translate,
        }
        async with session.post(YANDEX_TRANSLATE_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                data = await resp.json()
                translations = data.get("translations", [])
                for idx, trans in zip(indices, translations):
                    result = trans.get("text", texts[idx])
                    translation_cache[to_translate[indices.index(idx)]] = result
                    texts[idx] = result
    except Exception as e:
        logger.warning(f"Yandex batch translation failed: {e}")
    return texts


async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Найти рецепт по продуктам", callback_data="find_recipe")],
        [InlineKeyboardButton("Случайный рецепт", callback_data="random_recipe")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот-поваренок.\n\n"
        "Напиши, что у тебя есть в холодильнике - и я подберу рецепт.\n"
        "Можно писать по-русски: курица, помидоры, сыр, рис\n"
        "Также могу найти случайный рецепт на удачу!",
        reply_markup=reply_markup,
    )


async def help_command(update, context):
    text = """Как пользоваться:

1. Нажми "Найти рецепт по продуктам"
2. Перечисли ингредиенты через запятую
   Можно по-русски: курица, помидоры, сыр, рис
   Или по-английски: chicken, tomato, cheese, rice
3. Выбери понравившийся рецепт из списка

Советы:
- Чем больше ингредиентов - тем точнее подбор
- Можно указать количество: 2 яйца, 100г сыра
- Бот понимает русские названия продуктов
- Бесплатный лимит Spoonacular: 150 запросов в день"""
    await update.message.reply_text(text)


async def find_recipe_start(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Напиши, что есть в холодильнике.\n"
        "Перечисли продукты через запятую.\n"
        "Можно по-русски: курица, помидоры, сыр, рис, лук\n"
        "Или по-английски: chicken, tomato, cheese, rice, onion",
    )
    return INGREDIENTS


async def process_ingredients(update, context):
    ingredients_raw = update.message.text
    user = update.effective_user
    logger.info(f"User {user.id} searched for: {ingredients_raw}")

    await update.message.chat.send_action(action="typing")

    ingredients_en = translate_ingredients_ru_to_en(ingredients_raw)
    if not ingredients_en:
        await update.message.reply_text("Не распознал продукты. Попробуй написать по-другому.")
        return ConversationHandler.END

    ingredients_str = ",".join(ingredients_en)
    logger.info(f"Translated to EN: {ingredients_str}")

    url = f"{SPOONACULAR_BASE}/recipes/findByIngredients"
    params = {
        "ingredients": ingredients_str,
        "number": 5,
        "ranking": 1,
        "ignorePantry": "true",
        "apiKey": SPOONACULAR_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 402:
                    await update.message.reply_text(
                        "Лимит Spoonacular исчерпан (150 запросов/день).\n"
                        "Попробуй завтра или обнови план на spoonacular.com"
                    )
                    return ConversationHandler.END

                if resp.status != 200:
                    await update.message.reply_text("Ошибка сервера. Попробуй позже.")
                    return ConversationHandler.END

                recipes = await resp.json()

                if not recipes:
                    await update.message.reply_text(
                        f"Не нашел рецептов с такими продуктами.\n"
                        f"Попробуй другие ингредиенты или проверь написание."
                    )
                    return ConversationHandler.END

                titles = [r.get("title", "") for r in recipes]
                titles_ru = await translate_batch(session, titles)
                for recipe, title_ru in zip(recipes, titles_ru):
                    recipe["title_ru"] = title_ru

                context.user_data["recipes"] = recipes
                context.user_data["ingredients"] = ingredients_raw

                text = f"Рецепты из: {ingredients_raw}\n\n"
                keyboard = []

                for i, recipe in enumerate(recipes, 1):
                    used = recipe.get("usedIngredientCount", 0)
                    missed = recipe.get("missedIngredientCount", 0)
                    likes = recipe.get("likes", 0)
                    title_ru = recipe.get("title_ru", recipe["title"])

                    text += (
                        f"{i}. {title_ru}\n"
                        f"   (ориг: {recipe['title']})\n"
                        f"   Использует твоих: {used}\n"
                        f"   Нужно докупить: {missed}\n"
                        f"   Лайков: {likes}\n\n"
                    )

                    keyboard.append([
                        InlineKeyboardButton(
                            f"{i}. {title_ru[:30]}",
                            callback_data=f"recipe_{recipe['id']}"
                        )
                    ])

                keyboard.append([InlineKeyboardButton("Новый поиск", callback_data="find_recipe")])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(text, reply_markup=reply_markup)
                return CHOOSE_RECIPE

    except Exception as e:
        logger.error(f"Error fetching recipes: {e}")
        await update.message.reply_text("Ошибка при поиске. Попробуй еще раз позже.")
        return ConversationHandler.END


async def show_recipe_details(update, context):
    query = update.callback_query
    await query.answer()

    recipe_id = query.data.replace("recipe_", "")

    await query.edit_message_text("Загружаю рецепт...")

    url = f"{SPOONACULAR_BASE}/recipes/{recipe_id}/information"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "includeNutrition": "false",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 402:
                    await query.edit_message_text("Лимит API исчерпан. Попробуй завтра.")
                    return ConversationHandler.END

                if resp.status != 200:
                    await query.edit_message_text("Не удалось загрузить рецепт.")
                    return ConversationHandler.END

                recipe = await resp.json()

                title = recipe.get("title", "Без названия")
                image = recipe.get("image")
                ready_in = recipe.get("readyInMinutes", "?")
                servings = recipe.get("servings", "?")
                source = recipe.get("sourceUrl", "")

                title_ru = await translate_text(session, title)

                ingredients_list = []
                ingredient_names = []
                for ing in recipe.get("extendedIngredients", []):
                    name = ing.get("name", "")
                    ingredient_names.append(name)

                names_ru = await translate_batch(session, ingredient_names)

                for ing, name_ru in zip(recipe.get("extendedIngredients", []), names_ru):
                    amount = ing.get("measures", {}).get("metric", {}).get("amount", "")
                    unit = ing.get("measures", {}).get("metric", {}).get("unitShort", "")
                    if amount and unit:
                        ingredients_list.append(f"- {name_ru} - {amount:.1f} {unit}")
                    else:
                        ingredients_list.append(f"- {name_ru}")

                instructions = ""
                analyzed = recipe.get("analyzedInstructions", [])
                if analyzed and analyzed[0].get("steps"):
                    step_texts = [step["step"] for step in analyzed[0]["steps"]]
                    steps_ru = await translate_batch(session, step_texts)
                    for i, (step, step_ru) in enumerate(zip(analyzed[0]["steps"], steps_ru), 1):
                        instructions += f"{i}. {step_ru}\n\n"
                else:
                    raw_instr = recipe.get("instructions", "Инструкции не найдены.")
                    instructions = await translate_text(session, raw_instr)

                text = (
                    f"{title_ru}\n"
                    f"(оригинал: {title})\n"
                    f"Готовится за: {ready_in} мин | Порций: {servings}\n\n"
                    f"Ингредиенты:\n" + "\n".join(ingredients_list) + "\n\n"
                    f"Приготовление:\n{instructions[:900]}"
                )

                if len(instructions) > 900:
                    text += "..."

                keyboard = []
                if source:
                    keyboard.append([InlineKeyboardButton("Источник (оригинал)", url=source)])
                keyboard.append([InlineKeyboardButton("Назад к списку", callback_data="back_to_list")])
                keyboard.append([InlineKeyboardButton("В главное меню", callback_data="main_menu")])
                keyboard.append([InlineKeyboardButton("Новый поиск", callback_data="find_recipe")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                if image:
                    await query.message.reply_photo(
                        photo=image,
                        caption=text[:1024],
                        reply_markup=reply_markup,
                    )
                    if len(text) > 1024:
                        await query.message.reply_text(text[1024:], reply_markup=reply_markup)
                else:
                    await query.edit_message_text(text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error fetching recipe details: {e}")
        await query.edit_message_text("Ошибка при загрузке рецепта.")

    return ConversationHandler.END


async def back_to_list(update, context):
    query = update.callback_query
    await query.answer()

    recipes = context.user_data.get("recipes", [])
    ingredients = context.user_data.get("ingredients", "")

    if not recipes:
        await query.edit_message_text("Список устарел. Начни новый поиск с /start")
        return ConversationHandler.END

    text = f"Рецепты из: {ingredients}\n\n"
    keyboard = []

    for i, recipe in enumerate(recipes, 1):
        used = recipe.get("usedIngredientCount", 0)
        missed = recipe.get("missedIngredientCount", 0)
        title_ru = recipe.get("title_ru", recipe["title"])

        text += (
            f"{i}. {title_ru}\n"
            f"   (ориг: {recipe['title']})\n"
            f"   Использует твоих: {used}\n"
            f"   Нужно докупить: {missed}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {title_ru[:30]}",
                callback_data=f"recipe_{recipe['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("Новый поиск", callback_data="find_recipe")])
    keyboard.append([InlineKeyboardButton("В главное меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup)
    return CHOOSE_RECIPE


async def random_recipe(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ищу случайный рецепт...")

    url = f"{SPOONACULAR_BASE}/recipes/random"
    params = {
        "number": 1,
        "apiKey": SPOONACULAR_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 402:
                    await query.edit_message_text("Лимит API исчерпан. Попробуй завтра.")
                    return ConversationHandler.END

                if resp.status != 200:
                    await query.edit_message_text("Не удалось загрузить случайный рецепт.")
                    return ConversationHandler.END

                data = await resp.json()
                recipes = data.get("recipes", [])
                if not recipes:
                    await query.edit_message_text("Рецепт не найден.")
                    return ConversationHandler.END

                recipe = recipes[0]

                title = recipe.get("title", "Без названия")
                image = recipe.get("image")
                ready_in = recipe.get("readyInMinutes", "?")
                servings = recipe.get("servings", "?")
                source = recipe.get("sourceUrl", "")

                title_ru = await translate_text(session, title)

                ingredients_list = []
                ingredient_names = []
                for ing in recipe.get("extendedIngredients", []):
                    name = ing.get("name", "")
                    ingredient_names.append(name)

                names_ru = await translate_batch(session, ingredient_names)

                for ing, name_ru in zip(recipe.get("extendedIngredients", []), names_ru):
                    amount = ing.get("measures", {}).get("metric", {}).get("amount", "")
                    unit = ing.get("measures", {}).get("metric", {}).get("unitShort", "")
                    if amount and unit:
                        ingredients_list.append(f"- {name_ru} - {amount:.1f} {unit}")
                    else:
                        ingredients_list.append(f"- {name_ru}")

                instructions = ""
                analyzed = recipe.get("analyzedInstructions", [])
                if analyzed and analyzed[0].get("steps"):
                    step_texts = [step["step"] for step in analyzed[0]["steps"]]
                    steps_ru = await translate_batch(session, step_texts)
                    for i, (step, step_ru) in enumerate(zip(analyzed[0]["steps"], steps_ru), 1):
                        instructions += f"{i}. {step_ru}\n\n"
                else:
                    raw_instr = recipe.get("instructions", "Инструкции не найдены.")
                    instructions = await translate_text(session, raw_instr)

                text = (
                    f"Случайный рецепт: {title_ru}\n"
                    f"(оригинал: {title})\n"
                    f"Готовится за: {ready_in} мин | Порций: {servings}\n\n"
                    f"Ингредиенты:\n" + "\n".join(ingredients_list) + "\n\n"
                    f"Приготовление:\n{instructions[:900]}"
                )

                keyboard = []
                if source:
                    keyboard.append([InlineKeyboardButton("Источник (оригинал)", url=source)])
                keyboard.append([InlineKeyboardButton("Еще случайный", callback_data="random_recipe")])
                keyboard.append([InlineKeyboardButton("В главное меню", callback_data="main_menu")])
                keyboard.append([InlineKeyboardButton("Поиск по продуктам", callback_data="find_recipe")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                if image:
                    await query.message.reply_photo(
                        photo=image,
                        caption=text[:1024],
                        reply_markup=reply_markup,
                    )
                else:
                    await query.edit_message_text(text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error fetching random recipe: {e}")
        await query.edit_message_text("Ошибка при загрузке случайного рецепта.")

    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Отменено. Напиши /start чтобы начать заново.")
    return ConversationHandler.END


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        text = """Как пользоваться:

1. Нажми "Найти рецепт по продуктам"
2. Перечисли ингредиенты через запятую
   Можно по-русски: курица, помидоры, сыр, рис
   Или по-английски: chicken, tomato, cheese, rice
3. Выбери понравившийся рецепт из списка

Советы:
- Чем больше ингредиентов - тем точнее подбор
- Можно указать количество: 2 яйца, 100г сыра
- Бот понимает русские названия продуктов
- Бесплатный лимит Spoonacular: 150 запросов в день"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("В главное меню", callback_data="main_menu")]
        ]))
    elif query.data == "find_recipe":
        return await find_recipe_start(update, context)
    elif query.data == "random_recipe":
        return await random_recipe(update, context)
    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("Найти рецепт по продуктам", callback_data="find_recipe")],
            [InlineKeyboardButton("Случайный рецепт", callback_data="random_recipe")],
            [InlineKeyboardButton("Помощь", callback_data="help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Привет! Я бот-поваренок.\n\n"
            "Напиши, что у тебя есть в холодильнике - и я подберу рецепт.\n"
            "Можно писать по-русски: курица, помидоры, сыр, рис\n"
            "Также могу найти случайный рецепт на удачу!",
            reply_markup=reply_markup,
        )


async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(find_recipe_start, pattern=r"^find_recipe$"),
        ],
        states={
            INGREDIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_ingredients),
            ],
            CHOOSE_RECIPE: [
                CallbackQueryHandler(show_recipe_details, pattern=r"^recipe_\d+$"),
                CallbackQueryHandler(back_to_list, pattern=r"^back_to_list$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(button_handler, pattern=r"^(help|find_recipe|random_recipe|main_menu)$"),
        ],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler, pattern=r"^(help|random_recipe|main_menu)$"))

    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    if WEBHOOK_URL:
        # === WEBHOOK MODE (для Render Web Service) ===
        await application.initialize()
        webhook_path = f"/webhook/{TELEGRAM_TOKEN}"
        await application.bot.set_webhook(f"{WEBHOOK_URL}{webhook_path}")
        await application.start()

        async def handle(request):
            if request.match_info.get("token") == TELEGRAM_TOKEN:
                request_body = await request.read()
                update = Update.de_json(json.loads(request_body), application.bot)
                await application.process_update(update)
                return web.Response()
            return web.Response(status=403)

        app = web.Application()
        app.router.add_post(webhook_path, handle)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"Webhook запущен на {WEBHOOK_URL}{webhook_path} (порт {PORT})")
        await asyncio.Event().wait()
    else:
        # === POLLING MODE (для локального запуска) ===
        logger.info("Bot is running (polling)")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
