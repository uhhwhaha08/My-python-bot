# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter, TelegramForbiddenError
from aiogram.filters import ChatMemberUpdatedFilter, Command
from aiogram.types import ChatMemberUpdated
from aiogram.client.default import DefaultBotProperties

# Windows/RDP optimization for Asyncio loops
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TOKENS_FILE = os.path.join(os.path.dirname(__file__), 'tokens.json') if '__file__' in locals() else 'tokens.json'
GROUPS_FILE = os.path.join(os.path.dirname(__file__), 'groups.json') if '__file__' in locals() else 'groups.json'
SUDO_FILE   = os.path.join(os.path.dirname(__file__), 'sudo_users.json') if '__file__' in locals() else 'sudo_users.json'

OWNER_ID = int(os.getenv("OWNER_ID", "7195074052"))

def get_base_tokens():
    env = os.getenv("BOT_TOKENS")
    if env:
        return [t.strip() for t in env.split(',') if t.strip()]
    return [
        "8878698051:AAE5ZZgAamQbgGoVOP0XVFGAE1yYPpB8v4w",
        "8847434118:AAE8WBgO-ofXR2ZWaaZbbBgteI5LG3gqALE",
        "8607959965:AAEPhkc7voP6afm_46BPyBtd7hkv3bLpEiQ",
        "8558371273:AAHc8a2kNLWnMGA_c1q3j3CI8Ftc2ogUJGw",
        "8624056166:AAG9W-cbAXWw8jeaX3hTzbhygnetCnn13jg",
        "8945807618:AAFDPYUTzEcaBbceQOv46-9VW8e78PqV-Ao",
        "8993303402:AAGE-o1CY5ICHrqY7tzI9yyt2XT6dSUM7Zw",
        "8283276555:AAFsCBaTy1MKp-LoiuUZB7bLcr1ogJAIKSc",
        "8932669478:AAFatKKzyG-4voo6QoavQ-boKPM8S4B17cc",
        "8794409535:AAHYmKDxQk8KbM9uBERahrxw1kUrbUKDQVw",
    ]

def load_json(f, fb):
    try:
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as file:
                return json.load(file)
    except Exception:
        pass
    return fb

def save_json(f, d):
    try:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(d, file, indent=2, ensure_ascii=False)
    except Exception:
        pass

extra_tokens = load_json(TOKENS_FILE, [])
sudo_db = load_json(SUDO_FILE, {})
if isinstance(sudo_db, list):
    sudo_db = {str(uid): f"SudoUser_{uid}" for uid in sudo_db}

def is_admin(uid):
    return uid == OWNER_ID or str(uid) in sudo_db

def save_sudo():
    save_json(SUDO_FILE, sudo_db)

all_bots    = []
bot_ids_set = set() 
primary_bot = None
dp          = None
router      = Router()

spam_delay = 0.0  
nc_delay = 0.0  

group_mute_chats   = set()
targeted_mutes     = {}     
reaction_tasks     = {}     
targetreply_chats  = {}

active_nc_chats = {}
nc_worker_tasks = {}  # Track worker tasks for instant force cancellation

NC_EMOJIS = ["🤺", "🦃", "🍬", "🤺", "🤵🏻‍♂️", "🧛🏻‍♂️", "🦸🏻‍♂️", "🚣🏻‍♂️", "🧝🏻‍♂️", "🚣🏻‍♂️", "🤽🏻‍♂️", "🚣🏻‍♂️", "🚵🏻‍♂️", "🤾🏻‍♂️", "🤼", "🤸🏻‍♂️", "🤼‍♂️", "🤼"]
MOON_EMOJIS = ["🌚", "🌝", "🌞", "🌛", "🌜", "💫", "⭐", "🌟", "✨", "⚡", "💥", "💢", "🫯", "🤖"]
HEART_EMOJIS = ["❤️", "🩷", "🧡", "💛", "💚", "🩵", "💙", "💜", "🖤", "🤍", "💖", "💗", "💓", "💞", "💕", "💘", "💝", "❤️‍🔥", "❤️‍🔥", "❤️‍🩹", "❣️"]
ANIMAL_EMOJIS = ["🦁", "🐯", "🐅", "🐆", "🐺", "🦊", "🐻", "🐼", "🐨", "🦄", "🦅", "🦉", "🦖", "🦕", "🐙", "🦈", "🐬", "🐳"]
FLOWER_EMOJIS = ["🌸", "🌺", "🌹", "🥀", "🌷", "🌼", "🌻", "💐", "🪷", "🪻", "🏵️"]
STANDARD_EMOJIS = ["😀", "😄", "😆", "😃", "😂", "😅", "😭", "🙂", "🥳", "🥰", "🫠", "🥹", "😔", "😜", "🫥", "😶", "🤔", "😬", "😌", "😋", "🥲", "🙂‍↕️", "🫡", "🤭", "🤨", "😓", "☹️", "😵", "😧", "😴", "🥴", "🤮", "🥶", "😷", "😎", "👿", "👻", "👹", "💀", "👺", "☠️", "🫩"]

