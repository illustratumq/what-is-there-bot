from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType
from aiogram.utils.deep_linking import get_start_link

from app.database.services.enums import DealStatusEnum, DealTypeEnum
from app.database.services.repos import DealRepo, PostRepo
from app.keyboards import Buttons
from app.keyboards.inline.deal import to_bot_kb
from app.keyboards.reply.menu import basic_kb
from app.states.states import PrivateDealSG


async def create_new_deal_cmd(msg: Message, deal_db: DealRepo, state: FSMContext):
    deals = await deal_db.get_deal_type(DealTypeEnum.PRIVATE, DealStatusEnum.ACTIVE, msg.from_user.id)
    if deals:
        deal = deals[0]
        await state.update_data(role='executor' if deal.executor_id == msg.from_user.id else 'customer')
        await msg.answer('Перешли наступне повідомлення іншому учаснику, для того щоб розпочати',
                         reply_markup=basic_kb([Buttons.menu.back]))
        await new_deal_invite_msg(msg, deal, state)
        await state.finish()
    else:
        await msg.answer(
            'Для того щоб створити приватну угоду, обери свою роль у ній',
            reply_markup=basic_kb([[Buttons.deal.customer], [Buttons.deal.executor], [Buttons.menu.back]]))
        await PrivateDealSG.SelectRole.set()


async def new_deal_invite_msg(msg: Message, deal: DealRepo.model, state: FSMContext):
    data = await state.get_data()
    role = data['role']
    roles = {
        'customer': 'виконавцем',
        'executor': 'замовником'
    }
    link = await get_start_link(f'private_deal-{deal.deal_id}')
    await msg.answer(f'Запрошую тебе стати {roles[role]} в приватній угоді. Щоб прийняти пропозицію натисни на кнопку!',
                     reply_markup=to_bot_kb(text=f'Стати {roles[role]}', url=link), disable_web_page_preview=True)


async def save_deal_role(msg: Message, deal_db: DealRepo, post_db: PostRepo, state: FSMContext):
    role = 'executor' if msg.text == Buttons.deal.executor else 'customer'
    await state.update_data(role=role)
    deal = await deal_db.add(**{role + '_id': msg.from_user.id}, type=DealTypeEnum.PRIVATE,
                             status=DealStatusEnum.ACTIVE)
    post = await post_db.add(
        user_id=msg.from_user.id, title=f'Приватна угода #{deal.deal_id}',
        about=f'Власник угоди {msg.from_user.full_name} ({msg.from_user.id})',
        price=0
    )
    await deal_db.update_deal(deal.deal_id, post_id=post.post_id)
    await msg.answer('🎉 Нова приватна угода створена!\n\nПерешли наступне '
                     'повідомлення іншому учаснику, для того щоб розпочати', reply_markup=basic_kb([Buttons.menu.back]))
    await new_deal_invite_msg(msg, deal, state)
    await state.finish()


def setup(dp: Dispatcher):
    dp.register_message_handler(
        create_new_deal_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.new_deal, state='*')
    dp.register_message_handler(save_deal_role, ChatTypeFilter(ChatType.PRIVATE), state=PrivateDealSG.SelectRole)