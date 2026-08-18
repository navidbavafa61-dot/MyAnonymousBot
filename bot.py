from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import json
import os
import re


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("8847629801:AAGWhNJcs2dEXa4fSm2ygqw0gzkdl436iOA", "").strip()

try:
    ADMIN_ID = int(os.getenv("8480569292", "8480569292"))
except ValueError:
    ADMIN_ID = 8480569292

USERS_FILE = "users.json"
LINKS_FILE = "links.json"
BLOCKS_FILE = "blocks.json"
CHATS_FILE = "chats.json"
MESSAGES_FILE = "messages.json"
REPORTS_FILE = "reports.json"
SETTINGS_FILE = "settings.json"


# =========================================================
# DATABASE
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"LOAD ERROR {filename}: {e}")
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"SAVE ERROR {filename}: {e}")


users = load_json(USERS_FILE, {})
links = load_json(LINKS_FILE, {})
blocks = load_json(BLOCKS_FILE, {})
chats = load_json(CHATS_FILE, {})
messages = load_json(MESSAGES_FILE, {})
reports = load_json(REPORTS_FILE, [])

settings = load_json(
    SETTINGS_FILE,
    {
        "sleep": False,
        "force_join": False,
        "channel": "",
        "filter_enabled": False,
        "bad_words": [],
    },
)

settings.setdefault("sleep", False)
settings.setdefault("force_join", False)
settings.setdefault("channel", "")
settings.setdefault("filter_enabled", False)
settings.setdefault("bad_words", [])


# =========================================================
# MENUS
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📩 ارسال ناشناس"],
        ["🔗 لینک من", "🆔 شناسه من"],
        ["👤 پروفایل", "📊 آمار من"],
        ["📤 ارسال با لینک"],
        ["📋 بلاک‌ها", "👀 پیام را دیدم"],
        ["🚫 گزارش تخلف"],
    ],
    resize_keyboard=True,
)

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["📊 آمار"],
        ["📢 ارسال همگانی"],
        ["📨 ارسال به کانال"],
        ["⚙️ تنظیمات"],
        ["😴 حالت خواب"],
        ["🔙 منوی کاربر"],
    ],
    resize_keyboard=True,
)


# =========================================================
# USER HELPERS
# =========================================================

def ensure_user(user):
    uid = str(user.id)

    if uid not in users:
        users[uid] = {
            "id": user.id,
            "first_name": user.first_name or "",
            "username": user.username or "",
            "display_name": user.first_name or "کاربر",
            "sent": 0,
            "received": 0,
            "likes": 0,
            "dislikes": 0,
        }
    else:
        users[uid]["id"] = user.id
        users[uid]["first_name"] = user.first_name or ""
        users[uid]["username"] = user.username or ""

        users[uid].setdefault(
            "display_name",
            user.first_name or "کاربر"
        )

        for key in ("sent", "received", "likes", "dislikes"):
            users[uid].setdefault(key, 0)

    save_json(USERS_FILE, users)
    return users[uid]


def increase_stat(user_id, stat, amount=1):
    uid = str(user_id)

    if uid not in users:
        return

    users[uid][stat] = int(
        users[uid].get(stat, 0)
    ) + amount

    if users[uid][stat] < 0:
        users[uid][stat] = 0

    save_json(USERS_FILE, users)


def is_blocked(blocker, target):
    return str(target) in blocks.get(
        str(blocker),
        []
    )


def block_user(blocker, target):
    blocker = str(blocker)
    target = str(target)

    blocks.setdefault(blocker, [])

    if target not in blocks[blocker]:
        blocks[blocker].append(target)

    save_json(BLOCKS_FILE, blocks)


def unblock_user(blocker, target):
    blocker = str(blocker)
    target = str(target)

    if blocker in blocks:
        if target in blocks[blocker]:
            blocks[blocker].remove(target)

    save_json(BLOCKS_FILE, blocks)


def unblock_all(blocker):
    blocks[str(blocker)] = []
    save_json(BLOCKS_FILE, blocks)


def get_display_name(user_id):
    return users.get(
        str(user_id),
        {}
    ).get(
        "display_name",
        "کاربر"
    )


# =========================================================
# CHAT / MESSAGE HELPERS
# =========================================================

