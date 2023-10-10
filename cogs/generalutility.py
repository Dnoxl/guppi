"""
TODO: Add commands to display user/server information
"""

import os
import sys
import io
import discord
import logging
import traceback
import json
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

logger = logging.getLogger()

class Localization:
    def __init__(self, locale):
        """
        The function initializes an object with a given locale, loads a JSON file corresponding to that
        locale, and assigns localization values.
        """
        try:
            super().__init__()
            self.locale = locale
            self.file_name = os.path.basename(__file__).split('.py')[0]
            self.json_content = self.load_locale_file(locale)
            self.assign_localization()
        except:logger.error(traceback.format_exc())
    
    def load_locale_file(self, locale):
        try:
            if not os.path.exists(Path(sys.path[0], 'Localization', f'{locale}-locale.json')):
                locale = 'en-US'
            with open(Path(sys.path[0], 'Localization', f'{locale}-locale.json')) as f:
                j = json.loads(f.read())
            return j
        except:logger.error(traceback.format_exc())
        
    def assign_localization(self):
            try:
                base_content = self.json_content[self.file_name]
                for function, values in base_content.items():
                    setattr(self, function, self._NestedClass(values))
            except:logger.error(traceback.format_exc())

    class _NestedClass:
        def __init__(self, values):
            try:
                for k, v in values.items():
                    setattr(self, k, v)
            except:logger.error(traceback.format_exc())

class GeneralUtility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    utility = discord.SlashCommandGroup('utility')

    @utility.command(name='servericon', description='Fetches the servers Icon.')
    async def get_guildicon(self, ctx):
        try:
            await ctx.respond(ctx.guild.icon.url)
        except:logger.error(traceback.format_exc())

    @utility.command(name='useravatar', description='Fetches a users avatar.')
    async def get_avatar(self, ctx, member: Option(discord.Member)):
        try:
            await ctx.respond(member.avatar.url)
        except:logger.error(traceback.format_exc())

    @utility.command(name='clear',description='[Admin] Clears a specified amount of messages from the channel. ')
    @commands.has_permissions(administrator=True)
    #localization: deleted_message, deleted_messages
    async def clear_msgs(self, ctx:discord.ApplicationContext, amount: Option(int, description='The maximum amount of messages to clear.')):
        try:
            loc = Localization(ctx.locale)
            msgs = []
            async for msg in ctx.channel.history(limit=amount):
                    msgs.append(msg)
                    if len(msgs) == amount:
                        break
            if len(msgs) < amount:
                amount = len(msgs)
            if len(msgs) < amount:
                amount = len(msgs)
            if amount == 1:
                await ctx.respond(loc.clear_msgs.deleted_message,ephemeral=True)
            else:
                await ctx.respond(loc.clear_msgs.deleted_messages.format(amount),ephemeral=True)
            await ctx.channel.purge(limit=amount)   
        except:logger.error(traceback.format_exc())
        
    #localization: MissingPermissions, NotOwner
    async def cog_command_error(self, ctx, error):
        """
        The function `cog_command_error` handles errors that occur during command execution and sends an
        appropriate response based on the type of error.
        """
        try:
            loc = Localization(ctx.locale)
            if isinstance(error, MissingPermissions):
                await ctx.respond(loc.cog_command_error.MissingPermissions, ephemeral=True)
            if isinstance(error, NotOwner):
                await ctx.respond(loc.cog_command_error.NotOwner, ephemeral=True)
        except:logger.error(traceback.format_exc())
            
def setup(bot):
    bot.add_cog(GeneralUtility(bot))