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

TOKEN = "8847629801:AAGWhNJcs2dEXa4fSm2ygqw0gzkdl436iOA"

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
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
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
        "bad_words": [
            "spamword1",
            "spamword2"
        ]
    }
)


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
        ["🚫 گزارش تخلف"]
    ],
    resize_keyboard=True
)


ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["📊 آمار"],
        ["📢 ارسال همگانی"],
        ["📨 ارسال به کانال"],
        ["⚙️ تنظیمات"],
        ["😴 حالت خواب"],
        ["🔙 منوی کاربر"]
    ],
    resize_keyboard=True
)


# =========================================================
# HELPERS
# =========================================================

def ensure_user(user):

    uid = str(user.id)

    if uid not in users:

        users[uid] = {
            "id": user.id,
            "first_name": user.first_name or "",
            "username": user.username or "",
            "display_name": user.first_name or "کاربر",

            # Phase 1 statistics
            "sent": 0,
            "received": 0,
            "likes": 0,
            "dislikes": 0
        }

        save_json(
            USERS_FILE,
            users
        )

    else:

        # اطلاعات کاربر را به‌روز می‌کنیم
        users[uid]["first_name"] = user.first_name or ""
        users[uid]["username"] = user.username or ""

        if "display_name" not in users[uid]:
            users[uid]["display_name"] = (
                user.first_name or "کاربر"
            )

        if "sent" not in users[uid]:
            users[uid]["sent"] = 0

        if "received" not in users[uid]:
            users[uid]["received"] = 0

        if "likes" not in users[uid]:
            users[uid]["likes"] = 0

        if "dislikes" not in users[uid]:
            users[uid]["dislikes"] = 0

    return users[uid]


def increase_stat(user_id, stat):

    uid = str(user_id)

    if uid not in users:
        return

    if stat not in users[uid]:
        users[uid][stat] = 0

    users[uid][stat] += 1

    save_json(
        USERS_FILE,
        users
    )


def is_blocked(blocker, target):

    blocker = str(blocker)
    target = str(target)

    return target in blocks.get(
        blocker,
        []
    )


def block_user(blocker, target):

    blocker = str(blocker)
    target = str(target)

    if blocker not in blocks:
        blocks[blocker] = []

    if target not in blocks[blocker]:
        blocks[blocker].append(target)

    save_json(
        BLOCKS_FILE,
        blocks
    )


def unblock_user(blocker, target):

    blocker = str(blocker)
    target = str(target)

    if blocker in blocks:

        if target in blocks[blocker]:

            blocks[blocker].remove(target)

    save_json(
        BLOCKS_FILE,
        blocks
    )


def get_display_name(user_id):

    data = users.get(
        str(user_id),
        {}
    )

    return data.get(
        "display_name",
        "کاربر"
    )


def set_chat(receiver, sender):

    chats[str(receiver)] = {
        "sender": sender
    }

    save_json(
        CHATS_FILE,
        chats
    )


def get_last_sender(receiver):

    data = chats.get(
        str(receiver)
    )

    if not data:
        return None

    return data.get(
        "sender"
    )


def contains_bad_word(text):

    if not settings.get(
        "filter_enabled"
    ):
        return False

    bad_words = settings.get(
        "bad_words",
        []
    )

    lower = text.lower()

    for word in bad_words:

        if word.lower() in lower:
            return True

    return False


def message_key(chat_id, message_id):

    return f"{chat_id}:{message_id}"


def save_message(
    message_id,
    sender,
    receiver
):

    key = message_key(
        receiver,
        message_id
    )

    messages[key] = {
        "message_id": message_id,
        "sender": sender,
        "receiver": receiver,
        "likes": [],
        "dislikes": []
    }

    save_json(
        MESSAGES_FILE,
        messages
    )

    return key


def get_message_info(
    chat_id,
    message_id
):

    key = message_key(
        chat_id,
        message_id
    )

    return messages.get(
        key
    )