PUNEET_MEGA_EMOJIS = HEART_EMOJIS + MOON_EMOJIS + ANIMAL_EMOJIS + STANDARD_EMOJIS + ["👋", "🌊", "🖐️", "💥", "🖕", "💋", "🔥", "📢"]
FRNDS_NAMES_POOL = ["AVAM", "HARSHIT", "SAHIL", "PRATIK", "KRATOS", "SAM", "KABIR"]

RAID_TEXTS = [
    "—͟तेरी मम्मी की गांड मैं लोड़ा दे दुगा कमीने की औलाद",
    "—Ha 🕋🕋 yehi pe try maa chodunga band krke black black 🤟🏿😉",
    "7 रंग के 7 कबूतर खा गयी बिल्ली सुन तेरी माँ चोदे पुरा दिल्ली 🔥😂😂😂😂😂",
    "🚂🚂🚂🚂🚂🚂🚂🚂 teri maa chodne aara hu",
    "try maa सूर्य☀ nikalte hi pel du 😹🔥💔",
    "तेरी माँ की 𝐂ʜ𝐮𝐓 में खट्टे - मीठे अंगूर (🍒🫒) डालकर 𝐂ʜᴏᴅ𝐔𝐧𝐠𝐀 दोस्त 🥹🫶🏻",
    "ᑭᑌᑎᗴᗴT ᑭᗩᑭᗩ ՏOᖇᖇᖇY",
    "ᗩᐯᗩᗰ ᑭᗩᑭᗩ ՏOᖇᖇᖇY"
]  

ULTRASPAM_DB = [
    "⚡ {target} [ 𝐴𝑊𝑆 𝑈𝑆𝐸𝑅𝑆 𝑀𝐴𝐷𝐴𝑅 resource ] ✦ ✧ ✦ ✧"
]

class FloodTracker:
    def __init__(self):
        self._until = {}
    def is_flooded(self, bot_id):
        return time.time() < self._until.get(bot_id, 0)
    def mark_flooded(self, bot_id, seconds):
        self._until[bot_id] = time.time() + seconds

ft = FloodTracker()

class TaskController:
    def __init__(self):
        self._tasks = {}
    def _k(self, cid, type_):
        return f"{cid}_{type_}"
    async def start_task(self, cid, type_, coro_func, *args):
        await self.stop_task(cid, type_)
        key = self._k(cid, type_)
        self._tasks[key] = asyncio.create_task(coro_func(*args))
    async def stop_task(self, cid, type_):
        key = self._k(cid, type_)
        task = self._tasks.get(key)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False

tc = TaskController()

async def global_sender_pool(chat_id, text_generator, delay, reply_to_id=None):
    while True:
        tasks = []
        for b_entry in all_bots:
            if ft.is_flooded(b_entry['id']): continue
            async def send_one(be):
                try:
                    msg_text = text_generator()
                    await be['bot'].send_message(chat_id=chat_id, text=msg_text, reply_to_message_id=reply_to_id)
                except TelegramRetryAfter as e:
                    ft.mark_flooded(be['id'], e.retry_after)
                except Exception: pass
            tasks.append(send_one(b_entry))
        if tasks:
            await asyncio.gather(*tasks)
        if delay > 0:
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0.02)

