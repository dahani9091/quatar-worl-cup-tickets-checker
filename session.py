

import os


from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

api_id = "14371870"
api_hash = "bbba8c6a192b28e83049f33f6a72a1a2"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())