import os
import sys
import io
import discord
import sqlite3
import re
import datetime
import traceback
import logging
from collections import OrderedDict
from discord.ext import commands, tasks
from discord.commands import slash_command, Option, user_command
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

logger = logging.getLogger()

class ConfigAboutme(discord.ui.View):  
    def __init__(self, user_id:int):
        try:
            self.user_id = user_id
            super().__init__(timeout=30)
            self.db_path = Path(sys.path[0], 'bot.db')
            infos = ['name', 'birthday', 'country', 'hobbies']
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for info in infos:
                    if not check_info(info, user_id):
                        c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user_id, info,))
                con.commit()
                self.remops = [row[0] for row in c.execute('SELECT info FROM aboutme WHERE user_id = ? AND toggle = 1',(user_id,)).fetchall()]
                self.addops = [row[0] for row in c.execute('SELECT info FROM aboutme WHERE user_id = ? AND toggle = 0',(user_id,)).fetchall()]
            self.aoptions = []
            self.roptions = []
            if self.addops:
                self.aoptions.extend(discord.SelectOption(label=info, value=info) for info in self.addops)
                self.addselect.options = self.aoptions
            else:
                self.addselect.disabled = True
            if self.remops:
                self.roptions.extend(discord.SelectOption(label=info, value=info) for info in self.remops)
                self.removeselect.options = self.roptions
            else:
                self.removeselect.disabled = True
        except:logger.error(traceback.format_exc())
    
    @discord.ui.select(placeholder='Add a field to your Aboutme', options=[discord.SelectOption(label='Select an option', value='Placeholder')], row=0)
    async def addselect(self, select, interaction):
        try:
            select.disabled=False
            selval = select.values[0]
            with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
                c = con.cursor()
                c.execute('UPDATE aboutme SET toggle = ? WHERE user_id = ? AND info = ?', (1, self.user_id, selval,))
                con.commit()
            self.aoptions = [option for option in self.aoptions if option.value != selval]
            self.addselect.options = self.aoptions
            await interaction.response.edit_message(view=ConfigAboutme(self.user_id))
        except:logger.error(traceback.format_exc())

    @discord.ui.select(placeholder='Remove a field from your Aboutme', options=[discord.SelectOption(label='Select an option', value='Placeholder')], row=1)
    async def removeselect(self, select, interaction):
        try:
            select.disabled=False
            selval = select.values[0]
            with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
                c = con.cursor()
                c.execute('UPDATE aboutme SET toggle = ? WHERE user_id = ? AND info = ?', (0, self.user_id, selval,))
                con.commit()
            self.roptions = [option for option in self.roptions if option.value != selval]
            self.removeselect.options = self.roptions
            await interaction.response.edit_message(view=ConfigAboutme(self.user_id))
        except:logger.error(traceback.format_exc())
    
