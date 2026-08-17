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
        "filter_enabled": False
    }
)


# =========================================================
# MENUS
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📩 ارسال ناشناس"],
        ["🔗 لینک من", "🆔 شناسه من"],
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
            "display_name": user.first_name or "کاربر"
        }

        save_json(
            USERS_FILE,
            users
        )

    return users[uid]


def is_blocked(blocker, target):
    return str(target) in blocks.get(
        str(blocker),
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

    return users.get(
        str(user_id),
        {}
    ).get(
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

    bad_words = [
        "spamword1",
        "spamword2"
    ]

    lower = text.lower()

    for word in bad_words:

        if word in lower:
            return True

    return False


def save_message(
    message_id,
    sender,
    receiver
):

    messages[str(message_id)] = {
        "sender": sender,
        "receiver": receiver
    }

    save_json(
        MESSAGES_FILE,
        messages
    )


def get_message_info(message_id):

    return messages.get(
        str(message_id)
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

    if not update.message:
        return

    user = update.effective_user

    uid = user.id

    ensure_user(user)

    context.user_data.clear()

    # =====================================================
    # LINK
    # =====================================================

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

                context.user_data[
                    "target"
                ] = target_id

                context.user_data[
                    "mode"
                ] = "anonymous"

                await update.message.reply_text(
                    "✏️ پیام ناشناس خودت را بنویس:"
                )

                return

    # =====================================================
    # SLEEP
    # =====================================================

    if settings.get(
        "sleep"
    ) and uid != ADMIN_ID:

        await update.message.reply_text(
            "😴 ربات موقتاً در حالت خواب است."
        )

        return

    # =====================================================
    # ADMIN
    # =====================================================

    if uid == ADMIN_ID:

        await update.message.reply_text(
            "👑 پنل مدیریت",
            reply_markup=ADMIN_MENU
        )

        return

    # =====================================================
    # USER
    # =====================================================

    await update.message.reply_text(
        f"👋 سلام {user.first_name or 'کاربر'}!\n\n"
        "به ربات پیام ناشناس خوش آمدی.",
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

    if contains_bad_word(
        text
    ):

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
    update,
    context
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

        sender_id = int(
            value
        )

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

        context.user_data[
            "reply_to"
        ] = sender_id

        context.user_data[
            "mode"
        ] = "reply"

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

        await query.message.reply_text(
            "👍 واکنش شما ثبت شد."
        )

        return

    # =====================================================
    # DISLIKE
    # =====================================================

    if action == "dislike":

        await query.message.reply_text(
            "👎 واکنش شما ثبت شد."
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
                    text=(
                        "📢 پیام مدیریت:\n\n"
                        + text
                    )
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

        await update.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {len(users)}\n"
            f"🔗 لینک‌ها: {len(links)}\n"
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
                "با /setchannel کانال را تنظیم کن."
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

        status = (
            "فعال"
            if settings.get(
                "filter_enabled"
            )
            else "غیرفعال"
        )

        channel = (
            settings.get(
                "channel"
            )
            or "تنظیم نشده"
        )

        sleep = (
            "فعال"
            if settings.get(
                "sleep"
            )
            else "غیرفعال"
        )

        await update.message.reply_text(
            "⚙️ تنظیمات\n\n"
            f"فیلتر: {status}\n"
            f"حالت خواب: {sleep}\n"
            f"کانال: {channel}\n\n"
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
            "فعال"
            if settings.get(
                "sleep"
            )
            else "غیرفعال"
        )

        await update.message.reply_text(
            f"😴 حالت خواب: {status}"
        )

        return True

    # =====================================================
    # BACK
    # =====================================================

    if text == "🔙 منوی کاربر":

        await update.message.reply_text(
            "👤 منوی کاربر",
            reply_markup=MAIN_MENU
        )

        return True

    return False


# =========================================================
# HANDLE
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

    # =====================================================
    # REPLY
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "reply":

        target = context.user_data.get(
            "reply_to"
        )

        if target:

            if is_blocked(
                target,
                uid
            ):

                await update.message.reply_text(
                    "❌ این کاربر شما را بلاک کرده است."
                )

                context.user_data.clear()

                return

            try:

                await context.bot.send_message(
                    chat_id=target,
                    text="📨 پاسخ:\n\n" + text
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
    # SEND TO
    # =====================================================

    if text == "📩 ارسال ناشناس":

        context.user_data[
            "mode"
        ] = "anonymous_target"

        await update.message.reply_text(
            "🆔 شناسه عددی گیرنده را بفرست:"
        )

        return

    # =====================================================
    # MY LINK
    # =====================================================

    if text == "🔗 لینک من":

        bot = await context.bot.get_me()

        link = (
            f"https://t.me/{bot.username}?start=link_{uid}"
        )

        await update.message.reply_text(
            f"🔗 لینک ناشناس شما:\n\n{link}"
        )

        return

    # =====================================================
    # MY ID
    # =====================================================

    if text == "🆔 شناسه من":

        await update.message.reply_text(
            f"🆔 شناسه شما:\n\n`{uid}`",
            parse_mode="Markdown"
        )

        return

    # =====================================================
    # SEND BY LINK
    # =====================================================

    if text == "📤 ارسال با لینک":

        await update.message.reply_text(
            "✏️ لینک ناشناس گیرنده را بفرست:"
        )

        context.user_data[
            "mode"
        ] = "link_send"

        return

    # =====================================================
    # BLOCK LIST
    # =====================================================

    if text == "📋 بلاک‌ها":

        my_blocks = blocks.get(
            str(uid),
            []
        )

        if not my_blocks:

            await update.message.reply_text(
                "🚫 لیست بلاک شما خالی است."
            )

            return

        result = "🚫 لیست بلاک شما:\n\n"

        for b in my_blocks:

            name = get_display_name(
                b
            )

            result += (
                f"• {name} (ID: {b})\n"
            )

        await update.message.reply_text(
            result
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

            print(
                "SEEN ERROR:",
                e
            )

            await update.message.reply_text(
                "❌ خطا در ارسال اطلاعیه."
            )

        return

    # =====================================================
    # REPORT
    # =====================================================

    if text == "🚫 گزارش تخلف":

        await update.message.reply_text(
            "✏️ شناسه عددی کاربر متخلف را بفرست:"
        )

        context.user_data[
            "mode"
        ] = "report_user"

        return

    # =====================================================
    # TARGET
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "anonymous_target":

        try:

            target = int(
                text
            )

        except:

            await update.message.reply_text(
                "❌ شناسه باید عددی باشد."
            )

            context.user_data.clear()

            return

        if target == uid:

            await update.message.reply_text(
                "❌ نمی‌توانی به خودت پیام بفرستی."
            )

            context.user_data.clear()

            return

        if str(target) not in users:

            await update.message.reply_text(
                "❌ این کاربر در ربات ثبت نشده است."
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

        context.user_data[
            "target"
        ] = target

        context.user_data[
            "mode"
        ] = "anonymous"

        await update.message.reply_text(
            "✏️ پیام ناشناس خودت را بنویس:"
        )

        return

    # =====================================================
    # LINK SEND
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "link_send":

        match = re.search(
            r"link_(\d+)",
            text
        )

        if not match:

            await update.message.reply_text(
                "❌ لینک نامعتبر است."
            )

            context.user_data.clear()

            return

        target = int(
            match.group(1)
        )

        if str(target) not in users:

            await update.message.reply_text(
                "❌ این لینک معتبر نیست."
            )

            context.user_data.clear()

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

        context.user_data[
            "target"
        ] = target

        context.user_data[
            "mode"
        ] = "anonymous"

        await update.message.reply_text(
            "✏️ پیام ناشناس خودت را بنویس:"
        )

        return

    # =====================================================
    # REPORT USER
    # =====================================================

    if context.user_data.get(
        "mode"
    ) == "report_user":

        try:

            reported = int(
                text
            )

        except:

            await update.message.reply_text(
                "❌ شناسه باید عددی باشد."
            )

            context.user_data.clear()

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
                chat_id=ADMIN_ID,
                text=(
                    f"⚠️ گزارش جدید\n\n"
                    f"گزارش‌دهنده: {uid}\n"
                    f"گزارش‌شده: {reported}"
                )
            )

        except:
            pass

        await update.message.reply_text(
            "✅ گزارش شما ثبت شد."
        )

        context.user_data.clear()

        return

    # =====================================================
    # DEFAULT
    # =====================================================

    await update.message.reply_text(
        "❌ از دکمه‌های منو استفاده کن.",
        reply_markup=MAIN_MENU
    )


# =========================================================
# COMMANDS
# =========================================================

async def setchannel(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "مثال:\n/setchannel @my_channel"
        )

        return

    channel = context.args[0]

    settings["channel"] = channel

    save_json(
        SETTINGS_FILE,
        settings
    )

    await update.message.reply_text(
        f"✅ کانال تنظیم شد:\n{channel}"
    )


async def filter_command(
    update,
    context
):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "مثال:\n/filter on\n/filter off"
        )

        return

    status = context.args[0].lower()

    if status == "on":

        settings["filter_enabled"] = True

        await update.message.reply_text(
            "🔞 فیلتر محتوا فعال شد."
        )

    elif status == "off":

        settings["filter_enabled"] = False

        await update.message.reply_text(
            "🔞 فیلتر محتوا غیرفعال شد."
        )

    else:

        await update.message.reply_text(
            "❌ مقدار نامعتبر. از on یا off استفاده کن."
        )

        return

    save_json(
        SETTINGS_FILE,
        settings
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "ERROR:",
        context.error
    )


# =========================================================
# RUN
# =========================================================

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

print("✅ ربات V3 روشن شد!")

app.run_polling()
