from telethon import events, Button
from app.streamer.manager import session_manager
from app.database.connection import files_col, users_col, settings
from app.models.schemas import FileMetadata, User
from app.utils.helpers import generate_short_code
from app.utils.fsub import is_user_fsubbed
from app.utils.rate_limit import check_rate_limit
import datetime
import logging

logger = logging.getLogger(__name__)

def get_ist_greeting():
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(ist_tz)
    hour = now.hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"

def register_handlers(bot):
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        user_id = event.sender_id
        # Save user to DB
        user_data = await users_col.find_one({"user_id": user_id})
        if user_data and user_data.get('is_banned'):
            return await event.reply("You are banned from using this bot.")
            
        if not user_data:
            sender = await event.get_sender()
            new_user = User(
                user_id=user_id,
                username=getattr(sender, 'username', None),
                first_name=getattr(sender, 'first_name', None),
                last_name=getattr(sender, 'last_name', None)
            )
            await users_col.insert_one(new_user.dict())
            
            # Log New User
            if settings.CHANNEL_ID:
                try:
                    first_name = getattr(sender, 'first_name', '') or ''
                    last_name = getattr(sender, 'last_name', '') or ''
                    name = f"{first_name} {last_name}".strip()
                    await bot.send_message(
                        settings.CHANNEL_ID,
                        f"#NewUser\n\n"
                        f"ID - `{user_id}`\n"
                        f"Name - {name}\n"
                        f"Username - @{getattr(sender, 'username', None) or 'N/A'}"
                    )
                except Exception as e:
                    logger.error(f"Error sending new user log: {e}")
        
        # Force Sub Check
        if not await is_user_fsubbed(bot, user_id):
            return await event.respond("Access Denied! Please join our channels to use this bot.")

        sender = await event.get_sender()
        first_name = getattr(sender, 'first_name', None) or "User"
        mention = f"[{first_name}](tg://user?id={user_id})"
        greeting = get_ist_greeting()

        await event.respond(f"Welcome {mention}\n\n{greeting}")

    @bot.on(events.NewMessage(func=lambda e: e.media))
    async def media_handler(event):
        # Ignore messages inside channels or log channel
        if event.is_channel and not event.is_group:
            return

        # Ban Check
        user_data = await users_col.find_one({"user_id": event.sender_id})
        if user_data and user_data.get('is_banned'):
            return await event.reply("You are banned from using this bot.")

        # Rate Limit Check
        if not await check_rate_limit(event.sender_id):
            return await event.reply("Please wait a moment before sending more files.")

        # Force Sub Check
        if not await is_user_fsubbed(bot, event.sender_id):
            return await event.reply("Access Denied! Please join our channels to use this bot.")

        media = event.media
        if not media:
            return

        detecting_msg = await event.reply("Detecting, please wait...")

        # Extract file info
        file_id = ""
        file_name = "file"
        file_size = 0
        mime_type = "application/octet-stream"

        if hasattr(media, 'document'):
            doc = media.document
            file_name = next((attr.file_name for attr in doc.attributes if hasattr(attr, 'file_name')), "file")
            file_size = doc.size
            mime_type = doc.mime_type
            file_id = f"{doc.id}_{doc.access_hash}"
        elif hasattr(media, 'photo'):
            photo = media.photo
            file_name = f"photo_{photo.id}.jpg"
            file_size = photo.sizes[-1].size if hasattr(photo.sizes[-1], 'size') else 0
            mime_type = "image/jpeg"
            file_id = f"{photo.id}_{photo.access_hash}"
        
        if not file_id:
            return await detecting_msg.edit("Could not process this file.")

        short_code = generate_short_code()
        
        file_meta = FileMetadata(
            file_id=file_id,
            file_unique_id=str(event.id),
            filename=file_name,
            mime_type=mime_type,
            file_size=file_size,
            uploader_id=event.sender_id,
            short_code=short_code,
            chat_id=event.chat_id,
            message_id=event.id,
            expiry_time=datetime.datetime.utcnow() + datetime.timedelta(hours=settings.DEFAULT_EXPIRY) if settings.DEFAULT_EXPIRY > 0 else None
        )
        
        await files_col.insert_one(file_meta.dict())
        
        base_url = settings.BASE_URL.rstrip('/')
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"http://{base_url}"

        download_url = f"{base_url}/dl/{short_code}"
        stream_url = f"{base_url}/watch/{short_code}"
        
        original_caption = (event.message.message or "").strip()
        if original_caption:
            caption = (
                f"{original_caption}\n\n"
                f"Download: {download_url}\n"
                f"Stream: {stream_url}"
            )
        else:
            caption = (
                f"File: `{file_name}`\n"
                f"Size: `{file_size / (1024*1024):.2f} MB`\n\n"
                f"Download: {download_url}\n"
                f"Stream: {stream_url}"
            )

        # Delete detection status message
        try:
            await detecting_msg.delete()
        except Exception as e:
            logger.error(f"Error deleting detecting message: {e}")

        user_buttons = [
            [Button.url("Download", download_url), Button.url("Watch Online", stream_url)],
            [Button.inline("Delete Link", f"del_{short_code}".encode())]
        ]

        # Re-send file with edited caption to user
        try:
            await bot.send_file(
                event.chat_id,
                file=event.media,
                caption=caption,
                buttons=user_buttons,
                reply_to=event.id
            )
        except Exception as e:
            logger.error(f"Error sending file with buttons: {e}")
            try:
                await bot.send_file(
                    event.chat_id,
                    file=event.media,
                    caption=caption,
                    reply_to=event.id
                )
            except Exception as e2:
                logger.error(f"Error sending file: {e2}")
                await event.reply(caption)

        # Re-send file with edited caption to channel
        if settings.CHANNEL_ID and settings.CHANNEL_ID != event.chat_id:
            channel_buttons = [
                [Button.url("Download", download_url), Button.url("Watch Online", stream_url)]
            ]
            try:
                await bot.send_file(
                    settings.CHANNEL_ID,
                    file=event.media,
                    caption=caption,
                    buttons=channel_buttons
                )
            except Exception as e:
                logger.error(f"Error sending file to channel: {e}")

    @bot.on(events.CallbackQuery())
    async def global_callback_check(event):
        if not await is_user_fsubbed(bot, event.sender_id):
            return await event.answer("Please join the channel first!", alert=True)

    @bot.on(events.CallbackQuery(pattern=b'del_'))
    async def delete_callback(event):
        short_code = event.data.decode().split("_")[1]
        file_data = await files_col.find_one({"short_code": short_code})
        if file_data and file_data['uploader_id'] == event.sender_id:
            await files_col.delete_one({"short_code": short_code})
            await event.edit("Link deleted successfully!")
        else:
            await event.answer("You are not authorized to delete this link.", alert=True)

    # Admin Commands
    @bot.on(events.NewMessage(pattern='/stats'))
    async def stats_handler(event):
        if event.sender_id not in settings.admin_list and event.sender_id != settings.OWNER_ID:
            return
        
        total_files = await files_col.count_documents({})
        total_users = await users_col.count_documents({})
        
        await event.reply(
            f"Statistics:\n\n"
            f"Total Users: `{total_users}`\n"
            f"Total Files: `{total_files}`"
        )

    @bot.on(events.NewMessage(pattern='/broadcast'))
    async def broadcast_handler(event):
        if event.sender_id not in settings.admin_list and event.sender_id != settings.OWNER_ID:
            return
        
        if not event.reply_to_msg_id:
            return await event.reply("Please reply to a message to broadcast it.")
            
        msg = await event.get_reply_message()
        users = await users_col.find().to_list(None)
        
        status = await event.reply(f"Broadcast Started...\nTarget: `{len(users)}` users")
        
        done = 0
        failed = 0
        for user in users:
            try:
                await bot.send_message(user['user_id'], msg)
                done += 1
            except Exception:
                failed += 1
            
            if done % 20 == 0:
                await status.edit(f"Broadcast in Progress...\nDone: `{done}`\nFailed: `{failed}`")
                
        await status.edit(f"Broadcast Completed!\n\nTotal: `{len(users)}` users\nSuccess: `{done}`\nFailed: `{failed}`")

    @bot.on(events.NewMessage(pattern='/ban'))
    async def ban_handler(event):
        if event.sender_id not in settings.admin_list and event.sender_id != settings.OWNER_ID:
            return
        
        try:
            user_id = int(event.text.split()[1])
            await users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
            await event.reply(f"User `{user_id}` has been banned.")
        except Exception:
            await event.reply("Usage: `/ban USER_ID`")

    @bot.on(events.NewMessage(pattern='/unban'))
    async def unban_handler(event):
        if event.sender_id not in settings.admin_list and event.sender_id != settings.OWNER_ID:
            return
        
        try:
            user_id = int(event.text.split()[1])
            await users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
            await event.reply(f"User `{user_id}` has been unbanned.")
        except Exception:
            await event.reply("Usage: `/unban USER_ID`")

    @bot.on(events.NewMessage(pattern='/autodel'))
    async def autodel_handler(event):
        if event.sender_id not in settings.admin_list and event.sender_id != settings.OWNER_ID:
            return
            
        try:
            args = event.text.split()
            if len(args) < 2:
                return await event.reply("Usage: `/autodel 24h` or `/autodel off`")
            
            val = args[1].lower()
            if val == "off":
                await event.reply("Auto-delete disabled.")
            else:
                hours = int(val.replace("h", ""))
                await event.reply(f"Auto-delete set to `{hours}` hours.")
        except Exception:
            await event.reply("Usage: `/autodel 24h` or `/autodel off`")
