import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string
import datetime
from datetime import datetime as dt

TOKEN = os.environ.get("DISCORD_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
KEYS_FILE = "keys.json"

def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def gen_key(duration_code):
    p1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"MALEK-{duration_code}-{p1}{p2}"

def get_duration_days(code):
    m = {"1D":1, "3D":3, "7D":7, "14D":14, "30D":30, "90D":90, "180D":180, "365D":365, "LIFE":36500}
    return m.get(code.upper(), 0)

def now_iso():
    return dt.utcnow().isoformat()

def parse_iso(s):
    try: return dt.fromisoformat(s)
    except: return None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MalekBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()
        print("[MALEK HUB] Slash commands synced")

bot = MalekBot()

@bot.event
async def on_ready():
    print(f"[MALEK HUB] Bot ready as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="MALEK HUB")
    )

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="View Script", emoji="📜", style=discord.ButtonStyle.primary, custom_id="malek_view_script")
    async def view_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 MALEK HUB — SCRIPT",
            description="```lua\nloadstring(game:HttpGet('https://example.com/malek.lua'))()\n```",
            color=0xFFFFFF
        )
        embed.set_footer(text="MALEK HUB")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Redeem Key", emoji="🔑", style=discord.ButtonStyle.success, custom_id="malek_redeem")
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="Key Info", emoji="📊", style=discord.ButtonStyle.secondary, custom_id="malek_info")
    async def key_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal())

    @discord.ui.button(label="Get Buyer Role", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="malek_role")
    async def buyer_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👤 Contact admin for Buyer role.", ephemeral=True)

    @discord.ui.button(label="Free Key", emoji="🔗", style=discord.ButtonStyle.secondary, custom_id="malek_free")
    async def free_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔗 No free keys available.", ephemeral=True)

    @discord.ui.button(label="Reset HWID", emoji="🔄", style=discord.ButtonStyle.danger, custom_id="malek_reset")
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ResetModal())

class RedeemModal(discord.ui.Modal, title="🔑 Redeem Key"):
    key_input = discord.ui.TextInput(label="Your Key", placeholder="MALEK-7D-XXXXXXXX", required=True, max_length=30)
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        hwid = str(interaction.user.id)
        keys = load_json(KEYS_FILE)
        if key not in keys:
            await interaction.response.send_message("❌ Invalid key.", ephemeral=True)
            return
        info = keys[key]
        if info.get("banned"):
            await interaction.response.send_message("🚫 This key is banned.", ephemeral=True)
            return
        if info.get("hwid") is None:
            info["hwid"] = hwid
            info["used_by"] = str(interaction.user)
            info["started_at"] = now_iso()
            days = info["days"]
            expires = dt.utcnow() + datetime.timedelta(days=days)
            info["expires_at"] = expires.isoformat()
            keys[key] = info
            save_json(KEYS_FILE, keys)
            await interaction.response.send_message(f"✅ Key activated for **{info['duration_code']}**", ephemeral=True)
            return
        if info["hwid"] != hwid:
            await interaction.response.send_message("⚠️ HWID mismatch.", ephemeral=True)
            return
        exp = parse_iso(info["expires_at"])
        if not exp or dt.utcnow() > exp:
            await interaction.response.send_message("⌛ Key expired.", ephemeral=True)
            return
        remaining = (exp - dt.utcnow()).days
        await interaction.response.send_message(f"✅ Valid — {remaining} day(s) left.", ephemeral=True)

class InfoModal(discord.ui.Modal, title="📊 Key Info"):
    key_input = discord.ui.TextInput(label="Your Key", placeholder="MALEK-7D-XXXXXXXX", required=True, max_length=30)
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        keys = load_json(KEYS_FILE)
        if key not in keys:
            await interaction.response.send_message("❌ Invalid key.", ephemeral=True)
            return
        info = keys[key]
        embed = discord.Embed(title="📊 Key Info", color=0xFFFFFF)
        embed.add_field(name="Key", value=f"`{key}`", inline=False)
        embed.add_field(name="Duration", value=info["duration_code"], inline=True)
        embed.add_field(name="Used By", value=info["used_by"] or "—", inline=True)
        embed.add_field(name="Expires", value=info["expires_at"] or "—", inline=True)
        embed.add_field(name="Banned", value=str(info["banned"]), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ResetModal(discord.ui.Modal, title="🔄 Reset HWID"):
    key_input = discord.ui.TextInput(label="Your Key", placeholder="MALEK-7D-XXXXXXXX", required=True, max_length=30)
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        keys = load_json(KEYS_FILE)
        if key not in keys:
            await interaction.response.send_message("❌ Invalid key.", ephemeral=True)
            return
        info = keys[key]
        if info.get("used_by") and info["used_by"] != str(interaction.user):
            await interaction.response.send_message("🚫 Not your key.", ephemeral=True)
            return
        info["hwid"] = None
        info["used_by"] = None
        info["started_at"] = None
        info["expires_at"] = None
        keys[key] = info
        save_json(KEYS_FILE, keys)
        await interaction.response.send_message("🔄 HWID reset.", ephemeral=True)

@bot.tree.command(name="panel", description="Show MALEK HUB Panel")
async def panel(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    embed = discord.Embed(title="MALEK HUB PANEL", description="**MALEK ON TOP**\n\n🔒 Secure • ⚡ Fast", color=0xFFFFFF)
    embed.set_footer(text="MALEK HUB | v1")
    await interaction.channel.send(embed=embed, view=PanelView())
    await interaction.response.send_message("✅ Panel posted.", ephemeral=True)

@bot.tree.command(name="genkey", description="Generate keys")
@app_commands.describe(duration="1D, 7D, 30D, LIFE", amount="How many")
async def genkey(interaction: discord.Interaction, duration: str, amount: int = 1):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    days = get_duration_days(duration)
    if days == 0:
        await interaction.response.send_message("❌ Invalid duration.", ephemeral=True)
        return
    keys = load_json(KEYS_FILE)
    generated = []
    for _ in range(amount):
        k = gen_key(duration.upper())
        keys[k] = {"duration_code": duration.upper(), "days": days, "created_at": now_iso(), "used_by": None, "hwid": None, "started_at": None, "expires_at": None, "banned": False}
        generated.append(k)
    save_json(KEYS_FILE, keys)
    await interaction.response.send_message(f"✅ Generated:\n```\n" + "\n".join(generated) + "\n```", ephemeral=True)

@bot.tree.command(name="keyinfo", description="Show key info")
async def keyinfo(interaction: discord.Interaction, key: str):
    keys = load_json(KEYS_FILE)
    if key not in keys:
        await interaction.response.send_message("❌ Invalid key.", ephemeral=True)
        return
    info = keys[key]
    embed = discord.Embed(title="📊 Key Info", color=0xFFFFFF)
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Duration", value=info["duration_code"], inline=True)
    embed.add_field(name="Used By", value=info["used_by"] or "—", inline=True)
    embed.add_field(name="Expires", value=info["expires_at"] or "—", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