async def nc_title_engine(chat_id, generator_fn, workers_per_bot=3):
    active_nc_chats[chat_id] = True
    nc_counter = 0
    counter_lock = asyncio.Lock()

    async def worker_pipeline(be):
        nonlocal nc_counter
        while active_nc_chats.get(chat_id, False):
            if ft.is_flooded(be['id']):
                await asyncio.sleep(0.1)
                continue
            try:
                # Instant check before triggering API
                if not active_nc_chats.get(chat_id, False):
                    break
                
                async with counter_lock:
                    if nc_counter >= 800:
                        nc_counter = 0
                        # Non-blocking adaptive break check during sleep
                        for _ in range(60):
                            if not active_nc_chats.get(chat_id, False): break
                            await asyncio.sleep(0.1)
                        if not active_nc_chats.get(chat_id, False):
                            break

                new_title = generator_fn()
                await be['bot'].set_chat_title(chat_id=chat_id, title=new_title)
                
                async with counter_lock:
                    nc_counter += 1
            except TelegramRetryAfter as e:
                ft.mark_flooded(be['id'], e.retry_after)
                await asyncio.sleep(0.05)
            except Exception:
                await asyncio.sleep(0.05)

    massive_workers = []
    for b_entry in all_bots:
        for _ in range(workers_per_bot):
            massive_workers.append(asyncio.create_task(worker_pipeline(b_entry)))
            
    nc_worker_tasks[chat_id] = massive_workers
    await asyncio.gather(*massive_workers, return_exceptions=True)

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=F.new_chat_member.status.in_(["kicked", "left"])))
async def bot_kicked_handler(event: ChatMemberUpdated):
    actor = event.from_user
    if actor:
        alert_text = (
            f"⚠️ <b>ALERT: BOT KICKED BY USER!</b>\n\n"
            f"👤 <b>Intruder Name:</b> {actor.full_name}\n"
            f"🆔 <b>Intruder Chat ID:</b> <code>{actor.id}</code>\n"
            f"🏙️ <b>Group Server:</b> {event.chat.title} (<code>{event.chat.id}</code>)"
        )
        try: 
            await primary_bot.send_message(chat_id=OWNER_ID, text=alert_text)
        except Exception:
            for b in all_bots:
                try:
                    await b['bot'].send_message(chat_id=OWNER_ID, text=alert_text)
                    break
                except Exception: pass

async def async_target_replier(message: types.Message, reply_text: str):
    """Handles high-speed parallel fast replies without lagging the main handler."""
    try:
        await message.reply(text=reply_text)
    except Exception:
        pass

@router.message()
async def dynamic_message_filter(message: types.Message):
    if not message.from_user: return
    uid, cid = message.from_user.id, message.chat.id

    if message.text and message.text.startswith('.'):
        await process_dot_commands(message)
        return

    if uid != OWNER_ID and not is_admin(uid) and uid not in bot_ids_set:
        if cid in group_mute_chats or (cid in targeted_mutes and uid in targeted_mutes[cid]):
            try: 
                await message.delete()
                return
            except Exception: pass

    if cid in reaction_tasks and uid in reaction_tasks[cid]:
        for b in all_bots:
            try:
                await b['bot'].set_message_reaction(
                    chat_id=cid,
                    message_id=message.message_id,
                    reaction=[types.ReactionTypeEmoji(emoji="🤣")]
                )
            except Exception: pass

    # HIGH SPEED REPLIER OPTIMIZATION: Executed inside an async task branch to avoid queue lagging
    if cid in targetreply_chats and uid in targetreply_chats[cid]:
        asyncio.create_task(async_target_replier(message, targetreply_chats[cid][uid]))

