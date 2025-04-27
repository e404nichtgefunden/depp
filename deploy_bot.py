import os
import sys
import json
import asyncio
import subprocess
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === CONFIG
MASTER_BOT_TOKEN = '8119915270:AAGYc2V28Vmhi-kVIezgHjJpICnQnHAf-RM'  # <-- ganti token master lu
ADMINS = {7316824198}  # <-- ganti user ID admin utama
BOTS_FILE = 'bots.json'
ADMINS_FILE = 'admins.json'
BOTS = {}
ADDITIONAL_ADMINS = set()
current_dir = os.path.expanduser("~")

# === AUTO CREATE FILES
for filename, default_data in [(BOTS_FILE, {},), (ADMINS_FILE, {"additional_admins": []})]:
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_data, f, indent=4)

def load_bots_data():
    with open(BOTS_FILE, 'r') as f:
        return json.load(f)

def save_bots_data(data):
    with open(BOTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_admins_data():
    global ADDITIONAL_ADMINS
    with open(ADMINS_FILE, 'r') as f:
        data = json.load(f)
        ADDITIONAL_ADMINS = set(data.get("additional_admins", []))

def save_admins_data():
    with open(ADMINS_FILE, 'w') as f:
        json.dump({"additional_admins": list(ADDITIONAL_ADMINS)}, f, indent=4)

load_admins_data()

def is_admin(user_id):
    return user_id in ADMINS or user_id in ADDITIONAL_ADMINS

# === KEEP ALIVE
async def keep_alive_task(bot):
    while True:
        await asyncio.sleep(4 * 3600)
        for admin_id in ADMINS.union(ADDITIONAL_ADMINS):
            try:
                await bot.send_message(chat_id=admin_id, text="Keep Alive: Bot masih aktif.")
            except Exception as e:
                print(f"[KeepAliveError] {e}")

# === BOT COMMAND HANDLERS
def register_bot_handlers(app):
    async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.strip()

            if is_admin(user_id):
                command = message_text

                banned_words = ["shutdown", "reboot", "halt", "poweroff"]
                if any(word in command.lower() for word in banned_words):
                    await update.message.reply_text("Blocked dangerous command!")
                    return

                global current_dir
                if command.startswith("cd "):
                    path = command[3:].strip()
                    new_dir = os.path.abspath(os.path.join(current_dir, path))
                    if os.path.isdir(new_dir):
                        current_dir = new_dir
                        await update.message.reply_text(f"Changed directory to:\n`{current_dir}`", parse_mode='Markdown')
                    else:
                        await update.message.reply_text(f"Directory not found:\n`{new_dir}`", parse_mode='Markdown')
                    return

                if command == "pwd":
                    await update.message.reply_text(f"Current Directory:\n`{current_dir}`", parse_mode='Markdown')
                    return

                start_time = datetime.datetime.now()
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=current_dir,
                    timeout=600
                )
                end_time = datetime.datetime.now()
                elapsed = (end_time - start_time).total_seconds()

                output = result.stdout.strip() + "\n" + result.stderr.strip()
                output = output.strip() or "(No output)"
                status = "✅ Success" if result.returncode == 0 else "❌ Failed"

                full_text = (
                    f"User ID: `{user_id}`\n"
                    f"Current Directory: `{current_dir}`\n"
                    f"Status: `{status}`\n"
                    f"Time: `{elapsed:.2f} seconds`\n\n"
                    f"Output:\n{output}"
                )

                for i in range(0, len(full_text), 4000):
                    await update.message.reply_text(full_text[i:i+4000], parse_mode='Markdown')
            else:
                await update.message.reply_text("Unauthorized access.")

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    app.add_handler(MessageHandler(filters.TEXT, handle_command))

# === MASTER BOT COMMANDS
async def addbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /addbot <token>")
            return

        token = context.args[0]

        try:
            test_app = ApplicationBuilder().token(token).build()
            await test_app.bot.get_me()
        except Exception:
            await update.message.reply_text("Invalid token!")
            return

        bots_data = load_bots_data()
        if token in bots_data:
            await update.message.reply_text("Bot sudah terdaftar.")
            return

        bots_data[token] = {}
        save_bots_data(bots_data)

        subprocess.Popen(["python3", __file__, token])

        await update.message.reply_text(
            f"✅ Bot baru aktif!\nToken: `{token}`\nStatus: `Running`",
            parse_mode='Markdown'
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def listbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return

        bots_data = load_bots_data()
        if not bots_data:
            await update.message.reply_text("Belum ada bot yang ditambahkan.")
            return

        text = "**Daftar Bot (saved):**\n\n"
        for token in bots_data:
            text += f"`{token}`\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id not in ADMINS:
            await update.message.reply_text("Only main admin can add new admins.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /addadmin <user_id>")
            return

        new_admin = int(context.args[0])
        if new_admin in ADDITIONAL_ADMINS or new_admin in ADMINS:
            await update.message.reply_text("User already admin.")
        else:
            ADDITIONAL_ADMINS.add(new_admin)
            save_admins_data()
            await update.message.reply_text(f"User `{new_admin}` added as admin.", parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id not in ADMINS:
            await update.message.reply_text("Only main admin can delete admins.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /deladmin <user_id>")
            return

        target_admin = int(context.args[0])

        if target_admin in ADMINS:
            await update.message.reply_text("Cannot remove main admin.")
            return
        if target_admin in ADDITIONAL_ADMINS:
            ADDITIONAL_ADMINS.remove(target_admin)
            save_admins_data()
            await update.message.reply_text(f"User `{target_admin}` removed from admin.", parse_mode='Markdown')
        else:
            await update.message.reply_text("User not found in additional admins.")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def listadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return

        text = "**Admin List:**\n\n"
        text += "**Main Admin(s):**\n"
        text += "\n".join(f"`{admin}`" for admin in ADMINS)
        text += "\n\n**Additional Admin(s):**\n"
        text += "\n".join(f"`{admin}`" for admin in ADDITIONAL_ADMINS) if ADDITIONAL_ADMINS else "(none)"

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# === MAIN PROGRAM
if __name__ == '__main__':
    if len(sys.argv) > 1:
        # CHILD BOT MODE
        token = sys.argv[1]
        print(f"[+] Starting Child Bot for token: {token}")

        app = ApplicationBuilder().token(token).build()
        register_bot_handlers(app)

        loop = asyncio.get_event_loop()
        loop.create_task(keep_alive_task(app.bot))
        app.run_polling(allowed_updates=["message", "edited_message"])
    else:
        # MASTER BOT MODE
        print("[+] Starting Master Bot")

        app = ApplicationBuilder().token(MASTER_BOT_TOKEN).build()
        app.add_handler(CommandHandler("addbot", addbot))
        app.add_handler(CommandHandler("listbot", listbot))
        app.add_handler(CommandHandler("addadmin", addadmin))
        app.add_handler(CommandHandler("deladmin", deladmin))
        app.add_handler(CommandHandler("listadmin", listadmin))

        app.run_polling(allowed_updates=["message", "edited_message"])
