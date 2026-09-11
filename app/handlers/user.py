import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from app.keyboards.user_kb import get_start_kb, get_format_kb
from app.services.downloader import downloader
from aiogram.fsm.context import FSMContext

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        f"👋 Salom, {message.from_user.full_name}!\n\n"
        "🎬 Men Telegram Media Downloader Botman.\n"
        "Menga link yuboring yoki musiqa/artist nomini yozing."
    )
    await message.answer(text, reply_markup=get_start_kb())

# 1. LINK ORQALI YUKLASH
@user_router.message(F.text.startswith("http"))
async def handle_url(message: Message, state: FSMContext):
    url = message.text.strip()
    status_msg = await message.answer("🔍 Media ma'lumotlari tahlil qilinmoqda...")
    
    info = await downloader.get_info_async(url)
    if not info:
        await status_msg.edit_text("❌ Ushbu linkdan media topilmadi yoki havola xato.")
        return

    await state.update_data(url=url, title=info.get("title", "Media"))
    await status_msg.edit_text(
        f"📌 <b>{info.get('title', 'Media')}</b>\n\nYuklab olish formatini tanlang:",
        parse_mode="HTML",
        reply_markup=get_format_kb(url)
    )

# 2. FORMAT TANLANGANDA YUKLAB BERISH (CALLBACK)
@user_router.callback_query(F.data.startswith("dl:"))
async def process_download(callback: CallbackQuery, state: FSMContext):
    format_type = callback.data.split(":")[1]
    data = await state.get_data()
    url = data.get("url")

    if not url:
        await callback.message.edit_text("❌ Seans muddati tugagan. Linkni qayta yuboring.")
        return

    await callback.message.edit_text("⬇️ Yuklab olinmoqda, kuting...")
    
    try:
        file_path = await downloader.download_async(url, format_type)
        await callback.message.edit_text("📤 Telegram'ga yuklanmoqda...")
        
        from aiogram.types import FSInputFile
        input_file = FSInputFile(file_path)

        if format_type == "audio":
            await callback.message.answer_audio(audio=input_file)
        else:
            await callback.message.answer_video(video=input_file)
            
        await callback.message.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await callback.message.edit_text(f"❌ Yuklab olishda xatolik yuz berdi: {str(e)}")

# 3. SOZLAMALAR TUGMASI (Matn yoki Callback variantlari uchun)
@user_router.message(F.text.in_({"⚙️ Sozlamalar", "Sozlamalar", "/settings"}))
@user_router.callback_query(F.data == "settings")
async def handle_settings(event):
    text = "⚙️ <b>Sozlamalar bo'limi:</b>\n\nBu yerda bot sozlamalarini o'zgartirishingiz mumkin."
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

# 4. STATISTIKA TUGMASI
@user_router.message(F.text.in_({"📊 Statistika", "Statistika", "/stats"}))
@user_router.callback_query(F.data == "stats")
async def handle_stats(event):
    text = "📊 <b>Bot Statistikasi:</b>\n\nFoydalanuvchilar soni: 1"
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

# 5. ARTIST VA MUSIQA NOMI BO'YICHA QIDIRUV (Link bo'lmagan oddiy matnlar uchun)
@user_router.message(F.text & ~F.text.startswith("http"))
async def search_music_by_name(message: Message, state: FSMContext):
    query = message.text.strip()
    status_msg = await message.answer(f"🔍 <b>{query}</b> bo'yicha musiqa qidirilmoqda...", parse_mode="HTML")
    
    try:
        search_url = f"ytsearch1:{query}"
        info = await downloader.get_info_async(search_url)
        
        if not info:
            await status_msg.edit_text("❌ Hech narsa topilmadi.")
            return

        # Qidiruv natijasida topilgan haqiqiy youtube linkini saqlaymiz:
        actual_url = info.get("webpage_url") or info.get("url") or search_url
        title = info.get("title", query)

        # FSM state ga URL va nomini saqlaymiz (Tugma bosilganda ishlashi uchun)
        await state.update_data(url=actual_url, title=title)

        await status_msg.edit_text(
            f"🎵 Topildi: <b>{title}</b>\n\nYuklab olish formatini tanlang:",
            parse_mode="HTML",
            reply_markup=get_format_kb(actual_url)
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Qidiruvda xatolik yuz berdi: {str(e)}")
