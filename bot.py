import os
import json
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = 8480569292

LINKS_FILE = "links.json"
BLACKLIST_FILE = "blacklist.json"
CHATS_FILE = "chats.json"

def load_json(f, default=None):
    if os.path.exists(f):
        with open(f, "r") as file:
            return json.load(file)
    return default if default is not None else {}

def save_json(f, data):
    with open(f, "w") as file:
        json.dump(data, file, indent=4)

links = load_json(LINKS_FILE, {})
blacklist = load_json(BLACKLIST_FILE, [])
chats = load_json(CHATS_FILE, {})

main_menu = ReplyKeyboardMarkup([
    ["📩 ارسال ناشناس به فرد"],
    ["🔗 لینک ناشناس من"],
    ["📤 ارسال با لینک"],
    ["👀 پیام را دیدم", "🚫 بلاک"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["📊 آمار", "📢 ارسال همگانی"],
    ["🔙 منوی اصلی"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    if str(user_id) not in links:
        links[str(user_id)] = user_id
        save_json(LINKS_FILE, links)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            f"👋 سلام مدیر {first_name}!",
            reply_markup=admin_menu
        )
        return
    
    if context.args and context.args[0].startswith("link_"):
        link_id = context.args[0].replace("link_", "")
        if link_id in links:
            target_id = links[link_id]
            try:
                target_user = await context.bot.get_chat(target_id)
                target_name = target_user.first_name or target_user.username or "کاربر"
            except:
                target_name = "کاربر"
            
            context.user_data["target"] = target_id
            await update.message.reply_text(
                f"🔗 در حال ارسال پیام ناشناس به {target_name} هستی.\n✏️ پیامت رو بنویس:"
            )
            context.user_data["waiting_for_message"] = True
            return
    
    await update.message.reply_text(
        f"👋 سلام {first_name}!\nچه کاری برات انجام بدم؟",
        reply_markup=main_menu
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == ADMIN_ID:
        if text == "📊 آمار":
            await update.message.reply_text(f"👥 کاربران: {len(links)}")
            return
        if text == "📢 ارسال همگانی":
            context.user_data["broadcast"] = True
            await update.message.reply_text("✏️ متن رو بنویس:")
            return
        if context.user_data.get("broadcast"):
            sent = 0
            for uid in links.values():
                try:
                    await context.bot.send_message(uid, f"📢 {text}")
                    sent += 1
                except:
                    pass
            await update.message.reply_text(f"✅ به {sent} کاربر ارسال شد.")
            context.user_data["broadcast"] = False
            return
        if text == "🔙 منوی اصلی":
            await update.message.reply_text("👋 برگشتی.", reply_markup=main_menu)
            return
        if context.user_data.get("waiting_for_reply"):
            target = context.user_data.get("reply_to")
            if target:
                try:
                    await context.bot.send_message(target, f"📨 {text}")
                    await update.message.reply_text("✅ ارسال شد!")
                except:
                    await update.message.reply_text("❌ خطا!")
                context.user_data["waiting_for_reply"] = False
                context.user_data["reply_to"] = None
            return
        await update.message.reply_text("از منوی ادمین استفاده کن.")
        return

    if text == "📩 ارسال ناشناس به فرد":
        await update.message.reply_text("✏️ شناسه یا لینک رو بفرست:")
        context.user_data["waiting_for_target"] = True
        return

    if text == "🔗 لینک ناشناس من":
        if str(user_id) in blacklist:
            await update.message.reply_text("🚫 بلاک هستید!")
            return
        links[str(user_id)] = user_id
        save_json(LINKS_FILE, links)
        bot_username = (await context.bot.get_me()).username
        await update.message.reply_text(
            f"https://t.me/{bot_username}?start=link_{user_id}"
        )
        return

    if text == "📤 ارسال با لینک":
        await update.message.reply_text("✏️ لینک رو بفرست:")
        context.user_data["waiting_for_link"] = True
        return

    if text == "👀 پیام را دیدم":
        sender = chats.get(str(user_id))
        if sender:
            try:
                await context.bot.send_message(sender, "👀 پیامتو دیدم")
                await update.message.reply_text("👀 اطلاع داده شد!")
            except:
                await update.message.reply_text("❌ خطا!")
        else:
            await update.message.reply_text("❌ پیامی نیست!")
        return

    if text == "🚫 بلاک":
        await update.message.reply_text("✏️ شناسه رو بفرست:")
        context.user_data["waiting_for_block"] = True
        return

    if context.user_data.get("waiting_for_target"):
        try:
            target_id = int(text)
            if str(target_id) in links:
                context.user_data["target"] = target_id
                context.user_data["waiting_for_target"] = False
                context.user_data["waiting_for_message"] = True
                await update.message.reply_text("✏️ پیامت رو بنویس:")
                return
        except:
            pass
        await update.message.reply_text("❌ شناسه نامعتبر!")
        context.user_data["waiting_for_target"] = False
        return

    if context.user_data.get("waiting_for_link"):
        match = re.search(r'start=link_(\d+)', text)
        if match and match.group(1) in links:
            context.user_data["target"] = links[match.group(1)]
            context.user_data["waiting_for_link"] = False
            context.user_data["waiting_for_message"] = True
            await update.message.reply_text("✏️ پیامت رو بنویس:")
        else:
            await update.message.reply_text("❌ لینک نامعتبر!")
            context.user_data["waiting_for_link"] = False
        return

    if context.user_data.get("waiting_for_message"):
        target = context.user_data.get("target")
        if target:
            if str(target) in blacklist:
                await update.message.reply_text("❌ این کاربر بلاک شده!")
                context.user_data["waiting_for_message"] = False
                return
            
            chats[str(target)] = user_id
            save_json(CHATS_FILE, chats)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📨 پاسخ", callback_data=f"reply_{user_id}")],
                [InlineKeyboardButton("👀 پیام را دیدم", callback_data=f"seen_{user_id}")],
                [InlineKeyboardButton("🚫 بلاک", callback_data=f"block_{user_id}")]
            ])
            
            await context.bot.send_message(
                chat_id=target,
                text=text,
                reply_markup=keyboard
            )
            await update.message.reply_text("✅ ارسال شد!")
            context.user_data["waiting_for_message"] = False
            context.user_data["target"] = None
        return

    if context.user_data.get("waiting_for_block"):
        try:
            block_id = int(text)
            if str(block_id) not in blacklist:
                blacklist.append(str(block_id))
                save_json(BLACKLIST_FILE, blacklist)
                await update.message.reply_text(f"🚫 بلاک شد!")
            else:
                await update.message.reply_text("❗ قبلاً بلاک است!")
        except:
            await update.message.reply_text("❌ شناسه نامعتبر!")
        context.user_data["waiting_for_block"] = False
        return

    await update.message.reply_text("❌ از دکمه‌ها استفاده کن!")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "reply":
        context.user_data["reply_to"] = user_id
        context.user_data["waiting_for_reply"] = True
        await query.message.reply_text("✏️ پاسخ:")

    elif action == "seen":
        try:
            await context.bot.send_message(user_id, "👀 پیامتو دیدم")
            await query.message.reply_text("👀 اطلاع داده شد!")
        except:
            await query.message.reply_text("❌ خطا!")

    elif action == "block":
        if str(user_id) not in blacklist:
            blacklist.append(str(user_id))
            save_json(BLACKLIST_FILE, blacklist)
            await query.message.reply_text("🚫 بلاک شد!")
        else:
            await query.message.reply_text("❗ قبلاً بلاک است!")

async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_reply"):
        target = context.user_data.get("reply_to")
        if target:
            try:
                await context.bot.send_message(target, f"📨 {update.message.text}")
                await update.message.reply_text("✅ ارسال شد!")
            except:
                await update.message.reply_text("❌ خطا!")
            context.user_data["waiting_for_reply"] = False
            context.user_data["reply_to"] = None

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_handler))

print("✅ ربات ناشناس کامل روشن شد!")
app.run_polling()