def set_message_info(
    chat_id,
    message_id,
    data
):

    key = message_key(
        chat_id,
        message_id
    )

    messages[key] = data

    save_json(
        MESSAGES_FILE,
        messages
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    user = update.effective_user
    uid = user.id

    ensure_user(user)

    context.user_data.clear()

    # -------------------------
    # START LINK
    # -------------------------

    if context.args:

        arg = context.args[0]

        if arg.startswith("link_"):

            target_id = arg.replace(
                "link_",
                ""
            )

            if target_id.isdigit():

                target_id = int(
                    target_id
                )

                if target_id == uid:

                    await update.message.reply_text(
                        "❌ نمی‌توانی به خودت پیام بفرستی."
                    )

                    return

                if str(target_id) not in users:

                    await update.message.reply_text(
                        "❌ این لینک دیگر معتبر نیست."
                    )

                    return

                if is_blocked(
                    target_id,
                    uid
                ):

                    await update.message.reply_text(
                        "❌ این کاربر شما را بلاک کرده است."
                    )

                    return

                context.user_data["target"] = target_id
                context.user_data["mode"] = "anonymous"

                await update.message.reply_text(
                    "✏️ پیام ناشناس خودت را بنویس:"
                )

                return

    # -------------------------
    # SLEEP
    # -------------------------

    if (
        settings.get("sleep")
        and uid != ADMIN_ID
    ):

        await update.message.reply_text(
            "😴 ربات موقتاً در حالت خواب است."
        )

        return

    # -------------------------
    # ADMIN
    # -------------------------

    if uid == ADMIN_ID:

        await update.message.reply_text(
            "👑 پنل مدیریت",
            reply_markup=ADMIN_MENU
        )

        return

    # -------------------------
    # USER
    # -------------------------

    await update.message.reply_text(
        f"👋 سلام {user.first_name or 'کاربر'}!\n\n"
        "📬 به Navid's Mailbox خوش آمدی.\n"
        "اینجا می‌توانی پیام ناشناس دریافت و ارسال کنی.",
        reply_markup=MAIN_MENU
    )


# =========================================================
# SEND ANONYMOUS
# =========================================================

async def send_anonymous(
    update,
    context
):

    user = update.effective_user
    uid = user.id

    text = update.message.text

    target = context.user_data.get(
        "target"
    )

    if not target:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ گیرنده مشخص نیست."
        )

        return

    if target == uid:

        await update.message.reply_text(
            "❌ نمی‌توانی به خودت پیام بفرستی."
        )

        context.user_data.clear()

        return

    if is_blocked(
        target,
        uid
    ):

        await update.message.reply_text(
            "❌ این کاربر شما را بلاک کرده است."
        )

        context.user_data.clear()

        return

    if contains_bad_word(text):

        await update.message.reply_text(
            "⚠️ پیام به دلیل فیلتر محتوا ارسال نشد."
        )

        context.user_data.clear()

        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📨 پاسخ",
                    callback_data=f"reply:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    "👀 دیدم",
                    callback_data=f"seen:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    "👍",
                    callback_data=f"like:{uid}"
                ),
                InlineKeyboardButton(
                    "👎",
                    callback_data=f"dislike:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚫 بلاک",
                    callback_data=f"block:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚠️ گزارش",
                    callback_data=f"report:{uid}"
                )
            ]
        ]
    )

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

        # اعلان ساده برای گیرنده
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

        print(
            "SEND ERROR:",
            e
        )

        await update.message.reply_text(
            "❌ ارسال پیام انجام نشد."
        )

    context.user_data.clear()


# =========================================================
# CALLBACK
# =========================================================