def set_chat(receiver, sender):
    chats[str(receiver)] = {
        "sender": int(sender)
    }

    save_json(CHATS_FILE, chats)


def get_last_sender(receiver):
    data = chats.get(str(receiver))

    if not data:
        return None

    return data.get("sender")


def message_key(receiver, message_id):
    return f"{receiver}:{message_id}"


def save_message(message_id, sender, receiver):
    key = message_key(
        receiver,
        message_id
    )

    messages[key] = {
        "message_id": message_id,
        "sender": sender,
        "receiver": receiver,
        "likes": [],
        "dislikes": [],
    }

    save_json(
        MESSAGES_FILE,
        messages
    )


def get_message_info(receiver, message_id):
    return messages.get(
        message_key(
            receiver,
            message_id
        )
    )


def save_message_info(receiver, message_id, data):
    messages[
        message_key(
            receiver,
            message_id
        )
    ] = data

    save_json(
        MESSAGES_FILE,
        messages
    )


# =========================================================
# FILTER
# =========================================================

def contains_bad_word(text):
    if not settings.get("filter_enabled"):
        return False

    text = (text or "").casefold()

    for word in settings.get("bad_words", []):
        word = str(word).strip()

        if word and word.casefold() in text:
            return True

    return False


# =========================================================
# KEYBOARD
# =========================================================

def message_keyboard(sender_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📨 پاسخ",
                    callback_data=f"reply:{sender_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "👀 دیدم",
                    callback_data=f"seen:{sender_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "👍",
                    callback_data=f"like:{sender_id}"
                ),
                InlineKeyboardButton(
                    "👎",
                    callback_data=f"dislike:{sender_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚫 بلاک",
                    callback_data=f"block:{sender_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚠️ گزارش",
                    callback_data=f"report:{sender_id}"
                )
            ]
        ]
    )


# =========================================================
# START
# =========================================================

async def start(update, context):
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    uid = user.id

    ensure_user(user)
    context.user_data.clear()

    # لینک ناشناس
    if context.args:
        arg = context.args[0].strip()

        if arg.startswith("link_"):
            target_text = arg[5:]

            if target_text.isdigit():
                target = int(target_text)

                if target == uid:
                    await update.message.reply_text(
                        "❌ نمی‌توانی به خودت پیام بفرستی."
                    )
                    return

                if str(target) not in users:
                    await update.message.reply_text(
                        "❌ این لینک دیگر معتبر نیست."
                    )
                    return

                if is_blocked(target, uid):
                    await update.message.reply_text(
                        "❌ این کاربر شما را بلاک کرده است."
                    )
                    return

                context.user_data["target"] = target
                context.user_data["mode"] = "anonymous"

                await update.message.reply_text(
                    "✏️ پیام ناشناس خودت را بنویس:"
                )
                return

    if settings.get("sleep") and uid != ADMIN_ID:
        await update.message.reply_text(
            "😴 ربات موقتاً در حالت خواب است."
        )
        return

    if uid == ADMIN_ID:
        await update.message.reply_text(
            "👑 پنل مدیریت",
            reply_markup=ADMIN_MENU
        )
        return

    await update.message.reply_text(
        f"👋 سلام {user.first_name or 'کاربر'}!\n\n"
        "📬 به ربات پیام ناشناس خوش آمدی.",
        reply_markup=MAIN_MENU
    )


# =========================================================
# SEND ANONYMOUS
# =========================================================

