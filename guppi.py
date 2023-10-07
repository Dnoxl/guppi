#Version: Alpha 0.0.1
import discord
import os
import time
import asyncio
import sqlite3
import sys
import datetime
import inspect
import logging
import traceback
from pathlib import Path
from discord.ext import commands, tasks
from discord.ext.commands import MissingPermissions, NotOwner

logname = Path(sys.path[0], 'bot.log')

logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger()

global bot_starttime
bot_starttime = time.perf_counter()

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

class StartupTimes:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_startup()

    # Initialize the database if it doesn't exist
    def init_startup(self):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS startup_times
                        (startup_time REAL)''')
            con.commit()

    # Retrieve the startup times from the database
    def retrieve_startup_times(self):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT startup_time FROM startup_times')
            return [row[0] for row in c.fetchall()]

    # Update the startup times in the database
    def update_startup_times(self, new_time):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('INSERT INTO startup_times (startup_time) VALUES (?)', (new_time,))
            con.commit()

    # Check if a setting exists in the database
    def clear_startup_times(self):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('DELETE FROM startup_times')
            con.commit()

class Settings:
    def __init__(self):
        self.db_path = Path(sys.path[0], 'bot.db')
        self.init_settings()
        self.bottoken = self.retrieve_setting(setting='bottoken')
        self.statuschannel_id = self.retrieve_setting(setting='statuschannel_id')

    def init_settings(self):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            settings = ['bottoken', 'statuschannel_id']
            setup_vars = ['bottoken', 'statuschannel_id']
            default_settings = ['Invalid', 'Invalid']
            c.execute('CREATE TABLE IF NOT EXISTS settings(setting TEXT, value TEXT)')
            con.commit()
            for s in settings:
                if not self.check_setting(s):
                    c.execute('INSERT INTO settings (setting) VALUES (?)', (s,))
                    con.commit()
        for i, s in enumerate(setup_vars):
            while True:
                if not self.check_setting(s) or self.retrieve_setting(s) is None:
                    val = input(f'{s}:')
                    if val == '':
                        if default_settings[i] == 'Invalid':
                            continue
                        val = default_settings[i]
                    self.update_settings(val, s)
                    print(f'Added {s}: {val}\n')
                break     
    
    def check_setting(self, setting: str) -> bool:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT * FROM settings WHERE setting =?', (setting,))
            result = c.fetchone()
            return result is not None and result[0] is not None

    def retrieve_setting(self, setting: str) -> str:
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT value FROM settings WHERE setting =?', (setting,))
            return c.fetchone()[0]
    
    def update_settings(self, value: str, setting: str):
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            if not self.check_setting(setting):
                c.execute('INSERT INTO settings (setting, value) VALUES (?, ?)', (setting, value))
            else:
                c.execute('UPDATE settings SET value = ? WHERE setting = ?', (value, setting))
            con.commit()

@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, MissingPermissions):
            await ctx.respond('You do not have the necessary Permission(s).', ephemeral=True, delete_after=10)
        if isinstance(error, NotOwner):
            await ctx.respond('You do not have the necessary Permission(s).', ephemeral=True, delete_after=10)
    except:logger.error(traceback.format_exc())

# On ready event
@bot.event
async def on_ready():
    global botversion
    with open(Path(sys.path[0],os.path.basename(__file__)), 'r') as f:
        l1 = f.readlines(1)
        botversion = l1[0].strip('#Version: \n')
    print(f'Version: {botversion}, Logged on as {bot.user}')
    logger.info(f'Version: {botversion}, Logged on as {bot.user}')  
    version_control.start()  
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Users'))
    await status_msg()

# Handles the Status's button to kill the bot
class MyView(discord.ui.View):
    @discord.ui.button(label="Killbot", style=discord.ButtonStyle.danger)
    @commands.is_owner()
    async def button_callbackkillbot(self, button, interaction):
        try:
            await interaction.response.defer()
            await interaction.message.delete()
            print("Bot Closed")
            logger.info("Bot Closed")
            await bot.close()
            sys.exit(0)
        except:logger.error(traceback.format_exc())
    @discord.ui.button(label="Restart", style=discord.ButtonStyle.danger)
    @commands.is_owner()
    async def button_callbackrestart(self, button: discord.Button, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await interaction.message.delete()
            logger.info('Restarting')
            await restart(None)
        except:logger.error(traceback.format_exc())

# Displays the status of the bot
async def status_msg():
    startup = StartupTimes(Path(sys.path[0], "bot.db"))
    settings = Settings()
    chan = bot.get_channel(settings.statuschannel_id) or await bot.fetch_channel(settings.statuschannel_id)
    messages = await chan.history(limit=None).flatten()
    if len(messages) != 0:
        for msg in messages:
            if msg.author == bot.user:
                await msg.delete()
    bot_readytime = time.perf_counter()
    load_time = round(bot_readytime - bot_starttime, 2)
    load_times = startup.retrieve_startup_times()
    load_times.append(load_time)
    if len(load_times) > 3:
        while len(load_times) > 3:
            load_times.pop(0)
    startup.clear_startup_times()
    for lt in load_times:
        startup.update_startup_times(lt)
    avg_load_time = round(sum(load_times)/len(load_times),2)
    text = f'Bot was ready in: {load_time}s\nAvg. time until ready: {avg_load_time}s'
    embed=discord.Embed(colour=0x2ecc71)
    embed.add_field(name='Performance Information:', value=text)
    embed.set_footer(
        text=f'Uptime: {str(datetime.timedelta(seconds=int(time.perf_counter() - bot_starttime)))}'
    )
    msg = await chan.send(embed=embed,view=MyView())
    execs = []
    avgexectime = 0
    delay = 5
    while True:
        await asyncio.sleep(delay)
        s = time.perf_counter()
        text = f'Bot was ready in: {load_time}s\nAvg. time until ready: {avg_load_time}s'
        embed=discord.Embed(colour=0x2ecc71)
        embed.add_field(name='Performance Information:', value=text)
        embed.set_footer(
            text=f'Uptime: {str(datetime.timedelta(seconds=int(time.perf_counter() - bot_starttime)))}'
        )
        try:
            await msg.edit(embed=embed,view=MyView())
        except discord.NotFound:
            msg = await chan.send(embed=embed,view=MyView())
        except:
            logger.error(traceback.format_exc())
        e = time.perf_counter()
        execs.append(e - s)
        execs.pop(0) if len(execs) > 10 else None
        avgexectime = round(sum(execs) / len(execs), 5)
        delay = 5 - avgexectime if avgexectime <= 5 else avgexectime

@tasks.loop(seconds=10)
async def version_control():
    with open(Path(sys.path[0],os.path.basename(__file__)), 'r') as f:
        l1 = f.readlines(1)
        version = l1[0].strip('#Version: \n')
    if version and botversion != version:
        os.system('cls') if sys.platform == 'win32' else os.system('clear')
        print(f'Updated {bot.user.name}:\nbefore: {botversion}\nafter: {version}\n')
        os.execv(sys.executable, ['python'] + sys.argv)

@bot.slash_command(name='restart', guilds=[1109530644578582590], guild_only=True)
@commands.is_owner()
async def restart(ctx=None):
    if ctx is not None:
        await ctx.defer()
    await bot.change_presence(activity=discord.Game('Restarting'), status=discord.Status.idle)
    os.execv(sys.executable, ['python'] + sys.argv)

# runs the bot
def run():
    with open(Path(sys.path[0], 'bot.log'), 'a', encoding='utf-8') as f:
        f.write(f"\n\n-----{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}-----\n")
    settings = Settings() 
    bottoken = settings.bottoken
    del settings
    bot.load_extension('cogs.generalutility')
    bot.load_extension('cogs.aboutme')
    bot.load_extension('cogs.automod')
    bot.run(bottoken)
run()
