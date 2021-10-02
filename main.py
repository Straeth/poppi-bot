import discord
import asyncio
import os
import math
import random
import requests
import json
import urllib.parse, urllib.request, re
from discord.ext import commands
from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
from keep_alive import keep_alive

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True', 'download_archive': 'archive.txt'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

intents = discord.Intents().default()
intents.members = True
client = commands.Bot(command_prefix='-', intents=intents)

queues = {}
queueTitles = {}
queueDuration = {}
currentQueue = {}
shuffleTrigger = {}
loopTrigger = {}
jumpTrigger = {}

def check_queue(ctx, id):
  global currentQueue   
  global jumpTrigger    
  if ((loopTrigger[id] == True) and (currentQueue[id] >= len(queues[id]))):
    currentQueue[id] = 0
  if (shuffleTrigger[id] == True and jumpTrigger[id] == False):
    currentQueue[id] = random.randint(0, len(queues[id]) - 1)
  if 0 <= currentQueue[id] < len(queues[id]):
    voice = ctx.guild.voice_client
    URL = queues[id][currentQueue[id]]
    voice.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda x=None: check_queue(ctx, id))  
    currentQueue[id]+=1
    jumpTrigger[id] = False
    client.loop.create_task(currently_playing(ctx, id))
  client.loop.create_task(play_state(ctx))

def get_quote():
  response = requests.get("https://zenquotes.io/api/random")
  json_data = json.loads(response.text)
  quote = json_data[0]['q'] + " -" + json_data[0]['a']
  return(quote)

def append_queue(ctx, URL, title, duration):
  guild_id = ctx.message.guild.id
  if (guild_id in queues):
    queues[guild_id].append(URL)
    queueTitles[guild_id].append(title) 
    queueDuration[guild_id].append(duration)   
  else:
    queues[guild_id] = [URL]
    queueTitles[guild_id] = [title]
    queueDuration[guild_id] = [duration]

def insert_one(info, ctx) :
    URL = info['url']
    title = info['title']
    duration = info['duration']        
    append_queue(ctx, URL, title, duration)

def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

def youtubeurl(url):
  if not 'youtube.com' in url:   
    query_string = urllib.parse.urlencode({'search_query': url})
    htm_content = urllib.request.urlopen(
      'http://www.youtube.com/results?' + query_string
    )
    search_results = re.findall(r'/watch\?v=(.{11})', htm_content.read().decode())
    url = 'http://www.youtube.com/watch?v=' + search_results[0]
  with YoutubeDL(YDL_OPTIONS) as ydl:
    info = ydl.extract_info(url, download=False)

  return info

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.command(brief='Remnant of when the bot was first created. Try the command out.')
async def inspire(ctx):
  quote = get_quote()
  await ctx.send(quote)

