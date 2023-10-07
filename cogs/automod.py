import os
import discord
import asyncio
import re
from pathlib import Path
from discord.ext import commands
from discord.ext.commands import MissingPermissions
from discord.commands import slash_command, Option

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    automodcat = discord.SlashCommandGroup('automod', 'Moderates the Users.')

    def load_filter(self, gid):     
        with open(f'data/guilds/{gid}/filters.txt', 'r', encoding='utf-8') as f:
            rawfilt = f.readlines()
        procfilt = []
        for l in rawfilt:
            if not l.startswith('#'):
                if '-' in l:
                    procfilt.append(l.strip())                
        swrwrd = []
        replword = []
        for l in procfilt:
                tmpl = l.split('-',1)
                replword.append(tmpl[1])
                swrwrd.append(tmpl[0])
        filters = dict(zip(swrwrd, replword))    
        return filters, swrwrd
    
    def has_custom_emoji_format(self, text: str) -> bool:
        pattern = r'\<\:\+:\>'
        return bool(re.search(pattern, text))

    def find_custom_emoji(self, text: str):
        pattern = r'\<\:\+:\>'
        if match := re.search(pattern, text):
            return match.start(), match.end()
        else:
            return None, None

    def escape_formatting_chars(self, word):
        formatting_chars = ['*', '_', '`', '~', '#', '@', '\'', '\"', '\\']
        return ''.join(
            '\\' + char if char in formatting_chars else char for char in word
        )

    @automodcat.command(description='Lists all filtered words and their replacements.')
    async def list_filterwords(self, ctx):
        msg = 'List of filtered words:\n'
        gid = ctx.guild.id
        filters, swrwrd = self.load_filter(gid)
        filtwrd = [filters[ent] for ent in swrwrd]
        for i, wrd in enumerate(swrwrd):
            msg += (f'{wrd} - {filtwrd[i]}\n')
        await ctx.respond(msg,ephemeral=True)

    @automodcat.command(description='Adds a word to the list of filtered words.')
    @commands.has_guild_permissions(administrator=True)
    async def add_filterword(self, ctx, 
                            word: Option(str, description='The word which will be censored.'),
                            filtered: Option(str, description='The word which will replace the censored word.')
                            ):
        if not self.has_custom_emoji_format(word):
            word = self.escape_formatting_chars(word.lower())
        else:
            word = word.lower()
        if not self.has_custom_emoji_format(filtered):
            filtered = self.escape_formatting_chars(filtered.lower())
        else:
            filtered = filtered.lower()
        gid = ctx.guild.id
        filters, swrwrd = self.load_filter(gid)
        if word not in swrwrd:
            with open(f'data/guilds/{gid}/filters.txt', 'a', encoding='utf-8') as f:
                f.write(f'\n{word}-{filtered}')
        filters, swrwrd = self.load_filter(gid)
        await ctx.respond(f'Added word \'{word}\' to the filterlist, will be replaced with \'{filtered}\'.',ephemeral=True)

    @automodcat.command(description='Removes a word from the list of filtered words.')
    @commands.has_guild_permissions(administrator=True)
    async def remove_filterword(self, ctx, 
                                word: Option(str, description='Pick a word from /list_filterwords to remove from the filter.')
                                ):
        gid = ctx.guild.id
        filters, swrwrd = self.load_filter(gid)
        if word in swrwrd:
            with open(f'data/guilds/{gid}/filters.txt', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                f.truncate()
                for l in lines:
                    if not l.startswith(word) and not l.isspace():
                        f.write(l)
        filters, swrwrd = self.load_filter(gid)
        await ctx.respond(f'Removed word \'{word}\' from the filterlist.',ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        msg = self.bot.get_message(message.id)
        chan = msg.channel
        if msg.author == self.bot.user:
            return
        try:
            gid = msg.guild.id
        except:
            return
        filters, swrwrd = self.load_filter(gid)
        text = message.content.lower()
        send = False
        for wrd in swrwrd:           
            if wrd in text:
                if self.has_custom_emoji_format(filters[wrd]):
                    print('is emoji')
                start, end = self.find_custom_emoji(filters[wrd])
                if start is not None:
                    emoji_code = text[start:end]
                    emoji = self.bot.get_emoji(emoji_code)
                    text = text[:start] + emoji + text[end:]
                else:
                    replwrd = filters[wrd].encode('utf-8')
                    replwrd = replwrd.decode('utf-8')
                    print(replwrd)
                    text = text.replace(wrd,replwrd)
                send = True
        if not send:
            return
        await msg.delete()
        embed = discord.Embed(colour=0xe74c3c)
        embed.set_author(name=msg.author.display_name,icon_url=msg.author.avatar)
        embed.add_field(name='Censored message:',value=text)
        msg = await chan.send(embed=embed)
        
    async def cog_command_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)

def setup(bot):
    bot.add_cog(AutoMod(bot))
    