async def send_anonymous(update, context):
    user = update.effective_user
    uid = user.id

    text = (update.message.text or "").strip()
    target = context.user_data.get("target")

    if not target:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ گیرنده مشخص نیست."
        )
        return

    if target == uid:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ نمی‌توانی به خودت پیام بفرستی."
        )
        return

    if is_blocked(target, uid):
        context.user_data.clear()

        await update.message.reply_text(
            "❌ این کاربر شما را بلاک کرده است."
        )
        return

    if not text:
        await update.message.reply_text(
            "❌ پیام نمی‌تواند خالی باشد."
        )
        return

    if contains_bad_word(text):
        context.user_data.clear()

        await update.message.reply_text(
            "⚠️ پیام به دلیل فیلتر محتوا ارسال نشد."
        )
        return

    keyboard = message_keyboard(uid)

    try:
        sent = await context.bot.send_message(
            chat_id=target,
            text="📩 پیام ناشناس جدید:\n\n" + text,
            reply_markup=keyboard
        )

        set_chat(
            target,
            uid
        )

        save_message(
            sent.message_id,
            uid,
            target
        )

        increase_stat(
            uid,
            "sent"
        )

        increase_stat(
            target,
            "received"
        )

        try:
            await context.bot.send_message(
                chat_id=target,
                text="🔔 یک پیام ناشناس جدید برایت دریافت شد."
            )
        except Exception:
            pass

        await update.message.reply_text(
            "✅ پیام ناشناس ارسال شد.",
            reply_markup=MAIN_MENU
        )

    except Exception as e:
        print("SEND ERROR:", e)

        await update.message.reply_text(
            "❌ ارسال پیام انجام نشد."
        )

    context.user_data.clear()


# =========================================================
# CALLBACK
# =========================================================

async def callback(update, context):
    query = update.callback_query

    await query.answer()

    data = query.data or ""

    if ":" not in data:
        return

    action, value = data.split(":", 1)

    try:
        sender_id = int(value)
    except ValueError:
        sender_id = 0

    current_user = query.from_user.id

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    if action == "reply":
        if is_blocked(current_user, sender_id):
            await query.message.reply_text(
                "❌ این کاربر را بلاک کرده‌ای."
            )
            return

        context.user_data["reply_to"] = sender_id
        context.user_data["mode"] = "reply"

        await query.message.reply_text(
            "✏️ پاسخ خودت را بنویس:"
        )
        return

    # -----------------------------------------------------
    # SEEN
    # -----------------------------------------------------

    if action == "seen":
        if is_blocked(current_user, sender_id):
            await query.message.reply_text(
                "❌ این کاربر را بلاک کرده‌ای."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=sender_id,
                text="👀 گیرنده پیام شما را دید."
            )

            await query.message.reply_text(
                "👀 اطلاع داده شد."
            )

        except Exception as e:
            print("SEEN ERROR:", e)

            await query.message.reply_text(
                "❌ خطا در ارسال اطلاعیه."
            )

        return

    # -----------------------------------------------------
    # LIKE
    # -----------------------------------------------------

    if action == "like":
        info = get_message_info(
            current_user,
            query.message.message_id
        )

        if not info:
            await query.message.reply_text(
                "❌ اطلاعات پیام پیدا نشد."
            )
            return

        likes = info.setdefault("likes", [])
        dislikes = info.setdefault("dislikes", [])

        if current_user in likes:
            await query.message.reply_text(
                "👍 قبلاً لایک کرده‌ای."
            )
            return

        if current_user in dislikes:
            dislikes.remove(current_user)

            increase_stat(
                info["sender"],
                "dislikes",
                -1
            )

        likes.append(current_user)

        increase_stat(
            info["sender"],
            "likes"
        )

        save_message_info(
            current_user,
            query.message.message_id,
            info
        )

        await query.message.reply_text(
            f"👍 ثبت شد.\nتعداد لایک: {len(likes)}"
        )
        return

    # -----------------------------------------------------
    # DISLIKE
    # -----------------------------------------------------

    if action == "dislike":
        info = get_message_info(
            current_user,
            query.message.message_id
        )

        if not info:
            await query.message.reply_text(
                "❌ اطلاعات پیام پیدا نشد."
            )
            return

        likes = info.setdefault("likes", [])
        dislikes = info.setdefault("dislikes", [])

        if current_user in dislikes:
            await query.message.reply_text(
                "👎 قبلاً ثبت کرده‌ای."
            )
            return

        if current_user in likes:
            likes.remove(current_user)

            increase_stat(
                info["sender"],
                "likes",
                -1
            )

        dislikes.append(current_user)

        increase_stat(
            info["sender"],
            "dislikes"
        )

        save_message_info(
            current_user,
            query.message.message_id,
            info
        )

        await query.message.reply_text(
            f"👎 ثبت شد.\nتعداد دیسلایک: {len(dislikes)}"
        )
        return

    # -----------------------------------------------------
    # BLOCK
    # -----------------------------------------------------

    if action == "block":
        block_user(
            current_user,
            sender_id
        )

        await query.message.reply_text(
            "🚫 کاربر بلاک شد."
        )
        return

    # -----------------------------------------------------
    # UNBLOCK
    # -----------------------------------------------------

    if action == "unblock":
        unblock_user(
            current_user,
            sender_id
        )

        await query.message.reply_text(
            "🔓 کاربر آنبلاک شد."
        )
        return

    # -----------------------------------------------------
    # UNBLOCK ALL
    # -----------------------------------------------------

    if action == "unblockall":
        unblock_all(current_user)

        await query.message.reply_text(
            "🔓 همه کاربران آنبلاک شدند."
        )
        return

    # -----------------------------------------------------
    # REPORT
    # -----------------------------------------------------

    if action == "report":
        reports.append(
            {
                "reporter": current_user,
                "reported": sender_id,
            }
        )

        save_json(
            REPORTS_FILE,
            reports
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "⚠️ گزارش جدید\n\n"
                    f"گزارش‌دهنده: {current_user}\n"
                    f"گزارش‌شده: {sender_id}"
                )
            )
        except Exception as e:
            print("REPORT ERROR:", e)

        await query.message.reply_text(
            "⚠️ گزارش برای مدیر ارسال شد."
        )


