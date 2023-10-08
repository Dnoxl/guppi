#Version: Alpha 0.0.1
import discord
import os
import time
import asyncio
import sqlite3
import sys
import datetime
import logging
import traceback
from pathlib import Path
from discord.ext import commands, tasks
from discord.ext.commands import MissingPermissions, NotOwner

# This section of code is responsible for setting up logging for the bot.
logname = Path(sys.path[0], 'bot.log')

logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger()

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

# The `StartupTimes` class provides methods for initializing, retrieving, updating, and clearing
# startup times stored in a SQLite database.
class StartupTimes:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_startup()

    def init_startup(self):
        """
        The function initializes a SQLite database table for storing startup times if it doesn't already
        exist.
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS startup_times
                        (startup_time REAL)''')
            con.commit()

    def retrieve_startup_times(self):
        """
        The function retrieves the startup times from a SQLite database.
        :return: a list of startup times retrieved from the "startup_times" table in the SQLite
        database.
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT startup_time FROM startup_times')
            return [row[0] for row in c.fetchall()]
        
    def update_startup_times(self, new_time):
        """
        The function updates the startup times in a SQLite database with a new time value.
        
        :param new_time: The `new_time` parameter is the value representing the startup time that you
        want to insert into the `startup_times` table in the database
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('INSERT INTO startup_times (startup_time) VALUES (?)', (new_time,))
            con.commit()

    def clear_startup_times(self):
        """
        The function clears all the startup times stored in a SQLite database.
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('DELETE FROM startup_times')
            con.commit()

# The `Settings` class is a Python class that manages settings stored in a SQLite database.
class Settings:
    def __init__(self):
        """
        The function initializes the class instance with the necessary attributes.
        """
        self.db_path = Path(sys.path[0], 'bot.db')
        self.init_settings()
        self.bottoken = self.retrieve_setting(setting='bottoken')
        self.statuschannel_id = self.retrieve_setting(setting='statuschannel_id')

    def init_settings(self):
        """
        The function initializes settings in a SQLite database, prompts the user for input if the
        settings are missing or invalid, and updates the settings accordingly.
        """
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
        """
        The function checks if a given setting exists in a SQLite database table and returns a boolean
        value indicating its presence.
        
        :param setting: The "setting" parameter is a string that represents the name of the setting you
        want to check in the database
        :type setting: str
        :return: a boolean value. It returns True if the specified setting exists in the database table
        "settings" and has a non-null value, and False otherwise.
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT * FROM settings WHERE setting =?', (setting,))
            result = c.fetchone()
            return result is not None and result[0] is not None

    def retrieve_setting(self, setting: str) -> str:
        """
        The function retrieves the value of a specific setting from a SQLite database.
        
        :param setting: The "setting" parameter is a string that represents the name of the setting you
        want to retrieve from the database
        :type setting: str
        :return: the value of the specified setting from the database.
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute('SELECT value FROM settings WHERE setting =?', (setting,))
            return c.fetchone()[0]
    
    def update_settings(self, value: str, setting: str):
        """
        The function updates a setting in a SQLite database with a given value.
        
        :param value: The `value` parameter is the new value that you want to update for the specified
        setting. It is of type `str`
        :type value: str
        :param setting: The "setting" parameter is a string that represents the name of the setting to
        be updated or inserted into the database
        :type setting: str
        """
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            if not self.check_setting(setting):
                c.execute('INSERT INTO settings (setting, value) VALUES (?, ?)', (setting, value))
            else:
                c.execute('UPDATE settings SET value = ? WHERE setting = ?', (value, setting))
            con.commit()

# The `MyView` class is a Discord UI view that contains two buttons, one for killing the bot and one
# for restarting it, both of which require the owner's permission.
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

async def status_msg():
    """
    The `status_msg` function updates the performance information of a bot in a Discord channel and
    calculates the average load time.
    """
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
    """
    The function `version_control` checks the version of the current file and restarts the program if a
    new version is detected.
    """
    try:
        with open(Path(sys.path[0],os.path.basename(__file__)), 'r') as f:
            lines = f.readlines(1)
            file_version = lines[0].strip('#Version: \n')
        if file_version and current_version != file_version:
            os.system('cls') if sys.platform == 'win32' else os.system('clear')
            print(f'Updated {bot.user.name}:\nbefore: {current_version}\nafter: {file_version}\n')
            os.execv(sys.executable, ['python'] + sys.argv)
    except:logger.error(traceback.format_exc())

async def restart():
    """
    The function restarts the bot by changing its presence to "Restarting" and then executing the
    Python script again.
    """
    try:
        await bot.change_presence(activity=discord.Game('Restarting'), status=discord.Status.idle)
        os.execv(sys.executable, ['python'] + sys.argv)
    except:logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    """
    The function `on_command_error` handles different types of errors and sends appropriate responses
    based on the error type.
    
    :param ctx: The `ctx` parameter is an object representing the context of the command being executed.
    It contains information such as the message, the author, the channel, and the guild
    :param error: The `error` parameter is the exception that was raised when a command encountered an
    error. It can be any type of exception, such as `MissingPermissions` or `NotOwner`
    """
    try:
        if isinstance(error, MissingPermissions):
            await ctx.respond('You do not have the necessary Permission(s).', ephemeral=True, delete_after=10)
        if isinstance(error, NotOwner):
            await ctx.respond('You do not have the necessary Permission(s).', ephemeral=True, delete_after=10)
    except:logger.error(traceback.format_exc())

@bot.event
async def on_ready():
    """
    The `on_ready` function is responsible for setting up the bot's initial state, as
    well as displaying the current version and setting a custom status.
    """
    try:
        global current_version
        with open(Path(sys.path[0],os.path.basename(__file__)), 'r') as f:
            l1 = f.readlines(1)
            current_version = l1[0].strip('#Version: \n')
        print(f'Version: {current_version}, Logged on as {bot.user}')
        logger.info(f'Version: {current_version}, Logged on as {bot.user}')  
        version_control.start()  
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.custom,
                name="Custom Status",
                state=bot_status,
            )
        )
        await status_msg()
    except:logger.error(traceback.format_exc())

def run():
    """
    The function runs a bot by loading extensions and running it with the bot token.
    """
    with open(Path(sys.path[0], 'bot.log'), 'a', encoding='utf-8') as f:
        f.write(f"\n\n-----{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}-----\n")
    settings = Settings()
    for extension in bot_extensions:     
        bot.load_extension(extension)
    bot.run(settings.bottoken)

global bot_starttime, bot_status, bot_extensions
bot_starttime = time.perf_counter()
bot_status = "Undergoing maintenance"
bot_extensions = ('cogs.generalutility', 'cogs.aboutme', 'cogs.automod')

#Declare all necessary Variables before this
run()