
# Created By BitcoinJake09 from Anonymous Bitcoin Community
# https://discord.com/oauth2/authorize?client_id=1226314424348839997&permissions=1391569480738&scope=bot
import discord
import json
from collections import defaultdict
from datetime import datetime, timedelta

from dtoken import TOKEN  # Make sure this matches your file and token variable

client = discord.Client(intents=discord.Intents.all())
spam_tracker = defaultdict(lambda: defaultdict(list))
banned_messages_file = 'banned_messages.json'

def load_banned_messages():
    try:
        with open(banned_messages_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_banned_message(message_content):
    banned_messages = load_banned_messages()
    if message_content not in banned_messages:
        banned_messages.append(message_content)
        with open(banned_messages_file, 'w') as file:
            json.dump(banned_messages, file)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # Log the number of servers the bot is connected to
    print(f'Connected to {len(client.guilds)} servers.')


@client.event
async def on_guild_join(guild):
    # Create a message to introduce the bot and its functionalities
    greeting_message = """
    Hello! I'm Guardian Shield, designed to protect your server from spam and scams.
    Please ensure I have the following permissions for optimal functionality:
    - View Channels
    - Send Messages
    - Manage Messages
    - Kick Members
    """

    # Check if the bot has the necessary permissions
    me = guild.me  # The bot's Member object in the guild
    required_permissions = [
        me.guild_permissions.view_channel,
        me.guild_permissions.send_messages,
        me.guild_permissions.manage_messages,
        me.guild_permissions.kick_members,
    ]

    # If any of the required permissions are missing, notify the server
    if not all(required_permissions):
        greeting_message += "\nI'm missing some of the required permissions. Please adjust my role settings."

    # Attempt to send the greeting message to the guild's system channel
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        await guild.system_channel.send(greeting_message)
    else:
        # If there's no system channel with send permissions, try the first text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(greeting_message)
                break  # Exit after finding the first suitable channel


def has_permission(member):
    # Check if the member is the owner
    if member == member.guild.owner:
        return True
    # Check for Administrator permission
    if member.guild_permissions.administrator:
        return True
    # Check for a role named "Moderator" (customize as needed for your server)
    for role in member.roles:
        if role.name == "Moderator":
            return True
    return False

def has_mod_permissions(member):
    # Checks if the member has moderator-level permissions such as kick_members and manage_messages
    return member.guild_permissions.kick_members and member.guild_permissions.manage_messages

def bot_has_required_permissions(guild):
    me = guild.me  # The bot's member object in the guild
    return all([
        me.guild_permissions.view_channel,
        me.guild_permissions.send_messages,
        me.guild_permissions.manage_messages,
        me.guild_permissions.kick_members,
    ])


@client.event
async def on_message(message):
    # Ignore all bots
    if message.author.bot:
        return

    if message.content.startswith('!permcheck'):
        if not has_mod_permissions(message.author):
            await message.channel.send("You need moderator-level permissions to use this command.")
            return

        if bot_has_required_permissions(message.guild):
            await message.channel.send("The bot has all the required permissions.")
        else:
            await message.channel.send("The bot is missing some required permissions. Please check its role settings.")

    # Command: Delete all messages containing a specific string
    if message.content.startswith('!del_all'):
        if not has_permission(message.author):
            await message.channel.send("You do not have permission to use this command.")
            return

        target_string = message.content[len('!del_all '):].strip()
        deleted_count = 0
        for channel in message.guild.text_channels:
            if channel == message.channel:  # Skip the command's channel
                continue

            try:
                async for msg in channel.history(limit=100):
                    if target_string in msg.content:
                        await msg.delete()
                        deleted_count += 1
            except discord.errors.Forbidden:
                print(f"Missing permissions to read or delete messages in {channel.name}")
            except Exception as e:
                print(f"Error in {channel.name}: {str(e)}")

        confirmation_message = f"Deletion complete. {deleted_count} messages containing the target string were deleted."
        await message.channel.send(confirmation_message)

    # Message tracking and spam detection
    user_id = message.author.id
    now = datetime.now()
    spam_tracker[user_id][message.content].append(now)

    # Inside the spam detection if-block
    if len(spam_tracker[user_id][message.content]) >= 3:
        if (now - first_msg_time <= timedelta(seconds=60)):
            print(f"Spam messages detected in '{message.guild.name}' in channel '{message.channel.name}'")

        first_msg_time = spam_tracker[user_id][message.content][0]
        if now - first_msg_time <= timedelta(seconds=60):
            try:
                # Kick the user instead of banning
                await message.author.kick(reason="Spamming messages")
                await message.channel.send(f"{message.author.mention} has been kicked for spamming.")

                # Proceed to delete the messages that were considered spam
                for channel in message.guild.text_channels:
                    async for msg in channel.history(limit=100):
                        if msg.author == message.author and msg.content == message.content:
                            try:
                                await msg.delete()
                            except discord.Forbidden:
                                print(f"Lacking permissions to delete in {channel.name}")
                            except Exception as e:
                                print(f"Failed to delete message in {channel.name}: {str(e)}")

                # Log the spam message to the JSON file
                save_banned_message(message.content)
            except discord.Forbidden:
                print("Bot does not have permissions to kick or delete messages.")
            # Clear the tracked messages for this user to reset detection
            del spam_tracker[user_id][message.content]

    # Remove messages older than 60 seconds from tracking to avoid memory issues
    for msg_content in list(spam_tracker[user_id]):
        spam_tracker[user_id][msg_content] = [msg_time for msg_time in spam_tracker[user_id][msg_content] if now - msg_time <= timedelta(seconds=60)]
        if not spam_tracker[user_id][msg_content]:
            del spam_tracker[user_id][msg_content]

client.run(TOKEN)
