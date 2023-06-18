from datetime import datetime, timedelta

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Command
from aiogram.types import ChatJoinRequest, CallbackQuery, ChatType, Message
from pyrogram.errors import UserAlreadyParticipant

from app.config import Config
from app.database.models import Deal
from app.database.services.enums import DealTypeEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo
from app.handlers.userbot import UserbotController
from app.keyboards.inline.chat import room_menu_kb, room_cb
from app.keyboards.inline.deal import help_admin_kb, add_chat_cb, add_admin_chat_kb
from app.misc.commands import set_new_room_commands


async def process_chat_join_request(cjr: ChatJoinRequest, deal_db: DealRepo, user_db: UserRepo,
                                    post_db: PostRepo, userbot: UserbotController, config: Config):
    deal = await deal_db.get_deal_chat(cjr.chat.id)
    if not deal or cjr.from_user.id not in deal.participants:
        await cjr.bot.send_message(cjr.from_user.id, 'Ви не є учасником цього завдання')
        await cjr.decline()
        return
    await cjr.approve()
    members = await userbot.get_chat_members(cjr.chat.id)
    if deal.customer_id in members and deal.executor_id in members:
        await deal_db.update_deal(deal.deal_id, next_activity_date=datetime.now() + timedelta(minutes=1))
        await full_room_action(cjr, deal, user_db, post_db, config)
    else:
        await cjr.bot.send_message(
            cjr.chat.id, text='Зачекайте, доки приєднається інший користувач'
        )


async def add_admin_to_chat_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, room_db: RoomRepo,
                                user_db: UserRepo, userbot: UserbotController):
    deal_id = int(callback_data['deal_id'])
    admin_id = int(callback_data['admin_id'])
    deal = await deal_db.get_deal(deal_id)
    admin = await user_db.get_user(admin_id)
    reply_markup = add_admin_chat_kb(deal, admin)
    try:
        await userbot.add_chat_member(deal.chat_id, admin_id)
    except UserAlreadyParticipant:
        room = await room_db.get_room(deal.chat_id)
        await call.message.answer(f'Ви вже є учасником цієї групи: {room.invite_link}', disable_web_page_preview=True,
                                  reply_markup=reply_markup)
    except Exception as Error:
        await call.message.answer(f'Схоже юззербот не може додати вас у чат, причина:\n\n{Error}',
                                  reply_markup=reply_markup)
    await set_new_room_commands(call.bot, deal.chat_id, admin_id)
    await deal_db.update_deal(deal.deal_id, next_activity_date=None)
    await call.message.delete()


async def full_room_action(cjr: ChatJoinRequest, deal: Deal, user_db: UserRepo, post_db: PostRepo, config: Config):
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    post = await post_db.get_post(deal.post_id)
    text = (
        '<b>Ви стали учасниками угоди. Можете приступати до обговорення.</b>\n\n'
        f'Замовник: {customer.mention}\n'
        f'Виконавець: {executor.mention}\n'
        f'Ціна угоди: {deal.construct_price()}\n'
        f'🆔 #Угода_номер_{deal.deal_id}\n'
        f'ℹ Якщо Ви не знаєте правил нашого сервісу, то радимо ознайомитись '
        f'з ними тут (посилання).\n\n'  # TODO: додати посилання на правила сервісу
        f'Для повторного виклику меню, скористайтесь командою /menu'
    )
    message = await cjr.bot.send_message(cjr.chat.id, text)
    if deal.type == DealTypeEnum.PUBLIC:
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


async def cancel_action_cmd(call: CallbackQuery, deal_db: DealRepo, post_db: PostRepo, user_db: UserRepo,
                            state: FSMContext):
    # await call.message.delete()
    deal = await deal_db.get_deal_chat(call.message.chat.id)
    post = await post_db.get_post(deal.post_id)
    await state.storage.reset_data(chat=call.message.chat.id, user=deal.customer_id)
    await state.storage.reset_data(chat=call.message.chat.id, user=deal.executor_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text = (
        f'💬 Меню чату "{post.title}"\n\n'
        f'<b>Замовник</b>: {customer.mention}\n'
        f'<b>Виконавець</b>: {executor.mention}\n\n'
        f'<b>Встановленна ціна:</b> {deal.construct_price()}\n'
        f'<b>Статус угоди</b>: {deal.chat_status()}\n'
    )
    await call.message.edit_text(text, reply_markup=room_menu_kb(deal, media=bool(post.media_url)))


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


async def confirm_room_activity(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo):
    await call.message.delete()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    await deal_db.update_deal(deal.deal_id, activity_confirm=True,
                              next_activity_date=datetime.now() + timedelta(minutes=1))
    user = await user_db.get_user(call.from_user.id)
    text = (
        f'✅ {user.create_html_link("Замовник" if user.user_id == deal.customer_id else "Виконавець")} підтвердив '
        f'актуальність угоди. Можете провдожувати роботу!\n\n'
        f'Зверніть увагу, повідомлення про активність в чаті автоматично надисилається кожні 12 годин, якщо '
        f'ваша угода неоплачена.\n\n'
        f'Якщо протягом настпуних 12 годин, після цього, активність не буде підтверджена, угода буде '
        f'автоматично відмінена.'
    )
    await call.bot.send_message(deal.chat_id, text)


async def call_admin_to_room_cmd(call: CallbackQuery, deal_db: DealRepo, room_db: RoomRepo, config: Config):
    deal = await deal_db.get_deal_chat(call.message.chat.id)
    room = await room_db.get_room(call.message.chat.id)
    if room.admin_required:
        text = (
            'Повідомлення про допомогу вже було відправлено адміністраторам сервісу. Зачекайте '
            'поки адміністратор приєднається в чат.'
        )
        await call.message.answer(text)
        return
    await room_db.update_room(room.chat_id, reason='Виклик користувачем із чату', admin_required=True)
    text = await room.construct_admin_moderate_text(room_db, call.bot, config)
    msg = await call.bot.send_message(config.misc.admin_channel_id, text,
                                      reply_markup=await help_admin_kb(deal.deal_id))
    await room_db.update_room(room.chat_id, message_id=msg.message_id)
    await call.message.answer('Адміністратора було викликано у чат! Зачекайте, він невдовзі приєднається')


def setup(dp: Dispatcher):
    dp.register_chat_join_request_handler(process_chat_join_request, state='*')
    dp.register_message_handler(chat_menu_cmd, ChatTypeFilter(ChatType.GROUP), Command('menu'), state='*')
    dp.register_callback_query_handler(
        send_media_chat, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='send_media'), state='*')
    dp.register_callback_query_handler(
        confirm_room_activity, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='confirm_activity'), state='*')
    dp.register_callback_query_handler(
        call_admin_to_room_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='help'), state='*')
    dp.register_callback_query_handler(
        add_admin_to_chat_cmd, ChatTypeFilter(ChatType.PRIVATE), add_chat_cb.filter(action='enter'), state='*')
    dp.register_callback_query_handler(
        cancel_action_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='back'), state='*')