# =========================================================
# ADMIN
# =========================================================

async def admin_message(update, context):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()

    if uid != ADMIN_ID:
        return False

    # ارسال همگانی
    if context.user_data.get("admin_broadcast"):
        sent = 0

        for user_id in users:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="📢 پیام مدیریت:\n\n" + text
                )
                sent += 1
            except Exception:
                pass

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ پیام برای {sent} کاربر ارسال شد.",
            reply_markup=ADMIN_MENU
        )

        return True

    # ارسال به کانال
    if context.user_data.get("admin_channel"):
        channel = settings.get("channel")

        if not channel:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ ابتدا کانال را تنظیم کن."
            )
            return True

        try:
            await context.bot.send_message(
                chat_id=channel,
                text=text
            )

            await update.message.reply_text(
                "✅ پیام به کانال ارسال شد."
            )

        except Exception as e:
            print("CHANNEL ERROR:", e)

            await update.message.reply_text(
                "❌ ارسال به کانال ناموفق بود."
            )

        context.user_data.clear()
        return True

    # آمار
    if text == "📊 آمار":
        total_sent = sum(
            int(u.get("sent", 0))
            for u in users.values()
        )

        total_received = sum(
            int(u.get("received", 0))
            for u in users.values()
        )

        total_likes = sum(
            int(u.get("likes", 0))
            for u in users.values()
        )

        total_dislikes = sum(
            int(u.get("dislikes", 0))
            for u in users.values()
        )

        await update.message.reply_text(
            "📊 آمار کامل ربات\n\n"
            f"👥 کاربران: {len(users)}\n"
            f"🔗 لینک‌ها: {len(links)}\n"
            f"📨 پیام‌های ارسالی: {total_sent}\n"
            f"📩 پیام‌های دریافتی: {total_received}\n"
            f"👍 لایک‌ها: {total_likes}\n"
            f"👎 دیسلایک‌ها: {total_dislikes}\n"
            f"⚠️ گزارش‌ها: {len(reports)}"
        )

        return True

    # ارسال همگانی
    if text == "📢 ارسال همگانی":
        context.user_data["admin_broadcast"] = True

        await update.message.reply_text(
            "✏️ متن پیام همگانی را بفرست:"
        )
        return True

    # کانال
    if text == "📨 ارسال به کانال":
        if not settings.get("channel"):
            await update.message.reply_text(
                "❌ کانال تنظیم نشده.\n"
                "با /setchannel @channel تنظیمش کن."
            )
            return True

        context.user_data["admin_channel"] = True

        await update.message.reply_text(
            "✏️ متن پیام کانال را بفرست:"
        )
        return True

    # تنظیمات
    if text == "⚙️ تنظیمات":
        filter_status = (
            "فعال"
            if settings.get("filter_enabled")
            else "غیرفعال"
        )

        sleep_status = (
            "فعال"
            if settings.get("sleep")
            else "غیرفعال"
        )

        channel = (
            settings.get("channel")
            or "تنظیم نشده"
        )

        await update.message.reply_text(
            "⚙️ تنظیمات ربات\n\n"
            f"🛡️ فیلتر: {filter_status}\n"
            f"😴 حالت خواب: {sleep_status}\n"
            f"📢 کانال: {channel}\n\n"
            "دستورات:\n"
            "/setchannel @channel\n"
            "/filter on\n"
            "/filter off\n"
            "/sleep\n"
            "/wake"
        )

        return True

    # حالت خواب
    if text == "😴 حالت خواب":
        settings["sleep"] = not settings.get("sleep", False)

        save_json(
            SETTINGS_FILE,
            settings
        )

        status = (
            "فعال 😴"
            if settings["sleep"]
            else "غیرفعال ☀️"
        )

        await update.message.reply_text(
            f"حالت خواب: {status}"
        )
        return True

    # برگشت
    if text == "🔙 منوی کاربر":
        await update.message.reply_text(
            "👤 منوی کاربر",
            reply_markup=MAIN_MENU
        )
        return True

    return False


