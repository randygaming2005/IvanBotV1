import logging
import os
import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    PicklePersistence,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN_HERE"
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE")  # ex: https://yourapp.onrender.com
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_URL_BASE}{WEBHOOK_PATH}" if WEBHOOK_URL_BASE else None

timezone = pytz.timezone("Asia/Jakarta")

persistence = PicklePersistence(filepath="data.pkl")

# Jadwal lengkap per sesi
JADWAL_PAGI = [
    "07:00 cek phising",
    "07:05 cek link pc indo",
    "07:05 cek dana PGA BL",
    "07:15 req dana PGA",
    "07:30 paito berita",
    "08:00 total depo",
    "08:00 Slot Harian",
    "08:00 jadwalkan bukti jp ke jam 10.00",
    "08:10 BC link alternatif ke jam 12.00",
    "09:00 jowo pools",
    "09:10 TO semua pasaran",
    "09:30 Audit BCA",
    "09:45 First Register",
    "10:00 BC maintenance done ( kamis )",
    "10:00 cek data selisih",
    "10:00 total depo",
    "10:30 isi data bola ( > jam 1 )",
    "11:00 bc maintenance WL ( selasa )",
    "11:00 bc jadwal bola",
    "12:00 total depo",
    "12:00 slot & rng mingguan",
    "12:30 cek phising",
    "12:50 live ttm",
    "13:00 wd report",
    "13:00 BC Result Toto Macau",
    "13:30 slot & rng harian",
    "14:00 BC Result Sydney",
    "14:00 depo harian",
]

JADWAL_SIANG = [
    "15:30 cek link",
    "16:00 cek phising",
    "16:00 deposit harian",
    "16:00 isi data selisih",
    "16:00 BC Result Toto Macau",
    "16:30 jadwalkan bukti jp ke jam 17.00",
    "17:40 SLOT harian ( kalau tifak ada sgp jam 18.30 )",
    "17:50 BC Result Singapore",
    "18:00 5 lucky ball",
    "18:00 deposit harian",
    "18:05 BC link alt ke jam 19.00",
    "18:10 isi data wlb2c",
    "19:00 BC Result Toto Macau",
    "19:30 Audit BCA",
    "19:45 First Register",
    "20:00 deposit harian",
    "21:00 jowo pools",
    "21:00 cek phising",
    "21:00 wd report",
    "22:00 BC Result Toto Macau",
    "22:00 deposit harian",
    "22:45 Slot harian",
]

JADWAL_MALAM = [
    "23:00 SLOT harian",
    "23:10 BC Result Hongkong",
    "23:30 cek link & cek phising",
    "23:30 BC rtp slot jam 00.10",
    "23:40 depo harian",
    "00:01 update total bonus",
    "00:05 BC Result Toto Macau",
    "00:30 BC link alt jam 5",
    "00:30 BC bukti JP jam 4",
    "00:30 BC maintenance mingguan ke jam 4 ( kamis )",
    "00:45 slot harian",
    "01:00 isi biaya pulsa / isi akuran ( senin subuh )",
    "01:30 isi data promo",
    "02:00 total depo",
    "02:00 cek pl config",
    "03:30 Audit BCA",
    "03:45 First Register",
    "04:00 total depo",
    "05:00 cek phising",
    "05:00 wd report",
    "05:00 Slot harian",
    "05:45 total depo",
]