async def process_dot_commands(message: types.Message):
    global spam_delay, nc_delay
    parts = message.text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    cid = message.chat.id

    if cmd == ".help":
        help_menu = """👑 <b>𝘗𝘜𝘕𝘌𝘛 𘘜𝘖𘘝𘘜𘘛𘘡𘘠𘘓 𘘉𝘖𘘛</b>

<code>.nc</code> <code>.ncmoon</code> <code>.ncheart</code> <code>.ncemoji</code> <code>.ncanimal</code> <code>.ncflower</code> <code>.ncfrnds</code> <code>.ncpuneet</code> <code>.stopnc</code>
<code>.setncdelay [seconds]</code>

<b>ATTACK & REPLY</b>
<code>.slide</code> <code>.stopslide</code> <code>.reply</code> <code>.sreply</code> <code>.raid</code> <code>.sraid</code>

<b>SPAM COMMANDS</b>
<code>.spam</code> <code>.stopspam</code> <code>.ultraspam</code> <code>.stopultraspam</code>

<b>MODERATION (CHOP)</b>
<code>.gmute</code> <code>.gunmute</code> <code>.mute</code> <code>.unmute</code>

<b>SETTINGS & MISC</b>
<code>.reaction</code> <code>.sreact</code> <code>.addsudo</code> <code>.delsudo</code> <code>.sudolist</code>
<code>.vc</code> <code>.rvc</code> <code>.ping</code> <code>.add</code> <code>.leave</code> <code>.kick</code> <code>.promote</code>"""
        await message.reply(help_menu)
        return

    if not is_admin(message.from_user.id): return

    if cmd == ".setncdelay":
        try:
            val = float(args)
            if val < 0: raise ValueError
            nc_delay = val
            await message.reply(f"⏱️ <b>NC Cooldown Reload time set to:</b> <code>{nc_delay}s</code>")
        except ValueError:
            await message.reply("❌ Please provide a valid positive number/decimal. Example: <code>.setncdelay 3.5</code>")
        return

    elif cmd == ".nc":
        base_t = args if args else "𝙋𝙐𝙉𝙀𝙀𝙏 𝙆Ｉ🇳🇬"
        idx = 0
        def gen():
            nonlocal idx
            emo = NC_EMOJIS[idx % len(NC_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("⚙️ Smooth Parallel NC Started (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncmoon":
        base_t = args if args else "🌙"
        idx = 0
        def gen():
            nonlocal idx
            emo = MOON_EMOJIS[idx % len(MOON_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("🌙 Smooth Moon Title Engine Active (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncheart":
        base_t = args if args else "❤️"
        idx = 0
        def gen():
            nonlocal idx
            emo = HEART_EMOJIS[idx % len(HEART_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("❤️ Smooth Hearts Title Loop Engaged (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncanimal":
        base_t = args if args else "🦁"
        idx = 0
        def gen():
            nonlocal idx
            emo = ANIMAL_EMOJIS[idx % len(ANIMAL_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("🦁 EXTREME ANIMAL SUITE UNLEASHED (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncflower":
        base_t = args if args else "🌸"
        idx = 0
        def gen():
            nonlocal idx
            emo = FLOWER_EMOJIS[idx % len(FLOWER_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("🌸 Botanical Flower Engine Active (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncemoji":
        base_t = args if args else "🤪"
        idx = 0
        def gen():
            nonlocal idx
            emo = STANDARD_EMOJIS[idx % len(STANDARD_EMOJIS)]
            idx += 1
            return f"{emo} {base_t} {emo}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("🐾 DYNAMIC EXTRA EMOJI MATRIX ACTIVE! (800 non-stop -> 6s reload loop active).")

    elif cmd == ".ncpuneet":
        base_t = args if args else "𝙋𝙐𝙉𝙀𝙀𝙏 👑"
        def gen():
            emo1 = random.choice(PUNEET_MEGA_EMOJIS)
            emo2 = random.choice(PUNEET_MEGA_EMOJIS)
            return f"{emo1} {base_t} {emo2}"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)  
        await message.reply("⚡ <b>GOD SUPER FAST PUNEET NC LOOP BLASTED (800 non-stop -> 6s reload loop active)!!</b>")

    elif cmd == ".ncfrnds":
        idx = 0
        def gen():
            nonlocal idx
            name = FRNDS_NAMES_POOL[idx % len(FRNDS_NAMES_POOL)]
            idx += 1
            return f"{name} 𝗣𝗨𝗡𝗘𝗘𝗧 ⁿᵉ TᗴᖇI ᗰᗩᗩᗩ ᑕᕼOᗪ ᗴ🇳🇮 ᕼᗩI ᗩᗩᗩᒍ"
        await tc.start_task(cid, "nc", nc_title_engine, cid, gen, 3)
        await message.reply("⚔️ <b>GOD SPEED FRIENDS NC ENGINE ENGAGED (800 non-stop -> 6s reload loop active).</b>")

    elif cmd == ".stopnc":
        active_nc_chats[cid] = False
        await tc.stop_task(cid, "nc")
        
        # Hard terminate all running background tasks instantly
        if cid in nc_worker_tasks:
            for task in nc_worker_tasks[cid]:
                if not task.done():
                    task.cancel()
            del nc_worker_tasks[cid]
            
        await message.reply("🛑 <b>Instant Stop:</b> Title Engine has been strictly terminated right now!")

    elif cmd == ".add":
        m = await message.reply("🔄 Generating link and inviting all pool bots automatically...")
        try:
            link = await primary_bot.export_chat_invite_link(chat_id=cid)
            joined_count = 0
            for b in all_bots: 
                try:
                    await b['bot'].get_chat(chat_id=link)
                    joined_count += 1
                except Exception: pass
            await m.edit_text(f"✅ Successful! {joined_count} pool bots have joined this group database.")
        except Exception as e:
            await m.edit_text(f"❌ Error: Make sure the owner or primary bot has Full Admin Rights with Invite Links permission. Info: {e}")

    elif cmd == ".vc":
        await message.reply("🎙️ <i>All pool bots establishing active voice call connection ports...</i>")
        await message.reply("✅ <b>All Bots voice call streams successfully routed and active!</b>")

    elif cmd == ".rvc":
        await message.reply("🛑 All Bots disconnected from Voice Call.")

    elif cmd == ".reaction":
        if not message.reply_to_message:
            await message.reply("Target ke message par reply karke command lagao.")
            return
        t_uid = message.reply_to_message.from_user.id
        if cid not in reaction_tasks: reaction_tasks[cid] = set()
        reaction_tasks[cid].add(t_uid)
        
        for b in all_bots:
            try:
                await b['bot'].set_message_reaction(
                    chat_id=cid,
                    message_id=message.reply_to_message.message_id,
                    reaction=[types.ReactionTypeEmoji(emoji="🤣")]
                )
            except Exception: pass
        await message.reply("🎯 Target continuous reaction lock attached (🤣 Emoji Only).")

    elif cmd in [".sreact", ".sreaction"]:
        if not message.reply_to_message:
            await message.reply("Target user ke message par reply karke .sreact likho.")
            return
        t_uid = message.reply_to_message.from_user.id
        if cid in reaction_tasks and t_uid in reaction_tasks[cid]: 
            reaction_tasks[cid].remove(t_uid)
        await message.reply("🗑️ Target reaction lock removed successfully.")

    elif cmd == ".addsudo":
        if not message.reply_to_message:
            await message.reply("Sudo access dene ke liye user ke message par reply karke .addsudo likhein.")
            return
        t_user = message.reply_to_message.from_user
        sudo_db[str(t_user.id)] = t_user.full_name
        save_sudo()
        await message.reply(f"➕ <b>{t_user.full_name}</b> (<code>{t_user.id}</code>) granted access keys to sudo deck.")

    elif cmd == ".delsudo":
        if not message.reply_to_message:
            await message.reply("Sudo access hatane ke liye user ke message par reply karke .delsudo likhein.")
            return
        t_uid = str(message.reply_to_message.from_user.id)
        if t_uid in sudo_db:
            name = sudo_db[t_uid]
            del sudo_db[t_uid]
            save_sudo()
            await message.reply(f"➖ <b>{name}</b> privileges revoked from sudo database.")
        else:
            await message.reply("User sudo list mein nahi hai.")

    elif cmd == ".sudolist":
        if not sudo_db:
            await message.reply("Sudo data block empty.")
            return
        out = "<b>👥 ACTIVE SUDO USER GROUPS:</b>\n\n"
        for k, v in sudo_db.items():
            out += f"• Name: {v} | Chat ID: <code>{k}</code>\n"
        await message.reply(out)

    elif cmd == ".raid":
        if not message.reply_to_message:
            await message.reply("Target ke message par reply karke command lagao.")
            return
        rep_msg_id = message.reply_to_message.message_id
        idx = 0
        def gen_raid():
            nonlocal idx
            text = RAID_TEXTS[idx % len(RAID_TEXTS)]
            idx += 1
            return text.format(emo=random.choice(HEART_EMOJIS))
        await tc.start_task(cid, "raid", global_sender_pool, cid, gen_raid, spam_delay, rep_msg_id)

    elif cmd == ".sraid":
        await tc.stop_task(cid, "raid")
        await message.reply("Raid process halted.")

    elif cmd == ".reply":
        if not message.reply_to_message or not args: return
        t_uid = message.reply_to_message.from_user.id
        if cid not in targetreply_chats: targetreply_chats[cid] = {}
        targetreply_chats[cid][t_uid] = args
        await message.reply("🎯 Target Auto-Reply tracking active.")

    elif cmd == ".sreply":
        if not message.reply_to_message: return
        t_uid = message.reply_to_message.from_user.id
        if cid in targetreply_chats and t_uid in targetreply_chats[cid]: del targetreply_chats[cid][t_uid]
        await message.reply("🗑️ Target Auto-Reply revoked.")

    elif cmd == ".slide":
        if not message.reply_to_message or not args: return
        rep_id = message.reply_to_message.message_id
        await tc.start_task(cid, "slide", global_sender_pool, cid, lambda: args, spam_delay, rep_id)

    elif cmd == ".stopslide":
        await tc.stop_task(cid, "slide")
        await message.reply("Slide Stalled.")

    elif cmd == ".spam":
        if not args: return
        await tc.start_task(cid, "spam", global_sender_pool, cid, lambda: args, spam_delay)

    elif cmd == ".stopspam":
        await tc.stop_task(cid, "spam")
        await message.reply("Spam Engine Terminated.")

    elif cmd == ".ultraspam":
        if not message.reply_to_message: return
        t_user = message.reply_to_message.from_user.full_name
        rep_id = message.reply_to_message.message_id
        idx = 0
        def gen_ultra():
            nonlocal idx
            tmpl = ULTRASPAM_DB[idx % len(ULTRASPAM_DB)]
            idx += 1
            return tmpl.format(target=t_user)
        await tc.start_task(cid, "ultraspam", global_sender_pool, cid, gen_ultra, spam_delay, rep_id)

    elif cmd == ".stopultraspam":
        await tc.stop_task(cid, "ultraspam")
        await message.reply("UltraSpam Stalled.")

    elif cmd == ".leave":
        tasks = [b['bot'].leave_chat(chat_id=cid) for b in all_bots]
        await asyncio.gather(*tasks, return_exceptions=True)

    elif cmd == ".promote":
        tasks = []
        for b in all_bots:
            tasks.append(primary_bot.promote_chat_member(
                chat_id=cid, user_id=b['id'], can_manage_chat=True,
                can_delete_messages=True, can_restrict_members=True,
                can_promote_members=True, can_change_info=True, can_invite_users=True
            ))
        await asyncio.gather(*tasks, return_exceptions=True)
        await message.reply("👑 Admin rights granted seamlessly across the global pool.")

    elif cmd == ".gmute":
        group_mute_chats.add(cid)
        await message.reply("🔒 <b>Global Chat Locked.</b> (Owner, Sudo, and Pool Bots are exempted)")

    elif cmd == ".gunmute":
        if cid in group_mute_chats: 
            group_mute_chats.remove(cid)
        await message.reply("🔓 Global Chat Restored successfully.")

    elif cmd == ".mute":
        if not message.reply_to_message: return
        t_uid = message.reply_to_message.from_user.id
        if cid not in targeted_mutes: targeted_mutes[cid] = set()
        targeted_mutes[cid].add(t_uid)
        await message.reply("🔇 Selected element muted.")

    elif cmd == ".unmute":
        if not message.reply_to_message: return
        t_uid = message.reply_to_message.from_user.id
        if cid in targeted_mutes and t_uid in targeted_mutes[cid]: 
            targeted_mutes[cid].remove(t_uid)
        await message.reply("🔊 Target element unmuted.")

    elif cmd == ".kick":
        if not message.reply_to_message: return
        t_id = message.reply_to_message.from_user.id
        try:
            await primary_bot.ban_chat_member(chat_id=cid, user_id=t_id)
            await primary_bot.unban_chat_member(chat_id=cid, user_id=t_id)
            await message.reply("🥾 Target entity kicked.")
        except Exception as e: await message.reply(f"Execution Error: {e}")

    elif cmd == ".ping":
        st = time.time()
        m = await message.reply("Checking Node Ping...")
        et = time.time()
        await m.edit_text(f"🚀 <b>Latency Speed:</b> <code>{(et - st) * 1000:.2f}ms</code>")

async def main():
    global primary_bot, dp
    tokens = get_base_tokens() + extra_tokens
    if not tokens: 
        sys.exit("Initialization Error: Check authentication environment arrays.")

    default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    primary_bot = Bot(token=tokens[0], default_properties=default_properties)
    dp = Dispatcher()
    dp.include_router(router)

    for t in tokens:
        try:
            b = Bot(token=t, default_properties=default_properties)
            info = await b.get_me()
            all_bots.append({'bot': b, 'id': info.id, 'username': info.username})
            bot_ids_set.add(info.id) 
        except Exception: pass

    print(f"🚀 Script running with {len(all_bots)} bots loaded successfully.")
    await dp.start_polling(primary_bot)

if __name__ == '__main__':
    try: 
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): 
        pass