@client.command(brief='Play command.', description='Plays the audio of the requested video from a youtube URL. URL can also be a playlist.')
async def play(ctx, *, url):
  global loopTrigger
  global shuffleTrigger
  global currentQueue
  voice = get(client.voice_clients, guild=ctx.guild)  
  id = ctx.message.guild.id

  if ctx.author.voice:     
    channel = ctx.message.author.voice.channel
    if (not (voice and voice.is_connected)):
      currentQueue[id] = 0
      loopTrigger[id] = False
      shuffleTrigger[id] = False 
      voice = await channel.connect()
      embed = discord.Embed(title="Notice",description=f"Poppi successfully connected to **{channel}**", color=discord.Color.blurple())
      await ctx.send(embed=embed)
      if id in queues:           
        queues[id].clear()
        queueTitles[id].clear()
        queueDuration[id].clear()
    if (channel == ctx.voice_client.channel):
      info = youtubeurl(url)
      i = 0
      if (('playlist' in url) | voice.is_playing()):
        if not 'playlist' in url:
          insert_one(info, ctx)
          embed = discord.Embed(title="Queue Details",description="Queued " + "**_" + info['title'] + "_**" + " as requested by " + f"**{ctx.author.name}**", color=discord.Color.blurple())
        else:     
          for a in info.get('entries'):   
            URL = info['entries'][i]['url']
            title = info['entries'][i]['title'] 
            duration = info['entries'][i]['duration']           
            append_queue(ctx, URL, title, duration)     
            i+=1
          embed = discord.Embed(title="Queue Details",description="Queued " + str(i) + " songs as requested by " + f"**{ctx.author.name}**", color=discord.Color.blurple())       
      else:
        insert_one(info, ctx)
        embed = discord.Embed(title="Song Request",description="Queued " + "**_" + info['title'] + "_**" + " as requested by " + f"**{ctx.author.name}**", color=discord.Color.blurple())
      if not voice.is_playing():
        check_queue(ctx, id)
    else:
      embed = discord.Embed(title="Notice", description="Poppi is currently playing on another channel.", color=discord.Color.blurple())    
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Queue command.', description='Shows the current playlist.')
async def queue(ctx):
  id = ctx.message.guild.id
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  if ctx.author.voice and voice_client:  
    if (id in queues and len(queues[id]) > 0):
      contents = []
      b = 0
      for a in range(math.ceil(len(queues[id])/10)):    
        fill = ""
        for i in range(10):
          if (0 <= b < len(queues[id])):
            fill += str(b + 1) + ".) **" + queueTitles[id][b] + "**"
            b+=1
            if b == currentQueue[id]:
              fill += " _(Now Playing)_"
            fill += "\n"
        contents.append(fill)
      curPage = 1
      embed = discord.Embed(title="Playlist", description=f"\n\n{contents[curPage-1]}\n\n_Page {curPage} of {a+1}_", color=discord.Color.blurple())
      message = await ctx.send(embed=embed)

      await message.add_reaction("⏪")
      await message.add_reaction("⏩")

      def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⏪", "⏩"]

      while True:
        try:
          reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)

          if str(reaction.emoji) == "⏩" and curPage != (a+1):
            curPage += 1
            embed = discord.Embed(title="Playlist", description=f"\n\n{contents[curPage-1]}\n\n_Page {curPage} of {a+1}_", color=discord.Color.blurple())
            await message.edit(embed=embed)
            await message.remove_reaction(reaction, user)
          elif str(reaction.emoji) == "⏪" and curPage > 1:
            curPage -= 1
            embed = discord.Embed(title="Playlist", description=f"\n\n{contents[curPage-1]}\n\n_Page {curPage} of {a+1}_", color=discord.Color.blurple())
            await message.edit(embed=embed)
            await message.remove_reaction(reaction, user)
          else:
            await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
          await message.delete()
          break
    else:
      embed = discord.Embed(title="Playlist", description="Queue is empty, there is nothing to be shown.", color=discord.Color.blurple())
      await ctx.send(embed=embed)
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
    await ctx.send(embed=embed)

@client.command(brief='Jump command.', description='Followed by a number. Jumps to the requested song in a playlist.')
async def jump(ctx, position):
  global currentQueue  
  global jumpTrigger
  id = ctx.message.guild.id
  voice = get(client.voice_clients, guild=ctx.guild)  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  if ctx.author.voice and voice_client:
    if (id in queues and len(queues[id]) > 0):
      if (is_integer(position)):
          if (int(position) > 0 and int(position) <= len(queues[id])):
            jumpTrigger[id] = True
            currentQueue[id] = int(position) - 1
            if voice.is_playing():
              voice.stop()    
            else:
              check_queue(ctx, ctx.message.guild.id)
          else:
            embed = discord.Embed(title="Notice", description="Invalid position. Poppi can only jump to a certain song that's among the ones listed via the **-queue** command.", color=discord.Color.blurple())
            await ctx.send(embed=embed)
      else:
        embed = discord.Embed(title="Notice", description="Jump command should be followed by a number.", color=discord.Color.blurple())
        await ctx.send(embed=embed)
    else:
      embed = discord.Embed(title="Playlist", description="Queue is empty, there is no where to jump.", color=discord.Color.blurple())
      await ctx.send(embed=embed)
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
    await ctx.send(embed=embed)

