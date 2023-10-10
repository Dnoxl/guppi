"""
TODO: Make Code 
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

# The above class is a localization class that loads a JSON file containing localization data and
# assigns the data to class attributes.
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

class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        loc = Localization('de')

    @commands.Cog.listener()
    #localization
    async def on_guild_join(self, guild:discord.Guild):
        print(guild.id, guild.name)

def setup(bot):
    bot.add_cog(ServerSetup(bot))