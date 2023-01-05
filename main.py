import discord
import game
from decouple import config


#create discord client
client_key = config('PICTIONARY_AI_KEY')
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

#create game
Game = game.Game()


#game channel temp
game_channel = None
voice_channel = None
status = True
#start up client
@client.event
async def on_ready():
    #get game channel
    global game_channel
    global voice_channel
    global Game

    channels = client.get_all_channels()
    for channel in channels:
        if channel.name == 'pictionary-channel':
            game_channel = channel
        elif channel.name == 'Pictionary':
            voice_channel = channel
    
    await game_channel.send(f"This is the designated game channel, join {voice_channel} to participate in a game with the command \"$start game\"")

    Game.initiate(game_channel, voice_channel, client)

    print("logged in as {0.user}".format(client))

#get messages
@client.event
async def on_message(message):
    global status
    global Game
    global game_channel
    global voice_channel
    #ignore messges from bot
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Welcome!')

    if message.content.startswith("$start game"):
        #get game channel from users
        print(game_channel)

        if (status == True):
            status = False
            status = await Game.run()
        else:
            print("game running already")

@client.event
async def on_voice_state_update(member, before, after):
    global Game
    global game_channel

    print (after.channel)

    if after.channel == voice_channel:
        Game.add_player(member)

    elif after.channel != voice_channel:
        Game.remove_player(member)
    


#start client
client.run(client_key)