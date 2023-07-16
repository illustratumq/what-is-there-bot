import re
from datetime import timedelta, datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, ChatTypeFilter, Command
from aiogram.types import Message, ChatType, ChatActions
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import DealStatusEnum, UserTypeEnum, RoomStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, RoomRepo
from app.filters import IsAdminFilter
from app.handlers.userbot import UserbotController
from app.keyboards import Buttons
from app.keyboards.inline.admin import manage_post_kb
from app.keyboards.inline.deal import send_deal_kb, add_admin_chat_kb, join_room_kb
from app.keyboards.reply.menu import menu_kb
from app.misc.commands import set_new_room_commands
from app.states.states import ParticipateSG

PARTICIPATE_REGEX = re.compile(r'participate-(\d+)')
ADMIN_HELP_REGEX = re.compile(r'helpdeal-(\d+)')
MANAGE_POST_REGEX = re.compile(r'manage_post-(\d+)')
PRIVATE_DEAL_REGEX = re.compile(r'private_deal-(\d+)')

greeting_text = (
        'Цей бот дозволяє вам публікувати та керувати постами на каналі А ШО ТАМ?\n\n'
        'В нижній частині чату у Вас є кнопки для взаємодії з ботом 👇\n\n'
        '<b>Новий пост ➕</b> - Опублікувати новий пост на каналі.\n'
        '<b>Мої пости 📑</b> -  Переглянути та керувати своїми постами на каналі.\n'
        '<b>Мої кошти 💸</b> - Перевірити баланс та вивести кошти з рахунку.\n'
        '<b>Мій рейтинг ⭐</b> - Переглянути рейтинг у сервісі та додати опис про себе.\n'
        '<b>Мої чати 💬</b> -  Переглянути активні чати.\n'
        '<b>Сповіщення 🔔</b> -  Налаштувати сповіщення про нові пости на каналі.\n\n'
        'Якщо у вас є питання щодо реклами, співпраці або будь-яких інших питань, '
        'а також ідеї покращення сервісу, ви можете зв\'язатися з адміністрацією '
        'написавши сюди @AShoTam_Bot'
    )


async def start_cmd(msg: Message, state: FSMContext, user_db: UserRepo):
    if not msg.from_user.is_bot:
        user = await user_db.get_user(msg.from_user.id)
        await msg.answer(greeting_text if msg.text != Buttons.menu.back else 'Ви повернулись в головне меню',
                         reply_markup=menu_kb(admin=user.type == UserTypeEnum.ADMIN))
    else:
        await msg.answer(greeting_text, reply_markup=menu_kb())
        await state.finish()

async def cancel_action_cmd(msg: Message, user_db: UserRepo, state: FSMContext):
    await state.finish()
    user = await user_db.get_user(msg.from_user.id)
    await msg.answer('Ви відмінили дію', reply_markup=menu_kb(admin=user.type == UserTypeEnum.ADMIN))

async def participate_cmd(msg: Message, deep_link: re.Match, deal_db: DealRepo, post_db: PostRepo,
                          state: FSMContext):
    await msg.delete()
    deal_id = int(deep_link.groups()[-1])
    deal = await deal_db.get_deal(deal_id)
    if not deal:
        await msg.answer('Схоже ця угода вже не актуальна')
        return
    post = await post_db.get_post(deal.post_id)
    if deal.status != DealStatusEnum.ACTIVE:
        await msg.answer('Ви не можете долучитися до цього завдання')
        return
    elif deal.customer_id == msg.from_user.id:
        await msg.answer('Ви не можете долучитися до свого завдання')
        return
    elif msg.from_user.id in deal.willing_ids:
        await msg.answer('Ви вже відправили запит на це завдання')
        return
    text = (
        f'Ви хочете стати виконавцем завдання.\n\n'
        f'Для цього, надішліть коментар, який побачить замовник у Вашому запиті, і натисніть кнопку '
        f'"{Buttons.post.send_deal}". Або просто натисніть цю кнопку, якщо коментар не потрібен.\n\n'
        f'Рекомендація: Розкажіть чому замовник має обрати саме вас.'
        f'{hide_link(post.post_url)}'
    )
    await msg.answer(text, reply_markup=send_deal_kb(deal, msg.from_user.id))
    await ParticipateSG.Comment.set()
    await state.update_data(deal_id=deal_id, comment=False)


