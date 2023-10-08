"""
TODO: Add commands to display user/server information
"""

import os
import sys
import io
import discord
import logging
import traceback
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.ext.commands import MissingPermissions, NotOwner
from pathlib import Path

logger = logging.getLogger()

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
    async def clear_msgs(self, ctx, amount: Option(int, description='The maximum amount of messages to clear.')):
        try:
            msgs = []
            async for msg in ctx.channel.history(limit=am):
                    msgs.append(msg)
                    if len(msgs) == am:
                        break
            if len(msgs) < am:
                am = len(msgs)
            if len(msgs) < am:
                am = len(msgs)
            if am == 1:
                await ctx.respond(f'Deleting {am} message.',ephemeral=True)
            else:
                await ctx.respond(f'Deleting {am} messages.',ephemeral=True)
            await ctx.channel.purge(limit=am)   
        except:logger.error(traceback.format_exc())
        
    async def cog_command_error(self, ctx, error):
        """
        The function `cog_command_error` handles errors that occur during command execution and sends an
        appropriate response based on the type of error.
        """
        try:
            if isinstance(error, MissingPermissions):
                await ctx.respond("You don't have permission to use this command.", ephemeral=True)
            if isinstance(error, NotOwner):
                await ctx.respond("You are not my Owner.", ephemeral=True)
        except:logger.error(traceback.format_exc())
            
def setup(bot):
    bot.add_cog(GeneralUtility(bot))