# =========================================================
# MAIN HANDLE
# =========================================================

async def handle(update, context):
    if not update.message:
        return

    user = update.effective_user
    uid = user.id
    text = (update.message.text or "").strip()

    ensure_user(user)

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if uid == ADMIN_ID:
        if await admin_message(update, context):
            return

    # -----------------------------------------------------
    # SLEEP
    # -----------------------------------------------------

    if settings.get("sleep") and uid != ADMIN_ID:
        await update.message.reply_text(
            "😴 ربات موقتاً در حالت خواب است."
        )
        return

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    if context.user_data.get("mode") == "reply":
        target = context.user_data.get("reply_to")

        if not target:
            context.user_data.clear()
            return

        if is_blocked(target, uid):
            context.user_data.clear()

            await update.message.reply_text(
                "❌ این کاربر شما را بلاک کرده است."
            )
            return

        if contains_bad_word(text):
            context.user_data.clear()

            await update.message.reply_text(
                "⚠️ پیام به دلیل فیلتر محتوا ارسال نشد."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=target,
                text="📨 پاسخ ناشناس:\n\n" + text
            )

            increase_stat(uid, "sent")
            increase_stat(target, "received")

            await update.message.reply_text(
                "✅ پاسخ ارسال شد.",
                reply_markup=MAIN_MENU
            )

        except Exception as e:
            print("REPLY ERROR:", e)

            await update.message.reply_text(
                "❌ ارسال پاسخ ناموفق بود."
            )

        context.user_data.clear()
        return

    # -----------------------------------------------------
    # ANONYMOUS MESSAGE
    # -----------------------------------------------------

    if context.user_data.get("mode") == "anonymous":
        await send_anonymous(
            update,
            context
        )
        return

    # -----------------------------------------------------
    # SEND ANONYMOUS
    # -----------------------------------------------------

    if text == "📩 ارسال ناشناس":
        context.user_data["mode"] = "anonymous_target"

        await update.message.reply_text(
            "🆔 شناسه عددی گیرنده را بفرست:"
        )
        return

    # -----------------------------------------------------
    # TARGET
    # -----------------------------------------------------

    if context.user_data.get("mode") == "anonymous_target":
        try:
            target = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ شناسه باید عددی باشد."
            )
            return

        if target == uid:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ نمی‌توانی به خودت پیام بفرستی."
            )
            return

        if str(target) not in users:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را فعال نکرده است."
            )
            return

        if is_blocked(target, uid):
            context.user_data.clear()

            await update.message.reply_text(
                "❌ این کاربر شما را بلاک کرده است."
            )
            return

        context.user_data["target"] = target
        context.user_data["mode"] = "anonymous"

        await update.message.reply_text(
            "✏️ حالا پیام خودت را بنویس:"
        )
        return

    # -----------------------------------------------------
    # MY LINK
    # -----------------------------------------------------

    if text == "🔗 لینک من":
        bot = await context.bot.get_me()

        link = (
            f"https://t.me/{bot.username}"
            f"?start=link_{uid}"
        )

        links[str(uid)] = {
            "user_id": uid,
            "link": link,
        }

        save_json(
            LINKS_FILE,
            links
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔗 ارسال پیام ناشناس",
                        url=link
                    )
                ]
            ]
        )

        await update.message.reply_text(
            "🔗 لینک ناشناس شما:\n\n"
            f"{link}",
            reply_markup=keyboard
        )
        return

    # -----------------------------------------------------
    # MY ID
    # -----------------------------------------------------

    if text == "🆔 شناسه من":
        await update.message.reply_text(
            f"🆔 شناسه شما:\n\n`{uid}`",
            parse_mode="Markdown"
        )
        return

    # -----------------------------------------------------
    # SEND BY LINK
    # -----------------------------------------------------

    if text == "📤 ارسال با لینک":
        context.user_data["mode"] = "link_send"

        await update.message.reply_text(
            "🔗 لینک ناشناس گیرنده را بفرست:"
        )
        return

    # -----------------------------------------------------
    # LINK SEND
    # -----------------------------------------------------

    if context.user_data.get("mode") == "link_send":
        match = re.search(
            r"(?:start=)?link_(\d+)",
            text
        )

        if not match:
            await update.message.reply_text(
                "❌ لینک نامعتبر است."
            )
            return

        target = int(match.group(1))

        if str(target) not in users:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ این لینک معتبر نیست."
            )
            return

        if target == uid:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ نمی‌توانی به خودت پیام بفرستی."
            )
            return

        if is_blocked(target, uid):
            context.user_data.clear()

            await update.message.reply_text(
                "❌ این کاربر شما را بلاک کرده است."
            )
            return

        context.user_data["target"] = target
        context.user_data["mode"] = "anonymous"

        await update.message.reply_text(
            "✏️ پیام ناشناس خودت را بنویس:"
        )
        return

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------

    if text == "👤 پروفایل":
        data = users.get(
            str(uid),
            {}
        )

        username = data.get("username")
        username_text = (
            f"@{username}"
            if username
            else "ندارد"
        )

        await update.message.reply_text(
            "👤 پروفایل شما\n\n"
            f"📛 نام: {data.get('display_name', 'کاربر')}\n"
            f"🆔 شناسه: {uid}\n"
            f"🔗 یوزرنیم: {username_text}\n\n"
            f"📤 پیام‌های ارسالی: {data.get('sent', 0)}\n"
            f"📥 پیام‌های دریافتی: {data.get('received', 0)}\n"
            f"👍 لایک‌ها: {data.get('likes', 0)}\n"
            f"👎 دیسلایک‌ها: {data.get('dislikes', 0)}"
        )
        return

    # -----------------------------------------------------
    # USER STATS
    # -----------------------------------------------------

    if text == "📊 آمار من":
        data = users.get(
            str(uid),
            {}
        )

        await update.message.reply_text(
            "📊 آمار شما\n\n"
            f"📤 ارسال شده: {data.get('sent', 0)}\n"
            f"📥 دریافت شده: {data.get('received', 0)}\n"
            f"👍 لایک: {data.get('likes', 0)}\n"
            f"👎 دیسلایک: {data.get('dislikes', 0)}"
        )
        return

    # -----------------------------------------------------
    # BLOCK LIST
    # -----------------------------------------------------

    if text == "📋 بلاک‌ها":
        my_blocks = blocks.get(
            str(uid),
            []
        )

        if not my_blocks:
            await update.message.reply_text(
                "📋 لیست بلاک خالی است."
            )
            return

        lines = []
        rows = []

        for blocked_id in my_blocks:
            name = get_display_name(
                blocked_id
            )

            lines.append(
                f"• {name} — {blocked_id}"
            )

            rows.append(
                [
                    InlineKeyboardButton(
                        f"🔓 آنبلاک {blocked_id}",
                        callback_data=f"unblock:{blocked_id}"
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "🔓 آنبلاک همه",
                    callback_data="unblockall:0"
                )
            ]
        )

        await update.message.reply_text(
            "🚫 لیست بلاک شما:\n\n"
            + "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    # -----------------------------------------------------
    # SEEN
    # -----------------------------------------------------

    if text == "👀 پیام را دیدم":
        sender = get_last_sender(uid)

        if not sender:
            await update.message.reply_text(
                "❌ پیامی برای تأیید وجود ندارد."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=sender,
                text="👀 گیرنده پیام شما را دید."
            )

            await update.message.reply_text(
                "👀 اطلاع داده شد."
            )

        except Exception as e:
            print("SEEN ERROR:", e)

            await update.message.reply_text(
                "❌ خطا در ارسال اطلاعیه."
            )

        return

    # -----------------------------------------------------
    # REPORT
    # -----------------------------------------------------

    if text == "🚫 گزارش تخلف":
        context.user_data["mode"] = "report_user"

        await update.message.reply_text(
            "🆔 شناسه عددی کاربر متخلف را بفرست:"
        )
        return

    # -----------------------------------------------------
    # REPORT USER
    # -----------------------------------------------------

    if context.user_data.get("mode") == "report_user":
        try:
            reported = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ شناسه باید عددی باشد."
            )
            return

        if reported == uid:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ نمی‌توانی خودت را گزارش کنی."
            )
            return

        reports.append(
            {
                "reporter": uid,
                "reported": reported,
            }
        )

        save_json(
            REPORTS_FILE,
            reports
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "⚠️ گزارش جدید\n\n"
                    f"گزارش‌دهنده: {uid}\n"
                    f"گزارش‌شده: {reported}"
                )
            )
        except Exception as e:
            print("REPORT ERROR:", e)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ گزارش شما ثبت شد.",
            reply_markup=MAIN_MENU
        )
        return

    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    await update.message.reply_text(
        "❌ از دکمه‌های منو استفاده کن.",
        reply_markup=MAIN_MENU
    )