async def admin_help_cmd(msg: Message, deep_link: re.Match, deal_db: DealRepo, post_db: PostRepo,
                         user_db: UserRepo, room_db: RoomRepo, config: Config):
    await msg.delete()
    deal_id = int(deep_link.groups()[-1])
    deal = await deal_db.get_deal(deal_id)
    if not deal.chat_id:
        await msg.answer('Схоже ця угода вже не актуальна')
        return
    post = await post_db.get_post(deal.post_id)
    room = await room_db.get_room(deal.chat_id)
    admin = await user_db.get_user(msg.from_user.id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text_to_admin = (
        f'Ви хочете увійти як модератор у {room.name}\n\n'
        f'Пост: {post.construct_html_link(post.title)}\n'
        f'Замовник: {customer.mention}\n'
        f'Виконавець: {executor.mention}\n'
        f'Ціна угоди: {deal.construct_price()}\n'
        f'Статус оплати: {deal.chat_status()}\n\n'
    )
    text_to_channel = await room.construct_admin_moderate_text(room_db, msg.bot, config, admin)
    message = await msg.bot.edit_message_text(text_to_channel, config.misc.admin_channel_id, room.message_id)
    await room_db.update_room(deal.chat_id, admin_id=admin.user_id, message_id=message.message_id)
    await msg.answer(text_to_admin, reply_markup=add_admin_chat_kb(deal, admin))


async def manage_post_cmd(msg: Message, deep_link: re.Match, post_db: PostRepo,
                          user_db: UserRepo, room_db: RoomRepo, deal_db: DealRepo):
    await msg.delete()
    post_id = int(deep_link.groups()[-1])
    post = await post_db.get_post(post_id)
    text = (
        f'{post.construct_post_text(use_bot_link=False)}\n\n'
    )
    if post.status == DealStatusEnum.DONE:
        deal = await deal_db.get_deal_post(post_id)
        room = await room_db.get_room(deal.chat_id)
        text += f'🆔 #Угода_номер_{deal.deal_id} завершилась в {room.construct_html_text(room.name)}'
    elif post.status == DealStatusEnum.BUSY:
        deal = await deal_db.get_deal_post(post_id)
        customer = await user_db.get_user(deal.customer_id)
        executor = await user_db.get_user(deal.executor_id)
        text += f'<b>Угода укладена між:</b> {customer.mention} (Замовник) та {executor.mention} (Виконавець)'
    await msg.answer(text, reply_markup=manage_post_kb(post))


async def confirm_private_deal_cmd(msg: Message, deep_link: re.Match, deal_db: DealRepo, room_db: RoomRepo,
                                   userbot: UserbotController):
    await msg.delete()
    deal_id = int(deep_link.groups()[-1])
    deal = await deal_db.get_deal(deal_id)
    if deal.status == DealStatusEnum.BUSY or all([deal.customer_id, deal.executor_id]):
        await msg.answer('Упс, ця угода вже зайнята. Ти не можеш стати її учасником')
        return
    elif deal.customer_id == msg.from_user.id or deal.executor_id == msg.from_user.id:
        await msg.answer('Ти не можеш стати другим учасником в своїй угоді')
        return
    await msg.answer('🎉 Вітаємо. Ви стали 2-им учасником приватної угоди')
    role = 'customer_id' if deal.executor_id else 'executor_id'
    room_chat_id, invite_link = await get_room(msg, room_db, userbot)
    await deal_db.update_deal(
        deal_id, chat_id=room_chat_id, **{role: msg.from_user.id},
        next_activity_date=datetime.now() + timedelta(minutes=1)
    )
    text = (
        f'Приватна угода з {msg.from_user.full_name} ухвалена. Заходьте до кімнати за цим посиланням:\n\n'
        f'{invite_link}\n\nАбо натисніть на кнопку під цим повідомленням'
    )
    deal = await deal_db.get_deal(deal_id)
    await msg.bot.send_message(
        deal.customer_id, text=text, reply_markup=join_room_kb(invite_link), disable_web_page_preview=True)
    await msg.bot.send_message(
        deal.executor_id, text=text, reply_markup=join_room_kb(invite_link), disable_web_page_preview=True)


def setup(dp: Dispatcher):
    dp.register_message_handler(
        participate_cmd, ChatTypeFilter(ChatType.PRIVATE), CommandStart(PARTICIPATE_REGEX), state='*')
    dp.register_message_handler(
        admin_help_cmd, IsAdminFilter(), ChatTypeFilter(ChatType.PRIVATE), CommandStart(ADMIN_HELP_REGEX), state='*')
    dp.register_message_handler(
        manage_post_cmd, IsAdminFilter(), ChatTypeFilter(ChatType.PRIVATE), CommandStart(MANAGE_POST_REGEX), state='*')
    dp.register_message_handler(
        confirm_private_deal_cmd, ChatTypeFilter(ChatType.PRIVATE), CommandStart(PRIVATE_DEAL_REGEX), state='*')
    dp.register_message_handler(cancel_action_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.action.cancel,
                                state='*')
    dp.register_message_handler(start_cmd, CommandStart(), ChatTypeFilter(ChatType.PRIVATE), state='*')
    dp.register_message_handler(start_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.admin.menu, state='*')
    dp.register_message_handler(start_cmd, Command('menu'), ChatTypeFilter(ChatType.PRIVATE), state='*')
    dp.register_message_handler(start_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.back, state='*')


async def get_room(msg: Message, room_db: RoomRepo, userbot: UserbotController) -> tuple[int, str]:
    room = await room_db.get_free_room()
    await msg.answer('Очікуйте, ми створюємо для вас кімнату...')
    if room is None:
        await msg.bot.send_chat_action(msg.from_user.id, ChatActions.FIND_LOCATION)
        quantity_of_rooms = await room_db.count()
        chat, invite_link, name = await userbot.create_new_room(quantity_of_rooms)
        await room_db.add(chat_id=chat.id, invite_link=invite_link.invite_link, status=RoomStatusEnum.BUSY, name=name)
        await set_new_room_commands(msg.bot, chat.id, await userbot.get_client_user_id())
        chat_id = chat.id
        invite_link = invite_link.invite_link
    else:
        await msg.bot.send_chat_action(msg.from_user.id, ChatActions.FIND_LOCATION)
        await room_db.update_room(room.chat_id, status=RoomStatusEnum.BUSY)
        chat_id = room.chat_id
        invite_link = room.invite_link
    return chat_id, invite_link
