from pyrogram import Client

from environs import Env

env = Env()
env.read_env()

api_id = env.str('USERBOT_API_ID')
api_hash = env.str('USERBOT_API_HASH')

app = Client('userbot', api_id, api_hash)
app.start()
app.stop()