# =========================================================
# COMMANDS
# =========================================================

async def setchannel(update, context):
    if (
        not update.effective_user
        or update.effective_user.id != ADMIN_ID
    ):
        return

    if not context.args:
        await update.message.reply_text(
            "مثال:\n/setchannel @my_channel"
        )
        return

    channel = context.args[0].strip()

    settings["channel"] = channel

    save_json(
        SETTINGS_FILE,
        settings
    )

    await update.message.reply_text(
        f"✅ کانال تنظیم شد:\n{channel}"
    )


async def filter_command(update, context):
    if (
        not update.effective_user
        or update.effective_user.id != ADMIN_ID
    ):
        return

    if not context.args:
        await update.message.reply_text(
            "مثال:\n/filter on\n/filter off"
        )
        return

    status = context.args[0].lower().strip()

    if status == "on":
        settings["filter_enabled"] = True

        save_json(
            SETTINGS_FILE,
            settings
        )

        await update.message.reply_text(
            "🛡️ فیلتر محتوا فعال شد."
        )

    elif status == "off":
        settings["filter_enabled"] = False

        save_json(
            SETTINGS_FILE,
            settings
        )

        await update.message.reply_text(
            "🛡️ فیلتر محتوا غیرفعال شد."
        )

    else:
        await update.message.reply_text(
            "❌ مقدار نامعتبر. از on یا off استفاده کن."
        )


