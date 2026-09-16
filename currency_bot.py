"""
Telegram-бот: показывает курс мировых валют к рублю.
Источник данных: Центробанк РФ (бесплатный, без ключа API).

Установка зависимостей:
    pip install python-telegram-bot==21.* requests --break-system-packages

Запуск:
    export BOT_TOKEN="ваш_токен_от_BotFather"
    python currency_bot.py
"""

import logging
import os

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

# Валюты, которые показываем по команде /rates.
# Ключ — код валюты (как в ответе ЦБ), значение — человекочитаемое имя.
CURRENCIES = {
    "USD": "Доллар США",
    "EUR": "Евро",
    "GBP": "Фунт стерлингов",
    "CNY": "Китайский юань",
    "JPY": "Японская иена (100)",
    "CHF": "Швейцарский франк",
    "TRY": "Турецкая лира",
    "KZT": "Казахстанский тенге (100)",
}


def fetch_rates() -> dict:
    """Запрашивает актуальные курсы у ЦБ РФ и возвращает словарь code -> rate (в рублях)."""
    response = requests.get(CBR_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data["Valute"]


def format_rates_message(valute_data: dict) -> str:
    lines = ["💱 <b>Курсы валют к рублю</b>\n"]
    for code, name in CURRENCIES.items():
        info = valute_data.get(code)
        if not info:
            continue
        # Nominal — за сколько единиц валюты дана цена (например, 100 иен)
        nominal = info["Nominal"]
        value = info["Value"]
        previous = info["Previous"]
        diff = value - previous
        arrow = "🔺" if diff > 0 else ("🔻" if diff < 0 else "▪️")
        lines.append(
            f"{arrow} <b>{name}</b> ({code}): {value:.2f} ₽ за {nominal} "
            f"({diff:+.2f})"
        )
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я показываю курсы мировых валют к рублю.\n\n"
        "Команды:\n"
        "/rates — показать текущие курсы\n"
        "/rate <код валюты> — курс конкретной валюты, например /rate USD"
    )


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        valute_data = fetch_rates()
        text = format_rates_message(valute_data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка при получении курсов")
        text = "Не удалось получить курсы валют. Попробуйте позже."
    await update.message.reply_text(text, parse_mode="HTML")


async def rate_single(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Укажите код валюты, например: /rate USD"
        )
        return

    code = context.args[0].upper()
    try:
        valute_data = fetch_rates()
    except Exception:
        logger.exception("Ошибка при получении курсов")
        await update.message.reply_text("Не удалось получить курсы валют. Попробуйте позже.")
        return

    info = valute_data.get(code)
    if not info:
        await update.message.reply_text(
            f"Валюта с кодом {code} не найдена. "
            "Используйте стандартные коды: USD, EUR, GBP, CNY и т.д."
        )
        return

    nominal = info["Nominal"]
    value = info["Value"]
    name = info["Name"]
    await update.message.reply_text(
        f"💰 {name} ({code}): {value:.2f} ₽ за {nominal}"
    )


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Установите переменную окружения BOT_TOKEN "
            "с токеном, полученным от @BotFather."
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rates", rates))
    application.add_handler(CommandHandler("rate", rate_single))

    logger.info("Бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main()
