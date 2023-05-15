from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Command
from aiogram.types import CallbackQuery, ChatType, Message

from app.config import Config
from app.database.services.repos import UserRepo, RoomRepo, DealRepo, PostRepo
from app.handlers.userbot import UserbotController
from app.keyboards.inline.admin import admin_command_kb, admin_confirm_kb, admin_room_cb
from app.handlers.group.cancel import cancel_deal_processing, done_deal_processing


async def admin_room_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo,
                         room_db: RoomRepo, post_db: PostRepo):
    await msg.delete()
    deal = await deal_db.get_deal_chat(msg.chat.id)
    room = await room_db.get_room(deal.chat_id)
    if msg.from_user.id != room.admin_id:
        admin = await user_db.get_user(room.admin_id)
        await msg.bot.send_message(msg.from_user.id, f'Цей чат вже модерує {admin.full_name}')
        return
    await msg.bot.send_message(
        msg.from_user.id, await construct_deal_text(deal, post_db, user_db, room_db),
        reply_markup=admin_command_kb(deal))


async def back_to_room_cmd(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                           room_db: RoomRepo, post_db: PostRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    room = await room_db.get_room(deal.chat_id)
    if call.from_user.id != room.admin_id:
        admin = await user_db.get_user(room.admin_id)
        await call.answer(f'Цей чат вже модерує {admin.full_name}', show_alert=True)
        return
    await call.message.edit_text(await construct_deal_text(deal, post_db, user_db, room_db),
                                 reply_markup=admin_command_kb(deal))


async def cancel_deal_confirm(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                              room_db: RoomRepo, post_db: PostRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    text = (
        f'{await construct_deal_text(deal, post_db, user_db, room_db)}\n\n'
        f'ℹ <b>При відміні угоди</b>, всі кошти, які були оплачені + комісія сервісу - повертаюсться на '
        f'рахунок Замовника, пост знову публікується в каналі, бот видаляє користувачів із чату.\n\n'
        f'Щоб відмінити угоду, підтвердіть своє рішення 👇'
    )
    await call.message.edit_text(text, reply_markup=admin_confirm_kb(deal, 'cancel_deal'))


async def done_deal_confirm(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                            room_db: RoomRepo, post_db: PostRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    text = (
        f'{await construct_deal_text(deal, post_db, user_db, room_db)}\n\n'
        f'ℹ <b>При завершені угоди</b>, всі кошти, які були оплачені - нараховуються на '
        f'рахунок Виконавця, угода вважається виконаною.\n\n'
        f'Щоб завершити угоду, підтвердіть своє рішення 👇'
    )
    await call.message.edit_text(text, reply_markup=admin_confirm_kb(deal, 'done_deal'))


async def done_deal_admin(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                          room_db: RoomRepo, post_db: PostRepo, state: FSMContext, userbot: UserbotController,
                          config: Config):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    post = await post_db.get_post(deal.post_id)
    room = await room_db.get_room(deal.chat_id)
    admin = await user_db.get_user(call.from_user.id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text_to_channel = (
        f'{room.construct_admin_moderate_text()}\n\n🆔 #Угода_номер_{deal.deal_id} була завершена '
        f'адміністратором {admin.full_name}'
    )
    await call.bot.edit_message_text(text_to_channel, config.misc.admin_channel_id, room.message_id)
    await done_deal_processing(call, deal, post, customer, executor, state,
                               deal_db, post_db, user_db, room_db, userbot, config)
    await call.message.edit_text(f'🆔 #Угода_номер_{deal.deal_id} ({room.name}) була успішно завершена!')


async def cancel_deal_admin(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                            room_db: RoomRepo, post_db: PostRepo, state: FSMContext, userbot: UserbotController,
                            config: Config):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    post = await post_db.get_post(deal.post_id)
    room = await room_db.get_room(deal.chat_id)
    admin = await user_db.get_user(call.from_user.id)
    customer = await user_db.get_user(deal.customer_id)
    text_to_channel = (
        f'{room.construct_admin_moderate_text()}\n\n🆔 #Угода_номер_{deal.deal_id} була відмінена '
        f'адміністратором {admin.full_name}'
    )
    await call.bot.edit_message_text(text_to_channel, config.misc.admin_channel_id, room.message_id)
    await cancel_deal_processing(call.bot, deal, post, customer, state, deal_db,
                                 post_db, user_db, room_db, userbot, config,
                                 message=f'Угода {post.title}, була відмінена адміністратором')
    await call.message.edit_text(f'🆔 #Угода_номер_{deal.deal_id} ({room.name}) була успішно відмнінена!')


def setup(dp: Dispatcher):
    dp.register_message_handler(
        admin_room_cmd, ChatTypeFilter(ChatType.GROUP), Command('admin'), state='*')
    dp.register_callback_query_handler(
        back_to_room_cmd, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='back'), state='*')

    dp.register_callback_query_handler(
        cancel_deal_confirm, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='cancel_deal'), state='*')
    dp.register_callback_query_handler(
        cancel_deal_admin, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='conf_cancel_deal'), state='*')

    dp.register_callback_query_handler(
        done_deal_confirm, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='done_deal'), state='*')
    dp.register_callback_query_handler(
        done_deal_admin, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='conf_done_deal'), state='*')


async def construct_deal_text(deal: DealRepo.model, post_db: PostRepo, user_db: UserRepo, room_db: RoomRepo):
    post = await post_db.get_post(deal.post_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    room = await room_db.get_room(deal.chat_id)
    return (
        f'⚒ [Адмін панель | {room.construct_html_text(room.name)}]\n\n'
        f'Пост: {post.construct_html_link(post.title)}\n'
        f'Замовник: {customer.mention}\n'
        f'Виконавець: {executor.mention}\n'
        f'Ціна угоди: {deal.construct_price()}\n'
        f'Статус оплати: {deal.chat_status()}'
    )