# KEYBOARD MENU
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi")],
        [InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang")],
        [InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam")],
    ]
    return InlineKeyboardMarkup(buttons)


def jadwal_keyboard(jadwal_list, done_set):
    buttons = []
    for idx, item in enumerate(jadwal_list):
        label = f"✅ {item}" if idx in done_set else item
        # callback_data format: "toggle_done:<idx>"
        buttons.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"toggle_done:{idx}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Silakan pilih jadwal yang ingin dilihat:",
        reply_markup=main_menu_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_data = context.chat_data

    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text(
            "Silakan pilih jadwal yang ingin dilihat:", reply_markup=main_menu_keyboard()
        )
        return

    if data == "jadwal_pagi":
        chat_data["current_jadwal"] = "pagi"
        done_set = chat_data.setdefault("done_pagi", set())
        await query.edit_message_text(
            "JADWAL PAGI:\n\n"
            + format_jadwal(JADWAL_PAGI, done_set),
            reply_markup=jadwal_keyboard(JADWAL_PAGI, done_set),
        )
        return

    if data == "jadwal_siang":
        chat_data["current_jadwal"] = "siang"
        done_set = chat_data.setdefault("done_siang", set())
        await query.edit_message_text(
            "JADWAL SIANG:\n\n"
            + format_jadwal(JADWAL_SIANG, done_set),
            reply_markup=jadwal_keyboard(JADWAL_SIANG, done_set),
        )
        return

    if data == "jadwal_malam":
        chat_data["current_jadwal"] = "malam"
        done_set = chat_data.setdefault("done_malam", set())
        await query.edit_message_text(
            "JADWAL MALAM:\n\n"
            + format_jadwal(JADWAL_MALAM, done_set),
            reply_markup=jadwal_keyboard(JADWAL_MALAM, done_set),
        )
        return

    # toggle_done:<idx>
    if data.startswith("toggle_done:"):
        try:
            idx = int(data.split(":")[1])
        except:
            await query.answer("Data tidak valid.", show_alert=True)
            return

        current = chat_data.get("current_jadwal")
        if not current:
            await query.answer("Pilih jadwal dulu.", show_alert=True)
            return

        key = f"done_{current}"
        done_set = chat_data.setdefault(key, set())

        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)

        # Update message with new keyboard and text
        jadwal_list = {
            "pagi": JADWAL_PAGI,
            "siang": JADWAL_SIANG,
            "malam": JADWAL_MALAM,
        }[current]

        await query.edit_message_text(
            f"JADWAL {current.upper()}:\n\n" + format_jadwal(jadwal_list, done_set),
            reply_markup=jadwal_keyboard(jadwal_list, done_set),
        )


def format_jadwal(jadwal_list, done_set):
    lines = []
    for idx, item in enumerate(jadwal_list):
        prefix = "✅ " if idx in done_set else "⬜ "
        lines.append(f"{prefix}{item}")
    return "\n".join(lines)


async def waktu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(timezone)
    await update.message.reply_text(f"Waktu server sekarang:\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception occurred:", exc_info=context.error)
    if hasattr(update, "effective_chat") and update.effective_chat:
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                text="⚠️ Terjadi kesalahan. Silakan coba lagi nanti.",
            )
        except Exception:
            pass


# Webhook handlers with aiohttp

async def handle_root(request):
    return web.Response(text="Bot is running")


async def handle_webhook(request):
    application = request.app["application"]
    update_json = await request.json()
    from telegram import Update as TgUpdate

    update = TgUpdate.de_json(update_json, application.bot)
    await application.update_queue.put(update)
    return web.Response()


def parse_time_from_task(task_str):
    # Parse "HH:MM" from string like "07:00 cek phising"
    try:
        time_part = task_str.split()[0]
        hour, minute = map(int, time_part.split(":"))
        return hour, minute
    except Exception:
        return None


async def send_reminder(application, session_name, task_idx, task_text):
    chat_data_all = application.persistence.get_chat_data()
    for chat_id_str, data in chat_data_all.items():
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            continue

        done_key = f"done_{session_name}"
        done_set = data.get(done_key, set())

        if task_idx not in done_set:
            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⏰ *Pengingat tugas {session_name.upper()}*\n"
                        f"Tugas ke-{task_idx + 1}: {task_text}\n"
                        f"(Pengingat 5 menit sebelum waktu tugas)"
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logging.error(f"Gagal mengirim reminder ke chat {chat_id}: {e}")


async def reminder_loop(application):
    while True:
        now = datetime.datetime.now(timezone)
        now_plus_5 = now + datetime.timedelta(minutes=5)
        target_hour = now_plus_5.hour
        target_minute = now_plus_5.minute

        schedules = {
            "pagi": JADWAL_PAGI,
            "siang": JADWAL_SIANG,
            "malam": JADWAL_MALAM,
        }

        for session_name, tasks in schedules.items():
            for idx, task in enumerate(tasks):
                parsed_time = parse_time_from_task(task)
                if parsed_time is None:
                    continue
                task_hour, task_minute = parsed_time
                if task_hour == target_hour and task_minute == target_minute:
                    await send_reminder(application, session_name, idx, task)
        await asyncio.sleep(60)


async def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("waktu", waktu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # Run reminder_loop in background
    application.job_queue.run_repeating(
        lambda ctx: asyncio.create_task(reminder_loop(application)), interval=60, first=10
    )

    # Webhook mode
    if WEBHOOK_URL_BASE:
        app = web.Application()
        app["application"] = application
        app.router.add_get("/", handle_root)
        app.router.add_post(WEBHOOK_PATH, handle_webhook)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 3000)))
        await site.start()

        print("Webhook server started")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await application.updater.idle()
    else:
        # Polling mode (local testing)
        await application.initialize()
        await application.start()
        print("Bot started (polling mode)")
        await application.updater.start_polling()
        await application.updater.idle()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
