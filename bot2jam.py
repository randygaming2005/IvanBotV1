import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or "https://yourdomain.com" + WEBHOOK_PATH

app = FastAPI()

JADWAL_PAGI = [
    "07.05 cek link pc indo",
    "07.00 cek phising",
    # ... (isi lengkap seperti sebelumnya)
]

JADWAL_SIANG = [
    "15.30 cek link",
    # ... (isi lengkap)
]

JADWAL_MALAM = [
    "23.00 SLOT harian",
    # ... (isi lengkap)
]

def build_jadwal_keyboard(jadwal_list, done_set):
    keyboard = []
    for idx, item in enumerate(jadwal_list):
        done_mark = "✅ " if idx in done_set else ""
        keyboard.append(
            [InlineKeyboardButton(f"{done_mark}{item}", callback_data=f"toggle_{idx}")]
        )
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi"),
            InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang"),
            InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Halo! Silakan pilih jadwal yang ingin kamu lihat:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if "done_pagi" not in context.chat_data:
        context.chat_data["done_pagi"] = set()
    if "done_siang" not in context.chat_data:
        context.chat_data["done_siang"] = set()
    if "done_malam" not in context.chat_data:
        context.chat_data["done_malam"] = set()

    if data == "main_menu":
        keyboard = [
            [
                InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi"),
                InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang"),
                InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👋 Silakan pilih jadwal yang ingin kamu lihat:", reply_markup=reply_markup)
        return

    if data == "jadwal_pagi":
        keyboard = build_jadwal_keyboard(JADWAL_PAGI, context.chat_data["done_pagi"])
        await query.edit_message_text("📋 Jadwal Pagi - Klik item untuk tandai selesai:", reply_markup=keyboard)
        return

    if data == "jadwal_siang":
        keyboard = build_jadwal_keyboard(JADWAL_SIANG, context.chat_data["done_siang"])
        await query.edit_message_text("📋 Jadwal Siang - Klik item untuk tandai selesai:", reply_markup=keyboard)
        return

    if data == "jadwal_malam":
        keyboard = build_jadwal_keyboard(JADWAL_MALAM, context.chat_data["done_malam"])
        await query.edit_message_text("📋 Jadwal Malam - Klik item untuk tandai selesai:", reply_markup=keyboard)
        return

    if data.startswith("toggle_"):
        idx = int(data.split("_")[1])
        kategori = context.chat_data.get("active_kategori")
        if not kategori:
            if idx < len(JADWAL_PAGI):
                kategori = "done_pagi"
            elif idx < len(JADWAL_SIANG):
                kategori = "done_siang"
                idx -= len(JADWAL_PAGI)
            else:
                kategori = "done_malam"
                idx -= len(JADWAL_PAGI) + len(JADWAL_SIANG)

        if kategori not in ["done_pagi", "done_siang", "done_malam"]:
            await query.answer("⚠️ Terjadi kesalahan kategori", show_alert=True)
            return

        done_set = context.chat_data[kategori]
        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)

        if kategori == "done_pagi":
            keyboard = build_jadwal_keyboard(JADWAL_PAGI, done_set)
            await query.edit_message_text("📋 Jadwal Pagi - Klik item untuk tandai selesai:", reply_markup=keyboard)
        elif kategori == "done_siang":
            keyboard = build_jadwal_keyboard(JADWAL_SIANG, done_set)
            await query.edit_message_text("📋 Jadwal Siang - Klik item untuk tandai selesai:", reply_markup=keyboard)
        elif kategori == "done_malam":
            keyboard = build_jadwal_keyboard(JADWAL_MALAM, done_set)
            await query.edit_message_text("📋 Jadwal Malam - Klik item untuk tandai selesai:", reply_markup=keyboard)
        return

    keyboard = [
        [
            InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi"),
            InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang"),
            InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("👋 Silakan pilih jadwal yang ingin kamu lihat:", reply_markup=reply_markup)


persistence = PicklePersistence(filepath="reminder_data.pkl")
application = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Endpoint Telegram webhook menerima update POST JSON."""
    update = Update.de_json(await request.json(), application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # Set webhook sebelum run (hanya sekali, bisa jalankan secara manual)
    async def set_webhook():
        await application.bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook diset ke {WEBHOOK_URL}")

    import asyncio

    asyncio.run(set_webhook())

    # Jalankan server FastAPI di port 8443 (misal)
    uvicorn.run(app, host="0.0.0.0", port=8443)
