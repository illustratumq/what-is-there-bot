from pyrogram import Client
from environs import Env

env = Env()
env.read_env()

api_id = env.str('USERBOT_API_ID')
api_hash = env.str('USERBOT_API_HASH')
phone_number = env.str('USERBOT_PHONE_NUMBER')
name = env.str('USERBOT_SESSION_NAME')

app = Client(name, api_id, api_hash, phone_number=phone_number)
app.start()
app.stop()