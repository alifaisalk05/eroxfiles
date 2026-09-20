from telethon import TelegramClient
from telethon.sessions import StringSession
from app.database.connection import settings
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.clients = []
        self.bot_client = None
        self._index = 0

    async def start(self):
        from telethon.sessions import MemorySession
        # Start Bot Client
        self.bot_client = TelegramClient(MemorySession(), settings.API_ID, settings.API_HASH)
        await self.bot_client.start(bot_token=settings.BOT_TOKEN)
        logger.info("Bot client started")

        # Start User Clients (for high-speed streaming)
        session_strings = [s.strip() for s in settings.SESSIONS.split(",") if s.strip()]
        
        if not session_strings:
            logger.warning("No user sessions found! Using bot for streaming.")
            self.clients.append(self.bot_client)
        else:
            for i, session_str in enumerate(session_strings):
                try:
                    client = TelegramClient(
                        StringSession(session_str), 
                        settings.API_ID, 
                        settings.API_HASH,
                        connection_retries=5
                    )
                    await client.start()
                    self.clients.append(client)
                    logger.info(f"User Session {i+1} started")
                except Exception as e:
                    logger.error(f"Session {i+1} failed: {e}")
            
            if not self.clients:
                self.clients.append(self.bot_client)

    async def stop(self):
        for client in self.clients:
            await client.disconnect()

    def get_client(self):
        # Files are received by the bot account. User sessions may not have
        # access to private chats/messages where those files are stored.
        # Always use the bot client for reliable media retrieval.
        return self.bot_client

    def get_all_clients(self):
        """Return clients that can access bot-received media reliably."""
        return [self.bot_client] if self.bot_client else []

session_manager = SessionManager()
