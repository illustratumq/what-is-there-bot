from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.repos import CommissionRepo
from app.filters import IsAdminFilter
from app.keyboards.reply.admin import admin_kb, Buttons, construct_packs_kb

filters = (
    IsAdminFilter(), ChatTypeFilter(ChatType.PRIVATE)
)


async def admin_cmd(msg: Message, state: FSMContext):
    await state.finish()
    await msg.answer('Ви перейшли в адмін панель', reply_markup=admin_kb())


async def commission_cmd(msg: Message, commission_db: CommissionRepo):
    packs = await commission_db.get_all()
    text = (
        'Оберіть комісійний пакет, або додайте новий\n\n'
        f'{construct_commission_info(packs)}'
    )
    reply_markup = construct_packs_kb([pack.name for pack in packs])
    await msg.answer(text, reply_markup=reply_markup)


def setup(dp: Dispatcher):
    dp.register_message_handler(admin_cmd, *filters, state='*', text=(Buttons.menu.admin, Buttons.admin.back))
    dp.register_message_handler(commission_cmd, *filters, state='*', text=Buttons.admin.commission)


def construct_commission_info(commissions: list[CommissionRepo.model]):
    text = ''
    for pack, num in zip(commissions, range(1, len(commissions) + 1)):
        text += f'{num}. {pack.name}\n'
    return text