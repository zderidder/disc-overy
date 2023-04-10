import discord, os, re, logging, spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from discord.ext import commands

#load .env properties
load_dotenv()

ALLOW_DUPLICATE_TRACKS = os.getenv('ALLOW_DUPLICATE_TRACKS')
TRUSTED_USERS = os.getenv("TRUSTED_USER_IDS")
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
trusted_users = [] #users who can send a DM to bot account to use bot locally

bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
scope = "playlist-modify-public"
spotify_url_regex = re.compile('(?:(spotify:|https:|http:))(?:\/\/[a-z]+\.spotify\.com\/)?(track\/|track:)([^\s]+)')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=os.getenv('SPOTIFY_CLIENT_ID'), 
                                               client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'), redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI')))

"""
Method to load trusted IDs for user to interact with the bot via DM.
Users must manually add this ID which can be easily gotten by right clicking user profile > Copy User ID
"""
def load_trusted_ids(trusted_users):
    users = str(TRUSTED_USERS).strip()
    
    if users and "," in users:
        users_result = users.split(",")
        for user in users_result:
            trusted_users.append(user.strip())
    elif users:
        trusted_users.append(users)

#TODO JSON caching
#Overview: This is necessary to track playlist data so duplicate songs can't be spammed or readded over and over. Optional parameter in .env to setup
#1. Upon startup, parse directory of JSON files to get tracked server IDs
#2. Evaluate which values are necessary for JSON structure
    #a. snapshot_id of playlist
    #b. track data
    #c. playlists to add to for each server
    #d. ???
#2. Load into memory to check if valid server to track in on_message
#3. Upon using !add command, generate JSON objects based on the returned info
#4. fast-update parameter to only append to end of track data without reparsing entire playlist, see: https://github.com/spotipy-dev/spotipy/issues/601#issuecomment-720005356
    #a. save index location in JSON to start parse from

@bot.event
async def on_ready():
    print(f'Ready to go as {bot.user}')
    load_trusted_ids(trusted_users)

@bot.command()
@commands.dm_only()
async def add(ctx, location: str):
    if str(ctx.message.author.id) in trusted_users:
        
        #Get servers user is in
        if location == "server":
            available_servers = "Respond with the number of the server you want to add.\n"

            for idx, server in enumerate(bot.guilds):
                available_servers += str(idx) + ". " + server.name + "\n"
            await ctx.send(available_servers)

            def check(m):
                return m.channel == ctx.channel and m.content.isdigit() == True and m.content in available_servers 
                #user could paste a number in the message that isn't a valid index but is in a server name, but at that point it is willful misuse

            response = await bot.wait_for("message", check=check)

            available_channels = "Respond with the number of the channel in the server you want to add.\n"

            for idx, server in enumerate(bot.guilds):
                if int(response.content) == idx:
                    for idx, channel in enumerate(server.text_channels):
                        available_channels += str(idx) + ". " + channel.name + "\n"
            await ctx.send(available_channels)

            def check2(m):
                return m.channel == ctx.channel and m.content.isdigit() == True and m.content in available_channels
        
            response = await bot.wait_for("message", check=check2)

            for idx, channel in enumerate(server.text_channels):
                if int(response.content) == idx:
                    id = channel.id
                    #TODO add ID to JSON files that are generated

        #TODO add logic for if user wants to track a DM
        #elif arg == "dm":

        #TODO add logic for if user wanst to track a group chat (up to 10 people)
        #elif arg == "gc"

        #TODO add logic in each method to prevent already added channels from showing up in list
        #TODO add logic to remove tracked servers and DMs from listing
        #TODO add logic to remove server from being listed if all text channels are already tracked


@bot.event
async def on_message(message):

    if message.author == bot.user: #make sure message is sent from someone besides oneself
        return        
    if re.search(spotify_url_regex, str(message.content)): #regex to detect if a link is a specific spotify track list
        await add_tracks_to_playlist(message)
    await bot.process_commands(message)

"""
Method to add tracks to a given playlist.
Will loop through all various song links pasted in the chat
"""
async def add_tracks_to_playlist(message):
    playlist_id = os.getenv("SINGLE_PLAYLIST_ID") #for now, only supporting for one playlist -- #TODO add multiplaylist support after JSON setup
    matches = re.findall(spotify_url_regex, str(message.content))
    track_uris = []
    for match in matches:
        track_id = match[2] #track URI is third index in tuple
        if '?si' in track_id: #data cleaning for if ?si is included in link
            splitted = track_id.split('?')
            track_id = splitted[0]
        track_uris.append(track_id)
    await sp.playlist_add_items(playlist_id, track_uris)
    
bot.run(os.getenv('DISCORD_TOKEN'), log_handler=handler)