async def sleep_command(update, context):
    if (
        not update.effective_user
        or update.effective_user.id != ADMIN_ID
    ):
        return

    settings["sleep"] = True

    save_json(
        SETTINGS_FILE,
        settings
    )

    await update.message.reply_text(
        "😴 حالت خواب فعال شد."
    )


async def wake_command(update, context):
    if (
        not update.effective_user
        or update.effective_user.id != ADMIN_ID
    ):
        return

    settings["sleep"] = False

    save_json(
        SETTINGS_FILE,
        settings
    )

    await update.message.reply_text(
        "☀️ حالت خواب غیرفعال شد."
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(update, context):
    print(
        "ERROR:",
        context.error
    )


# =========================================================
# RUN
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN تنظیم نشده است. "
        "در Railway → Variables مقدار BOT_TOKEN را اضافه کن."
    )


app = (
    Application
    .builder()
    .token(TOKEN)
    .build()
)


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(
    CommandHandler(
        "setchannel",
        setchannel
    )
)

app.add_handler(
    CommandHandler(
        "filter",
        filter_command
    )
)

app.add_handler(
    CommandHandler(
        "sleep",
        sleep_command
    )
)

app.add_handler(
    CommandHandler(
        "wake",
        wake_command
    )
)

app.add_handler(
    CallbackQueryHandler(
        callback
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle
    )
)

app.add_error_handler(
    error_handler
)

print("✅ ربات V4 روشن شد!")

app.run_polling()