async def callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if ":" not in data:
        return

    action, value = data.split(
        ":",
        1
    )

    try:

        sender_id = int(value)

    except Exception:

        return

    current_user = query.from_user.id

    # =====================================================
    # REPLY
    # =====================================================

    if action == "reply":

        if is_blocked(
            current_user,
            sender_id
        ):

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

    # =====================================================
    # SEEN
    # =====================================================

    if action == "seen":

        if is_blocked(
            current_user,
            sender_id
        ):

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

            print(
                "SEEN ERROR:",
                e
            )

            await query.message.reply_text(
                "❌ خطا در ارسال اطلاعیه."
            )

        return

    # =====================================================
    # LIKE
    # =====================================================

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

        likes = info.setdefault(
            "likes",
            []
        )

        dislikes = info.setdefault(
            "dislikes",
            []
        )

        if current_user in likes:

            await query.message.reply_text(
                "👍 قبلاً لایک کرده‌ای."
            )

            return

        if current_user in dislikes:

            dislikes.remove(
                current_user
            )

            sender = info.get(
                "receiver"
            )

            if str(sender) in users:
                users[str(sender)]["dislikes"] = max(
                    0,
                    users[str(sender)].get("dislikes", 0) - 1
                )

        likes.append(
            current_user
        )

        sender = info.get(
            "sender"
        )

        if str(sender) in users:

            users[str(sender)]["likes"] = (
                users[str(sender)].get("likes", 0) + 1
            )

        set_message_info(
            current_user,
            query.message.message_id,
            info
        )

        save_json(
            USERS_FILE,
            users
        )

        await query.message.reply_text(
            f"👍 ثبت شد.\n"
            f"تعداد لایک: {len(likes)}"
        )

        return

    # =====================================================
    # DISLIKE
    # =====================================================

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

        likes = info.setdefault(
            "likes",
            []
        )

        dislikes = info.setdefault(
            "dislikes",
            []
        )

        if current_user in dislikes:

            await query.message.reply_text(
                "👎 قبلاً ثبت کرده‌ای."
            )

            return

        if current_user in likes:

            likes.remove(
                current_user
            )

            sender = info.get(
                "sender"
            )

            if str(sender) in users:

                users[str(sender)]["likes"] = max(
                    0,
                    users[str(sender)].get("likes", 0) - 1
                )

        dislikes.append(
            current_user
        )

        sender = info.get(
            "sender"
        )

        if str(sender) in users:

            users[str(sender)]["dislikes"] = (
                users[str(sender)].get("dislikes", 0) + 1
            )

        set_message_info(
            current_user,
            query.message.message_id,
            info
        )

        save_json(
            USERS_FILE,
            users
        )

        await query.message.reply_text(
            f"👎 ثبت شد.\n"
            f"تعداد دیسلایک: {len(dislikes)}"
        )

        return

    # =====================================================
    # BLOCK
    # =====================================================

    if action == "block":

        block_user(
            current_user,
            sender_id
        )

        await query.message.reply_text(
            "🚫 کاربر بلاک شد."
        )

        return

    # =====================================================
    # REPORT
    # =====================================================

    if action == "report":

        reports.append(
            {
                "reporter": current_user,
                "reported": sender_id
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

        except Exception:
            pass

        await query.message.reply_text(
            "⚠️ گزارش برای مدیر ارسال شد."
        )

        return

    # =====================================================
    # UNBLOCK
    # =====================================================

    if action == "unblock":

        unblock_user(
            current_user,
            sender_id
        )

        await query.message.reply_text(
            "🔓 کاربر آنبلاک شد."
        )

        return


# =========================================================
# ADMIN
# =========================================================

async def admin_message(
    update,
    context
):

    user = update.effective_user
    uid = user.id

    text = update.message.text

    if uid != ADMIN_ID:
        return False

    # =====================================================
    # BROADCAST
    # =====================================================

    if context.user_data.get(
        "admin_broadcast"
    ):

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

    # =====================================================
    # CHANNEL
    # =====================================================

    if context.user_data.get(
        "admin_channel"
    ):

        channel = settings.get(
            "channel"
        )

        if not channel:

            await update.message.reply_text(
                "❌ ابتدا کانال را تنظیم کن."
            )

            context.user_data.clear()

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

            print(
                "CHANNEL ERROR:",
                e
            )

            await update.message.reply_text(
                "❌ ارسال به کانال ناموفق بود."
            )

        context.user_data.clear()

        return True

    # =====================================================
    # STATS
    # =====================================================

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

    # =====================================================
    # BROADCAST BUTTON
    # =====================================================

    if text == "📢 ارسال همگانی":

        context.user_data[
            "admin_broadcast"
        ] = True

        await update.message.reply_text(
            "✏️ متن پیام همگانی را بفرست:"
        )

        return True

    # =====================================================
    # CHANNEL BUTTON
    # =====================================================

    if text == "📨 ارسال به کانال":

        if not settings.get(
            "channel"
        ):

            await update.message.reply_text(
                "❌ کانال تنظیم نشده.\n"
                "با /setchannel @channel تنظیمش کن."
            )

            return True

        context.user_data[
            "admin_channel"
        ] = True

        await update.message.reply_text(
            "✏️ متن پیام کانال را بفرست:"
        )

        return True

    # =====================================================
    # SETTINGS
    # =====================================================

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
            f"😴 خواب: {sleep_status}\n"
            f"📢 کانال: {channel}\n\n"
            "دستورات:\n"
            "/sleep\n"
            "/wake\n"
            "/filter_on\n"
            "/filter_off\n"
            "/setchannel @channel"
        )

        return True

    # =====================================================
    # SLEEP
    # =====================================================

    if text == "😴 حالت خواب":

        settings["sleep"] = not settings.get(
            "sleep"
        )

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

    # =====================================================
    # USER MENU
    # =====================================================

    if text == "🔙 منوی کاربر":

        await update.message.reply_text(
            "منوی کاربر",
            reply_markup=MAIN_MENU
        )

        return True

    return False


# =========================================================
# MAIN HANDLER
# =========================================================

async def handle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    user = update.effective_user
    uid = user.id

    text = update.message.text

    ensure_user(user)

    # =====================================================
    # ADMIN
    # =====================================================

    if uid == ADMIN_ID:

        if await admin_message(
            update,
            context
        ):
            return

        # پاسخ مدیر
        if context.user_data.get(
            "mode"
        ) == "reply":

            target = context.user_data.get(
                "reply_to"
            )

            if target:

                try:

                    await context.bot.send_message(
                        chat_id=target,
                        text="📨 پاسخ ناشناس:\n\n" + text
                    )

                    increase_stat(
                        uid,
                        "sent"
                    )

                    increase_stat(
                        target,
                        "received"
                    )

                    await update.message.reply_text(
                        "✅ پاسخ ارسال شد."
                    )

                except Exception as e:

                    print(
                        "REPLY ERROR:",
                        e
                    )

                    await update.message.reply_text(
                        "❌ ارسال پاسخ ناموفق بود."
                    )

            context.user_data.clear()

            return

    # =====================================================
    # SLEEP
    # =====================================================

    if (
        settings.get("sleep")
        and uid != ADMIN_ID
    ):

        await update.message.reply_text(
            "😴 ربات موقتاً خاموش است."
        )

        return

    # =====================================================
    # ANONYMOUS
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "anonymous":

        await send_anonymous(
            update,
            context
        )

        return

    # =====================================================
    # REPLY
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "reply":

        target = context.user_data.get(
            "reply_to"
        )

        if not target:

            context.user_data.clear()

            return

        if is_blocked(
            uid,
            target
        ):

            await update.message.reply_text(
                "❌ این کاربر را بلاک کرده‌ای."
            )

            context.user_data.clear()

            return

        try:

            await context.bot.send_message(
                chat_id=target,
                text="📨 پاسخ ناشناس:\n\n" + text
            )

            increase_stat(
                uid,
                "sent"
            )

            increase_stat(
                target,
                "received"
            )

            await update.message.reply_text(
                "✅ پاسخ ارسال شد."
            )

        except Exception as e:

            print(
                "REPLY ERROR:",
                e
            )

            await update.message.reply_text(
                "❌ ارسال پاسخ ناموفق بود."
            )

        context.user_data.clear()

        return

    # =====================================================
    # SEND ANONYMOUS
    # =====================================================

    if text == "📩 ارسال ناشناس":

        context.user_data[
            "mode"
        ] = "target"

        await update.message.reply_text(
            "🆔 شناسه عددی کاربر را بفرست:"
        )

        return

    # =====================================================
    # TARGET
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "target":

        try:

            target = int(text)

        except Exception:

            await update.message.reply_text(
                "❌ شناسه باید عددی باشد."
            )

            return

        if target == uid:

            await update.message.reply_text(
                "❌ نمی‌توانی به خودت پیام بفرستی."
            )

            return

        if str(target) not in users:

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را فعال نکرده است."
            )

            return

        if is_blocked(
            target,
            uid
        ):

            await update.message.reply_text(
                "❌ این کاربر شما را بلاک کرده است."
            )

            return

        context.user_data[
            "target"
        ] = target

        context.user_data[
            "mode"
        ] = "anonymous"

        await update.message.reply_text(
            "✏️ حالا پیام خودت را بنویس:"
        )

        return

    # =====================================================
    # PROFILE
    # =====================================================

    if text == "👤 پروفایل":

        data = users.get(
            str(uid),
            {}
        )

        username = data.get(
            "username"
        )

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

    # =====================================================
    # USER STATS
    # =====================================================

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

    # =====================================================
    # MY ID
    # =====================================================

    if text == "🆔 شناسه من":

        await update.message.reply_text(
            f"🆔 شناسه اختصاصی شما:\n\n{uid}"
        )

        return

    # =====================================================
    # MY LINK
    # =====================================================

    if text == "🔗 لینک من":

        bot = await context.bot.get_me()

        link = (
            f"https://t.me/{bot.username}"
            f"?start=link_{uid}"
        )

        links[str(uid)] = uid

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

    # =====================================================
    # SEND WITH LINK
    # =====================================================

    if text == "📤 ارسال با لینک":

        context.user_data[
            "mode"
        ] = "link"

        await update.message.reply_text(
            "🔗 لینک ناشناس را بفرست:"
        )

        return

    # =====================================================
    # LINK
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "link":

        match = re.search(
            r"start=link_(\d+)",
            text
        )

        if not match:

            await update.message.reply_text(
                "❌ لینک نامعتبر است."
            )

            return

        target = int(
            match.group(1)
        )

        if str(target) not in users:

            await update.message.reply_text(
                "❌ این لینک معتبر نیست."
            )

            return

        if target == uid:

            await update.message.reply_text(
                "❌ این لینک متعلق به خودت است."
            )

            return

        if is_blocked(
            target,
            uid
        ):

            await update.message.reply_text(
                "❌ این کاربر شما را بلاک کرده است."
            )

            return

        context.user_data[
            "target"
        ] = target

        context.user_data[
            "mode"
        ] = "anonymous"

        await update.message.reply_text(
            "✏️ پیام ناشناس را بنویس:"
        )

        return

    # =====================================================
    # SEEN
    # =====================================================

    if text == "👀 پیام را دیدم":

        sender = get_last_sender(
            uid
        )

        if not sender:

            await update.message.reply_text(
                "❌ پیام قبلی پیدا نشد."
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

        except Exception:

            await update.message.reply_text(
                "❌ خطا."
            )

        return

    # =====================================================
    # BLOCK LIST
    # =====================================================

    if text == "📋 بلاک‌ها":

        blocked = blocks.get(
            str(uid),
            []
        )

        if not blocked:

            await update.message.reply_text(
                "📋 لیست بلاک خالی است."
            )

            return

        lines = []

        keyboard_rows = []

        for i, blocked_id in enumerate(
            blocked,
            start=1
        ):

            lines.append(
                f"{i}. {blocked_id}"
            )

            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        f"🔓 آنبلاک {blocked_id}",
                        callback_data=f"unblock:{blocked_id}"
                    )
                ]
            )

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "🔓 آنبلاک همه",
                    callback_data="unblockall:0"
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            keyboard_rows
        )

        await update.message.reply_text(
            "🚫 بلاکی‌های شما:\n\n"
            + "\n".join(lines),
            reply_markup=keyboard
        )

        return

    # =====================================================
    # REPORT
    # =====================================================

    if text == "🚫 گزارش تخلف":

        context.user_data[
            "mode"
        ] = "report"

        await update.message.reply_text(
            "🆔 شناسه کاربری که می‌خواهی گزارش کنی را بفرست:"
        )

        return

    # =====================================================
    # REPORT PROCESS
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "report":

        try:

            reported = int(text)

        except Exception:

            await update.message.reply_text(
                "❌ شناسه نامعتبر است."
            )

            return

        if reported == uid:

            await update.message.reply_text(
                "❌ نمی‌توانی خودت را گزارش کنی."
            )

            context.user_data.clear()

            return

        reports.append(
            {
                "reporter": uid,
                "reported": reported
            }
        )

        save_json(
            REPORTS_FILE,
            reports
        )

        try:

            await context.bot.send_message(
                ADMIN_ID,
                "⚠️ گزارش جدید\n\n"
                f"گزارش‌
