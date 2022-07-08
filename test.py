

import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
load_dotenv()

api_id = os.getenv("api_id")
api_hash = os.getenv("api_hash")

try:
    client = TelegramClient(StringSession(os.getenv("session_token")), api_id, api_hash)
    client.start()
except Exception as e:
    print(f"Exception while starting the client - {e}")
else:
    print("Client started")

async def send(msg):
    try:
        # Replace the xxxxx in the following line with the full international mobile number of the contact
        # In place of mobile number you can use the telegram user id of the contact if you know
        ret_value = await client.send_message("+212658569397", )
    except Exception as e:
        print(f"Exception while sending the message - {e}")
    else:
        print(f"Message sent. Return Value {ret_value}")

with client:
    client.loop.run_until_complete(send('testing telegram bots'))