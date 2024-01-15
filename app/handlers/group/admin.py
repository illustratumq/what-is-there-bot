from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Command
from aiogram.types import CallbackQuery, ChatType, Message
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.enums import UserStatusEnum
from app.database.services.repos import UserRepo, RoomRepo, DealRepo, PostRepo, CommissionRepo, SettingRepo, JoinRepo, \
    LetterRepo
from app.fondy.new_api import FondyApiWrapper
from app.handlers.admin.users import detail_user_info
from app.handlers.userbot import UserbotController
from app.keyboards.inline.admin import admin_command_kb, admin_confirm_kb, admin_room_cb, admin_choose_user_kb, \
    user_setting_kb, user_setting_cb, user_full_setting_cb
from app.handlers.group.cancel import cancel_deal_processing, done_deal_processing
from app.states.states import UserBanSG


async def admin_room_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo,
                         room_db: RoomRepo, post_db: PostRepo):
    await msg.delete()
    deal = await deal_db.get_deal_chat(msg.chat.id)
    room = await room_db.get_room(deal.chat_id)
    if not room.admin_id:
        await msg.bot.send_message(msg.from_user.id, 'У цьому чаті невизначено адміністратора')
        return
    elif msg.from_user.id != room.admin_id:
        admin = await user_db.get_user(room.admin_id)
        await msg.bot.send_message(msg.from_user.id, f'Цей чат вже модерує {admin.full_name}')
        return
    else:
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
                          room_db: RoomRepo, post_db: PostRepo, commission_db: CommissionRepo,
                          state: FSMContext, userbot: UserbotController, config: Config, join_db: JoinRepo,
                          letter_db: LetterRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    room = await room_db.get_room(deal.chat_id)
    admin = await user_db.get_user(call.from_user.id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    post = await post_db.get_post(deal.post_id)
    if deal.price == 0:
        await call.answer('Ціна угоди ще не визначена, тому її неможливо завершити', show_alert=True)
        return
    elif deal.payed == 0:
        await call.answer('Угода неоплачена, тому її неможливо завершити', show_alert=True)
        return
    elif deal.price > deal.payed:
        await call.answer(f'Угода оплачена частково {deal.payed} з {deal.price}, тому її неможливо завершити',
                          show_alert=True)
        return
    await room_db.update_room(room.chat_id, reason=f'{room.reason}. Угода номер №{deal.deal_id} '
                                                   f'була завершена адміністратором')
    text_to_channel = await room.construct_admin_moderate_text(room_db, call.bot, config, admin,
                                                               done_action='Завершено')
    await call.bot.edit_message_text(text_to_channel, config.misc.admin_help_channel_id, room.message_id)
    await call.message.answer(f'🆔 #Угода_номер_{deal.deal_id} ({room.name}) була успішно завершена!')
    await done_deal_processing(call, deal, post, customer, executor, state, deal_db, post_db, user_db,
                               room_db, commission_db, join_db, letter_db, userbot, config)

async def cancel_deal_admin(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                            room_db: RoomRepo, post_db: PostRepo, state: FSMContext,
                            userbot: UserbotController, config: Config, fondy: FondyApiWrapper,
                            session: sessionmaker):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    post = await post_db.get_post(deal.post_id)
    room = await room_db.get_room(deal.chat_id)
    admin = await user_db.get_user(call.from_user.id)
    await room_db.update_room(room.chat_id, reason=f'{room.reason}. Угода номер №{deal.deal_id} '
                                                   f'була відмінена адміністратором')
    text_to_channel = await room.construct_admin_moderate_text(room_db,  call.bot, config, admin,
                                                               done_action='Завершено')
    await call.bot.edit_message_text(text_to_channel, config.misc.admin_help_channel_id, room.message_id)
    await cancel_deal_processing(call.bot, deal, state, userbot, config, fondy, session,
                                 message=f'🔔 Ваша угода "{post.title}", була відмінена адміністратором')
    await call.message.edit_text(f'🆔 #Угода_номер_{deal.deal_id} ({room.name}) була успішно відмнінена!')


async def select_user_cmd(call: CallbackQuery, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                          room_db: RoomRepo, post_db: PostRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    text = (
        f'{await construct_deal_text(deal, post_db, user_db, room_db)}\n\n'
        f'<b>Оберіть користувача, для якого треба обмежити права</b>'
    )
    await call.message.edit_text(text, reply_markup=admin_choose_user_kb(deal))


async def edit_user_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                        setting_db: SettingRepo):
    deal = await deal_db.get_deal(int(callback_data['deal_id']))
    if 'user_id' in callback_data.keys():
        user = await user_db.get_user(int(callback_data['user_id']))
    elif callback_data['action'] == 'restrict_customer':
        user = await user_db.get_user(deal.customer_id)
    else:
        user = await user_db.get_user(deal.executor_id)
    setting = await setting_db.get_setting(user.user_id)
    role = 'Замовник' if user.user_id == deal.customer_id else 'Виконавець'
    text = (
        f'Ім\'я: {user.mention} ({user.user_id})\n'
        f'Роль в цій угоді: {role}\n'
        f'{await user.construct_admin_info(deal_db)}'
    )
    await call.message.edit_text(text, reply_markup=user_setting_kb(deal, setting, user))


async def edit_user_setting(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                            setting_db: SettingRepo, state: FSMContext, config: Config):
    user_id = int(callback_data['user_id'])
    setting = await setting_db.get_setting(user_id)
    if callback_data['action'] == 'ban_user':
        user = await user_db.get_user(user_id)
        if user.status == UserStatusEnum.BANNED:
            await user_db.update_user(user_id, status=UserStatusEnum.ACTIVE, ban_comment='')
            await call.answer(f'{user.full_name} розбанено.', show_alert=True)
        else:
            if user.user_id == call.from_user.id:
                await call.answer('Ви не можете забанити себе', show_alert=True)
                return
            await user_db.update_user(user_id, status=UserStatusEnum.BANNED, ban_comment='Причина не вказана')
            text = (
                'Будь-ласка, вкажіть причину, за якою '
                'користувач був забанений (до 400 символів)'
            )
            message = await call.message.answer(text)
            ufst = callback_data['@'] == 'ufst'
            kwargs = dict(
                user_id=user_id, last_msg_id=message.message_id, origin_id=call.message.message_id,
                ufst=ufst
            )
            if ufst:
                await state.update_data(**kwargs)
            else:
                kwargs.update(dict(deal_id=int(callback_data['deal_id'])))
                await state.update_data(**kwargs)
            await UserBanSG.Input.set()
    elif callback_data['action'] == 'can_be_customer':
        await setting_db.update_setting(user_id, can_be_customer=not setting.can_be_customer)
    elif callback_data['action'] == 'can_be_executor':
        await setting_db.update_setting(user_id, can_be_executor=not setting.can_be_executor)
    elif callback_data['action'] == 'can_publish_post':
        await setting_db.update_setting(user_id, can_publish_post=not setting.can_publish_post)
    elif callback_data['action'] == 'need_check_post':
        await setting_db.update_setting(user_id, need_check_post=not setting.need_check_post)
    if callback_data['@'] == 'ufst':
        await detail_user_info(call, callback_data, user_db, deal_db, setting_db, state)
    else:
        await edit_user_cmd(call, callback_data, deal_db, user_db, setting_db)


async def save_user_ban_comment(msg: Message, state: FSMContext, user_db: UserRepo, deal_db: DealRepo,
                                setting_db: SettingRepo, config: Config):
    await msg.delete()
    data = await state.get_data()

    ban_comment = msg.html_text
    user_id = data['user_id']
    origin_id = data['origin_id']
    last_msg_id = data['last_msg_id']

    if len(ban_comment) > 400:
        text = (
            f'Будь-ласка, вкажіть причину, за якою користувач був забанений (до 400 символів)\n\n'
            f'Ваш коментар занадто великий {len(ban_comment)}, спробуйте ще раз.'
        )
        message = await msg.bot.edit_message_text(text, msg.from_user.id, message_id=last_msg_id)
        await state.update_data(last_msg_id=message.message_id)
    else:
        await user_db.update_user(user_id, ban_comment=ban_comment)
        await msg.bot.delete_message(msg.from_user.id, last_msg_id)
        if data['ufst']:
            await detail_user_info(msg, {'user_id': user_id}, user_db, deal_db, setting_db, state)
            return
        user = await user_db.get_user(user_id)
        deal = await deal_db.get_deal(data['deal_id'])
        setting = await setting_db.get_setting(user_id)
        text = (
            f'Ім\'я: {user.mention} ({user.user_id})\n'
            f'{await user.construct_admin_info(deal_db)}'
        )
        await msg.bot.edit_message_text(text, msg.from_user.id, origin_id, reply_markup=user_setting_kb(deal, setting,
                                                                                                        user))
        await state.finish()


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

    dp.register_callback_query_handler(
        select_user_cmd, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='restrict_user'), state='*')
    dp.register_callback_query_handler(
        edit_user_cmd, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='restrict_customer'), state='*')
    dp.register_callback_query_handler(
        edit_user_cmd, ChatTypeFilter(ChatType.PRIVATE), admin_room_cb.filter(action='restrict_executor'), state='*')

    dp.register_callback_query_handler(
        edit_user_setting, ChatTypeFilter(ChatType.PRIVATE), user_full_setting_cb.filter(), state='*')
    dp.register_callback_query_handler(
        edit_user_setting, ChatTypeFilter(ChatType.PRIVATE), user_setting_cb.filter(), state='*')

    dp.register_message_handler(save_user_ban_comment, ChatTypeFilter(ChatType.PRIVATE), state=UserBanSG.Input)


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
        f'Ціна угоди: {deal.deal_price}\n'
        f'Статус оплати: {deal.chat_status}'
    )
