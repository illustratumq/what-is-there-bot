from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter, Command
from aiogram.types import ChatJoinRequest, CallbackQuery, ChatType, Message

from app.config import Config
from app.database.models import Deal
from app.database.services.repos import DealRepo, UserRepo, PostRepo
from app.handlers.userbot import UserbotController
from app.keyboards.inline.chat import room_menu_kb, room_cb


async def process_chat_join_request(cjr: ChatJoinRequest, deal_db: DealRepo, user_db: UserRepo,
                                    post_db: PostRepo, userbot: UserbotController):
    deal = await deal_db.get_deal_chat(cjr.chat.id)
    if not deal or cjr.from_user.id not in deal.participants:
        await cjr.bot.send_message(cjr.from_user.id, 'Ви не є учасником цього завдання')
        await cjr.decline()
        return
    await cjr.approve()
    members = await userbot.get_chat_members(cjr.chat.id)
    if deal.customer_id in members and deal.executor_id in members:
        await full_room_action(cjr, deal, user_db, post_db)
    else:
        await cjr.bot.send_message(
            cjr.chat.id, text='Зачекайте, доки приєднається інший користувач'
        )


async def full_room_action(cjr: ChatJoinRequest, deal: Deal, user_db: UserRepo, post_db: PostRepo):
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    post = await post_db.get_post(deal.post_id)
    text = (
        '<b>Ви стали учасниками угоди. Можете приступати до обговорення.</b>\n\n'
        f'Замовник: {customer.mention}\n'
        f'Виконавець: {executor.mention}\n'
        f'Ціна угоди: {deal.construct_price()}\n'
        f'ℹ Якщо Ви не знаєте правил нашого сервісу, то радимо ознайомитись '
        f'з ними тут (посилання).\n\n'
        f'Для повторного виклику меню, скористайтесь командою /menu'
    )
    await cjr.bot.send_message(cjr.chat.id, text)
    message = await cjr.bot.send_message(cjr.chat.id, post.construct_post_text(use_bot_link=False))
    await cjr.chat.pin_message(message_id=message.message_id)
    await message.answer('Меню чату. Для повторного виклику натисніть /menu',
                         reply_markup=room_menu_kb(deal, media=bool(post.media_url)))


async def chat_menu_cmd(msg: Message, deal_db: DealRepo, post_db: PostRepo,
                        user_db: UserRepo):
    deal = await deal_db.get_deal_chat(msg.chat.id)
    post = await post_db.get_post(deal.post_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text = (
        f'💬 Меню чату "{post.title}"\n\n'
        f'<b>Замовник</b>: {customer.mention}\n'
        f'<b>Виконавець</b>: {executor.mention}\n\n'
        f'<b>Встановленна ціна:</b> {deal.construct_price()}\n'
        f'<b>Статус угоди</b>: {deal.chat_status()}\n'
    )
    await msg.answer(text, reply_markup=room_menu_kb(deal, media=bool(post.media_url)))


async def send_media_chat(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                          config: Config):
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    await call.bot.send_chat_action(call.message.chat.id, action='upload_document')
    await call.bot.copy_message(
        chat_id=call.message.chat.id, from_chat_id=config.misc.media_channel_chat_id, message_id=post.media_id
    )


def setup(dp: Dispatcher):
    dp.register_chat_join_request_handler(process_chat_join_request, state='*')
    dp.register_message_handler(chat_menu_cmd, ChatTypeFilter(ChatType.GROUP), Command('menu'), state='*')
    dp.register_callback_query_handler(
        send_media_chat, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='send_media'), state='*')

