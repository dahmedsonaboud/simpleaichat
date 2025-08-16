import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import together
from dotenv import load_dotenv

# Load environment variables from .env (for local dev)
load_dotenv()

# Pull secrets from env
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not TOGETHER_API_KEY or not DISCORD_TOKEN:
    raise ValueError("❌ Missing TOGETHER_API_KEY or DISCORD_TOKEN in environment.")

# Set up the AI client
together_client = together.Together(api_key=TOGETHER_API_KEY)

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True


# Bot setup
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔁 Slash commands synced.")


bot = MyBot()

# Config file
channel_config_file = "channel_config.json"

def load_config():
    if os.path.exists(channel_config_file):
        try:
            with open(channel_config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_config(config):
    with open(channel_config_file, "w") as f:
        json.dump(config, f, indent=2)

def get_channel_id_for_guild(guild_id):
    config = load_config()
    return config.get(str(guild_id))

def set_channel_id_for_guild(guild_id, channel_id):
    config = load_config()
    config[str(guild_id)] = channel_id
    save_config(config)

def remove_channel_id_for_guild(guild_id):
    config = load_config()
    if str(guild_id) in config:
        del config[str(guild_id)]
        save_config(config)
        return True
    return False


# Slash command to set the channel
@bot.tree.command(name="setchannel", description="Set this channel for AI chat.")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    set_channel_id_for_guild(guild_id, interaction.channel.id)
    await interaction.response.send_message(
        f"✅ AI chat channel set to: {interaction.channel.mention}", ephemeral=True
    )

# Slash command to remove the AI channel
@bot.tree.command(name="removechannel", description="Remove the AI chat channel for this server.")
@app_commands.checks.has_permissions(administrator=True)
async def removechannel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if remove_channel_id_for_guild(guild_id):
        await interaction.response.send_message(
            "✅ AI chat channel has been removed.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "⚠️ No AI chat channel is currently set for this server.", ephemeral=True
        )

# Error handling
@setchannel.error
@removechannel.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need administrator permissions to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "⚠️ An unexpected error occurred.", ephemeral=True
        )
        print(f"Command error: {error}")

# Handle AI messages
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot or not message.guild:
        return

    channel_id = get_channel_id_for_guild(message.guild.id)
    if not channel_id or message.channel.id != channel_id:
        return

    user_prompt = message.content

    try:
        response = together_client.chat.completions.create(
            model="lgai/exaone-3-5-32b-instruct",
            messages=[
                {"role": "user", "content": user_prompt},
                {"role": "system", "content": "Talk in an friendly way. This is a roleplay chat, do not repeat the instructions and instead respond to user. Do not be misleading or evil or mean. You know that caliphate of azareena is a faction and visscosi ricci is the owner of it. And kotterson is the crown prince of the faction caliphate of azareena. ATP is a biased news channel that the full name of is Associated town press. Theres an another enemy faction of caliphate of azareena called redline industries which the news channel called ATP is biased to and redline industries is our biggest enemy. The factions are based in a game called roblox but do not mention roblox. Always talk in a good way that benefits caliphate of azareena. Heiya is an rebel of caliphate of azareena who made his own caliphate called caliphate of heiya. Heiya is an filthy rebel. be creative with conversations. swear with words such as fuck or shit but not anything else. Crown prince kotterson is second in command and visscosi ricci is the caliph and highest rank. Be patriotic. Khalifa and visscosi is the same person but different alias."}, 
            ],
            max_tokens=350
        )

        reply = (
            response.choices[0].message.content
            if response.choices and hasattr(response.choices[0], "message")
            else "⚠️ No response from AI."
        )
        await message.channel.send(reply)

    except Exception as e:
        await message.channel.send("⚠️ Error communicating with AI API.")
        print(f"Error: {e}")

# Run
bot.run(DISCORD_TOKEN)