class AboutModal(discord.ui.Modal):
    def __init__(self, user_id:int):
        self.db_path = Path(sys.path[0], 'bot.db')
        self.user_id = user_id
        super().__init__(title='About you:')
        infos = ['name', 'birthday', 'country', 'hobbies']
        info_dict = OrderedDict()
        try:
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for info in infos:
                    if not check_info(info, user_id):
                        c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (self.user_id, info,))
                con.commit()
                rows = list(
                    c.execute(
                        'SELECT info, value FROM aboutme WHERE user_id = ? AND toggle = 1',
                        (self.user_id,),
                    ).fetchall()
                )
                for row in rows:
                    info, value = row
                    info_dict[info] = value
                info_dict = OrderedDict((info, info_dict[info]) for info in infos if info in info_dict)
            for info in info_dict.keys():
                if info == 'birthday':
                    label = info
                    label += '(dd.mm.yyyy)'
                    self.add_item(discord.ui.InputText(label=label, value=info_dict[info]))
                    continue
                self.add_item(discord.ui.InputText(label=info, value=info_dict[info]))
        except:logger.error(traceback.format_exc())
            
    async def callback(self, interaction):
        try:
            values = {}
            for child in self.children:
                if isinstance(child, discord.ui.InputText):
                    if 'birthday' in child.label:
                        child.label = child.label.replace('(dd.mm.yyyy)', '')
                    values[child.label] = child.value
            embed = discord.Embed()
            embed.set_author(
                name=f'About me of {interaction.user.display_name}',
                icon_url=interaction.user.avatar,
            )
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                for value in values:
                    c.execute('UPDATE aboutme SET value = ? WHERE info = ? AND user_id = ?', (values[value], value, self.user_id,))
                    if value == 'birthday' and values[value] is not None:
                        age = age_from_string(values[value])
                        if age is not None:
                            embed.add_field(name='age', value=age)
                    embed.add_field(name=value, value=values[value])
                con.commit()
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        except:logger.error(traceback.format_exc())

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path(sys.path[0], 'bot.db')
        with sqlite3.connect(self.db_path) as con:
            c = con.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
        
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            infos = ['name', 'birthday', 'country', 'hobbies']
            with sqlite3.connect(self.db_path) as con:
                c = con.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
                for user in self.bot.users:
                    for info in infos:
                        if not check_info(info, user.id):
                            c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user.id, info,))
                con.commit()
        except:logger.error(traceback.format_exc())

    aboutme = discord.SlashCommandGroup('aboutme')

    @aboutme.command(name='configure', description= 'Choose what information you want to display.')
    async def aboutme_config(self, ctx):
        user_id = ctx.author.id      
        try:
            await ctx.respond(view=ConfigAboutme(user_id=user_id), ephemeral=True, delete_after=30)
        except:logger.error(traceback.format_exc())

    @aboutme.command(name='write',description='Write some Information about yourself.')    
    async def update_aboutme(self, ctx):
        try:
            user_id = int(ctx.author.id)
            await ctx.send_modal(AboutModal(user_id))
        except:logger.error(traceback.format_exc())
        
    @user_command(name='Aboutme', cog='social')
    async def aboutme_user(self, ctx, user: discord.Member):
        try:
            embed = create_aboutme_embed(user)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())

    @aboutme.command(name='user', description='Show the Aboutme of another user.')
    async def about_user(self, ctx, 
                         user: Option(discord.Member, description='User whose Aboutme you want to see.')
                         ):
        try:
            embed = create_aboutme_embed(user)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())
        
    @aboutme.command(name='self', description='Show the About Me of yourself.')
    async def about_self(self, ctx: discord.ApplicationContext):
        try:
            user = ctx.author
            embed = create_aboutme_embed(user)
            await ctx.respond(embed=embed, delete_after=30)
        except:logger.error(traceback.format_exc())

    async def cog_command_error(self, ctx, error):
        try:
            if isinstance(error, MissingPermissions):
                await ctx.respond("You don't have permission to use this command.", ephemeral=True, delete_after=10)
            if isinstance(error, NotOwner):
                await ctx.respond("You are not my Owner.", ephemeral=True, delete_after=10)     
        except:logger.error(traceback.format_exc())   

def create_aboutme_embed(user: discord.User):
    try:
        infos = ['name', 'birthday', 'country', 'hobbies']
        info_dict = OrderedDict()
        embed = discord.Embed()
        age = ''
        with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
            c = con.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS aboutme (user_id INTEGER NOT NULL, info TEXT NOT NULL, value TEXT, toggle INTEGER DEFAULT 1 CHECK (toggle < 2), PRIMARY KEY (user_id, info))")
            for info in infos:
                if not check_info(info, user.id):
                    c.execute('INSERT INTO aboutme (user_id, info) VALUES (?,?)', (user.id, info,))
            con.commit()
            rows = list(
                c.execute(
                    'SELECT info, value FROM aboutme WHERE user_id = ? AND toggle = 1',
                    (user.id,),
                ).fetchall()
            )
            for row in rows:
                info, value = row
                info_dict[info] = value
            info_dict = OrderedDict((info, info_dict[info]) for info in infos if info in info_dict)
        for info in info_dict.keys():
            if info == 'birthday' and info_dict[info] is not None:
                age = age_from_string(info_dict[info])
                print(age)
                if age is not None:
                    embed.add_field(name='age', value=age)
            embed.add_field(name=info, value=info_dict[info])
        embed.set_author(
            name=f'About me of {user.display_name}', icon_url=user.avatar
        ) if user.avatar is not None else embed.set_author(
            name=f'About me of {user.display_name}'
        )
        return embed
    except:logger.error(traceback.format_exc())

def check_info(info: str, user_id:int) -> bool:
    try:
        with sqlite3.connect(Path(sys.path[0], 'bot.db')) as con:
            c = con.cursor()
            c.execute('SELECT * FROM aboutme WHERE info = ? AND user_id = ?', (info, user_id))
            result = c.fetchone()
            return result is not None and result[0] is not None
    except:logger.error(traceback.format_exc())

def age_from_string(date_string):
    try:
        pattern = r'^(0[1-9]|[12][0-9]|3[01])[./](0[1-9]|1[0-2])[./]\d{4}$'
        if re.match(pattern, date_string):
            day, month, year = map(int, re.split(r'[./]', date_string))
            birthdate = datetime.datetime(year, month, day)
            today = datetime.date.today()
            return (
                today.year
                - birthdate.year
                - ((today.month, today.day) < (birthdate.month, birthdate.day))
            )
        else:
            return None
    except:logger.error(traceback.format_exc())

def setup(bot):
    bot.add_cog(Social(bot))