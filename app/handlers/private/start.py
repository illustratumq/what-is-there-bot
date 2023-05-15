import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, ChatTypeFilter, Command
from aiogram.types import Message, ChatType
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, RoomRepo
from app.filters import IsAdminFilter
from app.keyboards import Buttons
from app.keyboards.inline.deal import send_deal_kb, add_admin_chat_kb
from app.keyboards.reply.menu import menu_kb
from app.states.states import ParticipateSG

PARTICIPATE_REGEX = re.compile(r'participate-(\d+)')
ADMIN_HELP_REGEX = re.compile(r'helpdeal-(\d+)')


async def start_cmd(msg: Message, state: FSMContext):
    await state.finish()
    await msg.answer('Мої вітаннячка. Ви перейшли в головне меню.', reply_markup=menu_kb())


async def participate_cmd(msg: Message, deep_link: re.Match, deal_db: DealRepo, post_db: PostRepo,
                          state: FSMContext):
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
    text_to_channel = (
        f'{room.construct_admin_moderate_text()}\n\n'
        f'Розглядається адміном: {admin.mention}'
    )
    message = await msg.bot.edit_message_text(text_to_channel, config.misc.admin_channel_id, room.message_id)
    await room_db.update_room(deal.chat_id, admin_id=admin.user_id, message_id=message.message_id)
    await msg.answer(text_to_admin, reply_markup=add_admin_chat_kb(deal, admin))


def setup(dp: Dispatcher):
    dp.register_message_handler(
        participate_cmd, ChatTypeFilter(ChatType.PRIVATE), CommandStart(PARTICIPATE_REGEX), state='*')
    dp.register_message_handler(
        admin_help_cmd, IsAdminFilter(), ChatTypeFilter(ChatType.PRIVATE), CommandStart(ADMIN_HELP_REGEX), state='*')
    dp.register_message_handler(start_cmd, CommandStart(), ChatTypeFilter(ChatType.PRIVATE), state='*')
    dp.register_message_handler(start_cmd, Command('menu'), ChatTypeFilter(ChatType.PRIVATE), state='*')
    dp.register_message_handler(start_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.action.cancel, state='*')
    dp.register_message_handler(start_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.back, state='*')