@client.command(brief='Stop command.', description='Stops the playback.')
async def stop(ctx):
  global currentQueue
  id = ctx.message.guild.id
  voice = get(client.voice_clients, guild=ctx.guild)  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  if ctx.author.voice and voice_client:    
    if voice.is_playing():
      currentQueue[id] = len(queues[ctx.message.guild.id])
      voice.stop()
      embed = discord.Embed(title="Notice", description=f"Playback stopped by {ctx.author.name}.", color=discord.Color.blurple())
    else:
      embed = discord.Embed(title="Notice", description=f"Playback already stopped.", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Loop command.', description='Loops the entire playlist.')
async def loop(ctx):
  global loopTrigger    
  id = ctx.message.guild.id
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  if ctx.author.voice and voice_client:
    if shuffleTrigger[id] == False:
      if loopTrigger[id] == False:
        loopTrigger[id] = True
        embed = discord.Embed(title="Notice", description="Now looping playlist.", color=discord.Color.blurple())
      else:
        loopTrigger[id] = False
        embed = discord.Embed(title="Notice", description="Looping disabled.", color=discord.Color.blurple())
    else:
      embed = discord.Embed(title="Notice", description="Cannot loop playlist when shuffle is enabled.", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Remove command.', description='Followed by a number. Removes the specific song from the playlist.')
async def remove(ctx, position):
  id = ctx.message.guild.id  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  if ctx.author.voice and voice_client:
    if (id in queues and len(queues[id]) > 0):
      if (position == 'last'):
        position = str(len(queues[id]))
      if (is_integer(position)):
        if (int(position) > 0 and int(position) <= len(queues[id])):
          embed = discord.Embed(title="Notice", description="Removed " + "**" + queueTitles[id][int(position) - 1] + "**", color=discord.Color.blurple())
          queues[id].pop(int(position) - 1)
          queueTitles[id].pop(int(position) - 1)
          queueDuration[id].pop(int(position) - 1)
        else:
          embed = discord.Embed(title="Notice", description="Invalid position. Poppi can only remove a certain song that's among the ones listed via the **-queue** command.", color=discord.Color.blurple())
      else:
        embed = discord.Embed(title="Notice", description="Remove command should be followed by a number.", color=discord.Color.blurple())
    else:
      embed = discord.Embed(title="Notice", description="Queue is empty, there is nothing to remove.", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Skip command.', description='Skips the current song.')
async def skip(ctx):  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)  
  id = ctx.message.guild.id  
  if ctx.author.voice and voice_client:
    voice = get(client.voice_clients, guild=ctx.guild) 
    if voice.is_playing():
      if (id in queues and len(queues[id]) > 0):  
        if ((currentQueue[id] >= len(queues[id])) and loopTrigger[id] == False): 
          embed = discord.Embed(title="Notice", description="This is the last song in the playlist.", color=discord.Color.blurple())
        else:
          embed = discord.Embed(title="Notice", description=f"Skipped **_{queueTitles[ctx.message.guild.id][currentQueue[id] - 1]}_** as requested by **{ctx.author.name}**", color=discord.Color.blurple())
          voice.stop()
      else:
        embed = discord.Embed(title="Notice", description="Playlist is empty. There is nothing to skip to.", color=discord.Color.blurple())
    else:
      embed = discord.Embed(title="Notice", description="There is nothing to skip.", color=discord.Color.blurple())        
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Shuffle command.', description='Shuffles the entire playlist.')
async def shuffle(ctx):
  global shuffleTrigger
  global loopTrigger  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  id = ctx.message.guild.id
  if ctx.author.voice and voice_client:
    if (shuffleTrigger[id] == False):
      shuffleTrigger[id] = True
      if (loopTrigger[id] == True):
        loopTrigger[id] = False
        embed = discord.Embed(title="Notice", description="Shuffle on. Looping is now disabled.", color=discord.Color.blurple())
      else:
        embed = discord.Embed(title="Notice", description="Shuffle on", color=discord.Color.blurple())
    else:
      shuffleTrigger[id] = False      
      embed = discord.Embed(title="Notice", description="Shuffle off", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Force play command.', description='Stops the current song and forcibly plays the requested song instead. Requested song is not added to playlist. ***Not fully tested on all scenarios, might cause errors.')
async def fplay(ctx, *, url):
  global currentQueue
  voice = get(client.voice_clients, guild=ctx.guild)  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  info = youtubeurl(url)  
  id = ctx.message.guild.id
  if ctx.author.voice and voice_client:
    if voice.is_playing():
      if ('playlist' in url):
        embed = discord.Embed(title="Notice", description="This command can only be used on single videos and not playlists. If you wish to play another playlist, use the **_-clearpl_** command and then use **_-play_** afterwards.", color=discord.Color.blurple())
      else:
        tempQueue = currentQueue[id]
        currentQueue[id] = len(queues[ctx.message.guild.id])
        voice.stop()
        currentQueue[id] = tempQueue - 1
        voice2 = ctx.guild.voice_client
        voice2.play(FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS), after=lambda x=None: check_queue(ctx, ctx.message.guild.id))
        embed = discord.Embed(title="Notice", description=f"Current track has stopped as **_{info['title']}_** was force played by **{ctx.author.name}**.", color=discord.Color.blurple())
    else:
      embed = discord.Embed(title="Notice", description="This command can only be used when another track is playing. Use **_-play_** instead.", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)

@client.command(brief='Clear playlist command.', description='Clears the playlist.')
async def clearpl(ctx):  
  global currentQueue
  global loopTrigger
  global shuffleTrigger  
  toAdd = ""
  voice = get(client.voice_clients, guild=ctx.guild)  
  voice_client = get(ctx.bot.voice_clients, guild=ctx.guild)
  id = ctx.message.guild.id
  if ctx.author.voice and voice_client:
    if voice.is_playing():
      currentQueue[id] = len(queues[ctx.message.guild.id])
      voice.stop()
      currentQueue[id] = 0
      toAdd = "Current playback stopped. "
    loopTrigger[id] = False
    shuffleTrigger[id] = False
    queues[id].clear()
    queueTitles[id].clear()
    queueDuration[id].clear()
    embed = discord.Embed(title="Notice", description=toAdd + "Cleared playlist and defaulted the shuffle and loop options to **off**.", color=discord.Color.blurple())
  else:
    embed = discord.Embed(title="Notice", description="You and Poppi need to be connected to a voice channel to use that command.", color=discord.Color.blurple())
  await ctx.send(embed=embed)
  
async def play_state(ctx):
  voice = get(client.voice_clients, guild=ctx.guild)
  if voice:
    if voice.is_playing():
      await asyncio.sleep(1)
    else:
      await asyncio.sleep(300)
      if ((not voice.is_playing()) and voice.is_connected()):
        embed = discord.Embed(title="Notice", description="Poppi left the voice channel because Poppi was ignored. Call Poppi back when you need Poppi, okay?", color=discord.Color.blurple())
        await voice.disconnect()
        await ctx.send(embed=embed)

async def currently_playing(ctx, id):
  if 0 <= (currentQueue[id]-1) < len(queueTitles[id]):
    embed = discord.Embed(title="Notice", description="Now playing " + "**" + queueTitles[id][currentQueue[id]-1] + "**", color=discord.Color.blurple())
    notice = await ctx.send(embed=embed)
    await asyncio.sleep(queueDuration[id][currentQueue[id]-1])
    await notice.delete()

@client.event
async def on_voice_state_update(member, before, after):  
  voice_state = member.guild.voice_client

  if voice_state is None:
    return 
  if len(voice_state.channel.members) == 1 and member != client.user:
    await asyncio.sleep(60)
    await voice_state.disconnect()
    embed = discord.Embed(title="Notice", description="Poppi left the voice channel because Poppi was left alone. Call Poppi back when you come back, okay?", color=discord.Color.blurple())      
    await member.guild.system_channel.send(embed=embed)
    
keep_alive()
client.run(os.environ['TOKEN'])
