import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType

from app.database.services.repos import DealRepo, UserRepo
from app.keyboards.inline.chat import room_cb
from app.misc.pirce import PriceList

NEW_PRICE_REGEX = re.compile(
    r'^\d{2,5}$'
)


async def edit_price_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo,
                         user_db: UserRepo, state: FSMContext):
    await call.message.delete()
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    price_list = PriceList.current()
    text = (
        f'Щоб встановити ціну угоди, {executor.create_html_link("Виконавець")} та '
        f'{customer.create_html_link("Замовник")} повинні відправити одне й те саме ціле число. '
        f'Мінімальна ціна — {price_list.minimal_price} грн.\n\n'
        f'ℹ В нашому сервісі встановлена комісія, з якою Ви можете ознайомитись за посиланням.'
    )
    await call.message.answer(text, disable_web_page_preview=True)
    await state.storage.set_state(chat=call.message.chat.id, user=deal.customer_id, state='set_price')
    await state.storage.set_state(chat=call.message.chat.id, user=deal.executor_id, state='set_price')
    await state.storage.update_data(chat=call.message.chat.id, user=deal.customer_id, price=0)
    await state.storage.update_data(chat=call.message.chat.id, user=deal.executor_id, price=0)


async def handle_new_price(msg: Message, state: FSMContext, deal_db: DealRepo, user_db: UserRepo):
    new_price = int(msg.text)
    deal = await deal_db.get_deal_chat(msg.chat.id)
    price_list = PriceList.current()
    if not price_list.minimal_price <= new_price <= price_list.maximal_price:
        text = (
            f'Нова ціна угоди має бути не меншою за {price_list.minimal_price} та не більшою за '
            f'{price_list.maximal_price} грн.'
        )
        await msg.reply(text)
        return
    await msg.reply(f'Ви становили ціну - {new_price} грн')
    await state.storage.update_data(chat=msg.chat.id, user=msg.from_user.id, price=new_price)
    customer_data = await state.storage.get_data(chat=msg.chat.id, user=deal.customer_id)
    executor_data = await state.storage.get_data(chat=msg.chat.id, user=deal.executor_id)
    if customer_data['price'] == executor_data['price'] and customer_data['price'] != 0:
        customer = await user_db.get_user(deal.customer_id)
        await apply_new_price(msg, deal_db, deal, state, customer, new_price)
        return
    if customer_data['price'] == 0 or executor_data['price'] == 0:
        if customer_data['price'] == 0:
            user = await user_db.get_user(deal.customer_id)
        else:
            user = await user_db.get_user(deal.executor_id)
        await msg.answer(f'{user.mention}, відправте таке ж саме число, щоб підтвердити зміну ціни.')
    else:
        await msg.answer('Ціни які ви вказали не співпадають.')


async def apply_new_price(msg: Message, deal_db: DealRepo, deal: DealRepo.model,
                          state: FSMContext, customer: UserRepo.model, price: int):
    text = (
        f'Ціна угоди була успішно змінена на {price} грн.\n\n'
    )
    if deal.payed == 0:
        text += (
            'Якщо все готово, переходьте до оплати угоди /menu'
        )
    else:
        if price > deal.payed:
            text += (
                f'Тепер {customer.create_html_link("Замовник")} повинен доплатити '
                f'різницю у розмірі {price-deal.payed} грн.'
            )
        else:
            text += (
                f'Різниця у розмірі {price - deal.payed} грн. буде нарахована {customer.create_html_link("Замовнику")} '
                f'на баланс.'
            )
    await msg.answer(text)
    await deal_db.update_deal(deal.deal_id, price=price)
    await state.storage.reset_data(chat=msg.chat.id, user=deal.executor_id)
    await state.storage.reset_data(chat=msg.chat.id, user=deal.customer_id)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        edit_price_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='price'), state='*'
    )
    dp.register_message_handler(
        handle_new_price, ChatTypeFilter(ChatType.GROUP), regexp=NEW_PRICE_REGEX, state='set_price'
    )