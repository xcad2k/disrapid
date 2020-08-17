import logging
from discord.ext import commands
# from datetime import datetime
# import random
import models
from sqlalchemy import exists, and_
from helpers import is_role, is_string, get_role_id_from_string
# import os


class Reactionrole(commands.Cog, name="Reactionrole"):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

    # EVENTS
    # ---
    #
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # check if this guild has an active reactionrole message
        try:
            s = self.db.Session()

            user = payload.member
            guild = payload.member.guild
            role_n = payload.emoji.name

            # check if bot is the message owner or the reaction initiator
            # this is needed because we don't want to react the bot to other
            # peoples messages, only if this is a reactionrole message

            # ignore message if we're the initiator
            if user.id == self.bot.user.id:
                return

            # ignore if message is not ours
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if message.author.id != self.bot.user.id:
                return

            # get role_id by name
            role_id = self._get_reactionrole_id(s, role_n, guild.id)

            if role_id is not None:
                # assign role to user
                await user.add_roles(user.guild.get_role(int(role_id)))

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole event: {e}"
            )
            s.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # check if this guild has an active reactionrole message
        try:
            s = self.db.Session()

            user_id = payload.user_id
            guild_id = payload.guild_id
            guild = self.bot.get_guild(guild_id)
            user = guild.get_member(user_id)
            role_n = payload.emoji.name

            # check if bot is the message owner or the reaction initiator
            # this is needed because we don't want to react the bot to other
            # peoples messages, only if this is a reactionrole message

            # ignore message if we're the initiator
            if user_id == self.bot.user.id:
                return

            # ignore if message is not ours
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if message.author.id != self.bot.user.id:
                return

            # get role_id by name
            role_id = self._get_reactionrole_id(s, role_n, guild.id)

            if role_id is not None:
                # assign role to user
                await user.remove_roles(user.guild.get_role(int(role_id)))

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole event: {e}"
            )
            s.close()

    # ADMIN CONFIG COMMANDS
    # ---
    #
    @commands.has_permissions(administrator=True)
    @commands.group()
    async def reactionrole(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        try:
            s = self.db.Session()

            msg = "This is a list of all configured" \
                "Reactionroles on this guild.\n" \
                "for more details check the help.\n\n" \
                "```css\n" \
                "/* Syntax= .name : (role) */\n\n"

            # get all reactionroles
            for result in s.query(
                    models.Reactionrole
                ) \
                .filter(
                    models.Reactionrole.guild_id == ctx.guild.id,
                    ).all():

                role_n = ctx.guild.get_role(result.role_id).name

                msg += f".{result.name} : " \
                    f"{role_n}\n"

            msg += "```"

            await ctx.send(msg)

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole command: {e}"
            )
            s.close()

    @reactionrole.command()
    async def message(self, ctx):
        # this will write a reactionrole message where people can react to
        # --
        try:
            s = self.db.Session()

            msg = "Pick a role:\n"
            message = await ctx.send(msg)

            # get all reactionroles
            for result in s.query(
                    models.Reactionrole
                ) \
                .filter(
                    models.Reactionrole.guild_id == ctx.guild.id,
                    ).all():

                # get the emoji object of the reaction
                for emoji in ctx.guild.emojis:
                    if result.name == emoji.name:
                        await message.add_reaction(emoji)
                        break
                else:
                    # no emoji found for this command...
                    logging.error(f"emoji not found for result-{result.name}")
                    continue

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole command: {e}"
            )
            s.close()

    @reactionrole.command()
    async def add(self, ctx, msg: str, role: str):

        try:
            if not is_string(msg):
                return

            s = self.db.Session()

            if is_role(role):
                # extract role id
                role_id = get_role_id_from_string(role)

                # skip if this role is not existing on the server
                if ctx.guild.get_role(int(role_id)) is None:
                    s.close()
                    return

            else:
                s.close()
                return

            # check if this is already existing in database
            if self._exists_reactionrole(s, msg, ctx.guild.id):
                await ctx.channel.send("Reactionrole is already existing.")
                s.close()
                return

            # reactionrole is not existing, add to list
            new_rr = models.Reactionrole(
                guild_id=ctx.guild.id,
                name=msg,
                role_id=role_id
            )
            s.add(new_rr)
            s.commit()

            await ctx.channel.send("Reactionrole was added to list")

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole command: {e}"
            )
            s.close()

    @reactionrole.command()
    async def rm(self, ctx, msg: str, role: str):

        try:
            if not is_string(msg):
                return

            s = self.db.Session()

            if is_role(role):
                # extract role id
                role_id = get_role_id_from_string(role)

                # skip if this role is not existing on the server
                if ctx.guild.get_role(int(role_id)) is None:
                    s.close()
                    return

            else:
                s.close()
                return

            # check if this is already existing in database
            if self._exists_reactionrole(s, msg, ctx.guild.id):
                # delete reactionrole
                obj = s.query(
                    models.Reactionrole
                ).filter(
                    models.Reactionrole.guild_id == ctx.guild.id,
                    models.Reactionrole.name == msg,
                    models.Reactionrole.role_id == role_id
                )
                obj.delete()

                s.commit()

                await ctx.channel.send("Reactionrole was deleted from list.")

            else:
                await ctx.channel.send("Reactionrole is not existing.")

            s.close()

        except Exception as e:
            logging.error(
                f"Error in reactionrole command: {e}"
            )
            s.close()

    def _exists_reactionrole(self, s, name, guild_id):
        # this return true when yt channel is followed for guild
        # ---
        #
        try:

            if s.query(
                exists().
                where(
                    and_(
                        models.Reactionrole.guild_id == guild_id,
                        models.Reactionrole.name == name
                    )
                )
            ).scalar():
                return True
        except Exception as e:
            logging.error(
                f"error in _exists_ytfollow: {e}"
            )
            return False

    def _get_reactionrole_id(self, s, name, guild_id):
        if self._exists_reactionrole(s, name, guild_id):
            role_id = s.query(
                    models.Reactionrole
            ).filter(
                models.Reactionrole.guild_id == guild_id,
                models.Reactionrole.name == name
            ).one()

            return role_id.role_id
        else:
            return None


def setup(bot):
    bot.add_cog(Reactionrole(bot))
