import logging
import os
import asyncio
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

# --- Jadwal tugas (list string) ---
JADWAL_PAGI = [
    "07.05 cek link pc indo",
    "07.00 cek phising",
    "07.05 cek dana PGA BL",
    "07.15 req dana PGA",
    "07.30 paito berita",
    "08.00 total depo",
    "08.00 Slot Harian",
    "08.00 jadwalkan bukti jp ke jam 10.00",
    "08.10 BC link alternatif ke jam 12.00",
    "09.00 jowo pools",
    "09.10 TO semua pasaran",
    "09.30 Audit BCA",
    "09.45 First Register",
    "10.00 BC maintenance done ( kamis )",
    "10.00 cek data selisih",
    "10.00 total depo",
    "10.30 isi data bola ( > jam 1 )",
    "11.00 bc maintenance WL ( selasa )",
    "11.00 bc jadwal bola",
    "12.00 total depo",
    "12.00 slot & rng mingguan",
    "12.50 live ttm",
    "12.30 cek phising",
    "13.00 wd report",
    "13.00 BC Result Toto Macau",
    "13.30 slot & rng harian",
    "14.00 BC Result Sydney",
    "14.00 depo harian",
]

JADWAL_SIANG = [
    "15.30 cek link",
    "16.00 cek phising",
    "16.00 deposit harian",
    "16.30 jadwalkan bukti jp ke jam 17.00",
    "16.00 isi data selisih",
    "16.00 BC Result Toto Macau",
    "17.40 SLOT harian ( kalau tifak ada sgp jam 18.30 )",
    "17.50 BC Result Singapore",
    "18.00 5 lucky ball",
    "18.00 deposit harian",
    "18.05 BC link alt ke jam 19.00",
    "18.10 isi data wlb2c",
    "19.00 BC Result Toto Macau",
    "19.30 Audit BCA",
    "19.45 First Register",
    "20.00 deposit harian",
    "21.00 jowo pools",
    "21.00 cek phising",
    "21.00 wd report",
    "22.00 BC Result Toto Macau",
    "22.00 deposit harian",
    "22.45 Slot harian",
]

JADWAL_MALAM = [
    "23.00 SLOT harian",
    "23.10 BC Result Hongkong",
    "23.30 cek link & cek phising",
    "23.30 BC rtp slot jam 00.10",
    "23.40 depo harian",
    "00.05 BC Result Toto Macau",
    "00.01 update total bonus",
    "00.30 BC link alt jam 5",
    "00.30 BC bukti JP jam 4",
    "00.30 BC maintenance mingguan ke jam 4 ( kamis )",
    "00.45 slot harian",
    "01.00 isi biaya pulsa / isi akuran ( senin subuh )",
    "01.30 isi data promo",
    "02.00 total depo",
    "02.00 cek pl config",
    "03.30 Audit BCA",
    "03.45 First Register",
    "04.00 total depo",
    "05.00 cek phising",
    "05.00 wd report",
    "05.00 Slot harian",
    "05.45 total depo",
]

# --- Helper: buat keyboard list tugas dengan tombol ✅ ---
def build_jadwal_keyboard(jadwal_list, done_set):
    keyboard = []
    for idx, item in enumerate(jadwal_list):
        done_mark = "✅ " if idx in done_set else ""
        keyboard.append(
            [InlineKeyboardButton(f"{done_mark}{item}", callback_data=f"toggle_{idx}")]
        )
    # Tambah tombol kembali ke menu utama
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
    chat_id = update.effective_chat.id

    # Inisialisasi set tugas selesai per kategori dan chat jika belum ada
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

    # Toggle status selesai tugas
    if data.startswith("toggle_"):
        # Cari kategori yang sedang aktif dari chat_data (cek pesan terakhir?)
        # Untuk kesederhanaan, cek apakah idx ada di pagi, siang atau malam
        idx = int(data.split("_")[1])
        # Kita harus tahu kategori dari context message, jadi kita simpan kategori aktif di chat_data
        kategori = context.chat_data.get("active_kategori")
        if not kategori:
            # fallback: coba pagi, siang, malam sesuai idx range
            if idx < len(JADWAL_PAGI):
                kategori = "done_pagi"
            elif idx < len(JADWAL_SIANG):
                kategori = "done_siang"
                idx -= len(JADWAL_PAGI)
            else:
                kategori = "done_malam"
                idx -= len(JADWAL_PAGI) + len(JADWAL_SIANG)

        # Just to be safe, kategori valid
        if kategori not in ["done_pagi", "done_siang", "done_malam"]:
            await query.answer("⚠️ Terjadi kesalahan kategori", show_alert=True)
            return

        done_set = context.chat_data[kategori]
        if idx in done_set:
            done_set.remove(idx)
        else:
            done_set.add(idx)

        # Update keyboard berdasarkan kategori
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

    # Jika input tidak dikenali, tampilkan menu utama
    keyboard = [
        [
            InlineKeyboardButton("JADWAL PAGI", callback_data="jadwal_pagi"),
            InlineKeyboardButton("JADWAL SIANG", callback_data="jadwal_siang"),
            InlineKeyboardButton("JADWAL MALAM", callback_data="jadwal_malam"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("👋 Silakan pilih jadwal yang ingin kamu lihat:", reply_markup=reply_markup)


async def main():
    persistence = PicklePersistence(filepath="reminder_data.pkl")
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Jalankan bot sampai dihentikan manual
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
