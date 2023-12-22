import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType
from aiogram.utils.deep_linking import get_start_link

from app.database.services.repos import DealRepo, UserRepo, PostRepo, CommissionRepo
from app.keyboards.inline.chat import room_cb, back_chat_kb, room_pay_kb
from app.keyboards.inline.deal import to_bot_kb
from app.keyboards.inline.pay import pay_deal_kb

NEW_PRICE_REGEX = re.compile(
    r'^\d{2,5}$'
)


async def edit_price_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo,
                         user_db: UserRepo, commission_db: CommissionRepo, state: FSMContext):
    await call.message.delete()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    commission = await commission_db.get_commission(customer.commission_id)
    text = (
        f'Щоб встановити ціну угоди, {customer.full_name} та '
        f'{executor.full_name} повинні відправити одне й те саме ціле число. '
        f'Мінімальна ціна — {commission.minimal} грн.\n\n'
        f'ℹ В нашому сервісі встановлена комісія, з якою Ви можете ознайомитись за посиланням.'
    )
    await call.message.answer(text, disable_web_page_preview=True, reply_markup=back_chat_kb(deal))
    await state.storage.set_state(chat=call.message.chat.id, user=deal.customer_id, state='set_price')
    await state.storage.set_state(chat=call.message.chat.id, user=deal.executor_id, state='set_price')
    await state.storage.update_data(chat=call.message.chat.id, user=deal.customer_id, price=0)
    await state.storage.update_data(chat=call.message.chat.id, user=deal.executor_id, price=0)


async def handle_new_price(msg: Message, state: FSMContext, deal_db: DealRepo, user_db: UserRepo,
                           commission_db: CommissionRepo):
    new_price = int(msg.text)
    deal = await deal_db.get_deal_chat(msg.chat.id)
    customer = await user_db.get_user(deal.customer_id)
    commission = await commission_db.get_commission(customer.commission_id)
    if not commission.minimal <= new_price <= commission.maximal:
        text = (
            f'Нова ціна угоди має бути не меншою за {commission.minimal} та не більшою за '
            f'{commission.maximal} грн.'
        )
        await msg.reply(text, reply_markup=back_chat_kb(deal))
        return
    await state.storage.update_data(chat=msg.chat.id, user=msg.from_user.id, price=new_price)
    customer_data = await state.storage.get_data(chat=msg.chat.id, user=deal.customer_id)
    executor_data = await state.storage.get_data(chat=msg.chat.id, user=deal.executor_id)
    if customer_data['price'] == 0 or executor_data['price'] == 0:
        if customer_data['price'] == 0:
            user = await user_db.get_user(deal.customer_id)
        else:
            user = await user_db.get_user(deal.executor_id)
        await msg.answer(f'{user.mention}, відправте таке ж саме число, '
                         f'щоб підтвердити зміну ціни.')
    elif customer_data['price'] == executor_data['price'] and customer_data['price'] != 0:
        customer = await user_db.get_user(deal.customer_id)
        await apply_new_price(msg, deal_db, deal, state, customer, new_price)
        return
    else:
        await msg.answer('Ціни які ви вказали не співпадають.')


async def apply_new_price(msg: Message, deal_db: DealRepo, deal: DealRepo.model,
                          state: FSMContext, customer: UserRepo.model, price: int):
    text = (
        f'🔔 Ціна угоди була успішно змінена на {price} грн.\n\n'
    )
    reply_markup = None
    if deal.payed == 0:
        text += (
            'Якщо все готово, переходьте до оплати угоди'
        )
        reply_markup = to_bot_kb(url=await get_start_link(f'pay_deal-{deal.deal_id}'))
    else:
        if price > deal.payed:
            text += (
                f'Тепер {customer.create_html_link(customer.full_name)} повинен доплатити '
                f'різницю у розмірі {price-deal.payed} грн.'
            )
            reply_markup = room_pay_kb(deal)
        else:
            text += (
                f'Різниця у розмірі {price - deal.payed} грн. буде нарахована '
                f'{customer.create_html_link(customer.full_name)} на баланс.'
            )
    await msg.answer(text, reply_markup=reply_markup)
    await deal_db.update_deal(deal.deal_id, price=price)
    await state.storage.reset_data(chat=msg.chat.id, user=deal.executor_id)
    await state.storage.reset_data(chat=msg.chat.id, user=deal.customer_id)
    await deal.create_log(deal_db, f'Встановлена нова ціна {price} грн.')


async def pay_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    if call.from_user.id == deal.executor_id:
        text = (
            'Ця кнопка доступна тільки Замовнику. Якщо бажаєте, щоб Замовник '
            'оплатив угоду, напишіть про це в чаті.'
        )
        await call.answer(text, show_alert=True)
        return
    if deal.price == 0:
        await call.answer('Ціна угоди не визначена', show_alert=True)
        return
    elif deal.payed >= deal.price:
        await call.answer('Угода вже оплачена 👌', show_alert=True)
        return
    await call.answer()
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text = (
        f'{customer.create_html_link(customer.full_name)} оплачує угоду в особистому чаті з ботом.\n\n'
        f'{executor.create_html_link(executor.full_name)} не приступайте до роботи, поки не побачите повідомлення від '
        f'бота про успішну оплату угоди.'
    )
    await call.message.delete()
    await call.bot.send_message(deal.chat_id, text,
                                reply_markup=to_bot_kb(await get_start_link(f'pay_deal-{deal.deal_id}')))

def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        edit_price_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='price'), state='*'
    )
    dp.register_message_handler(
        handle_new_price, ChatTypeFilter(ChatType.GROUP), regexp=NEW_PRICE_REGEX, state='set_price'
    )
    dp.register_callback_query_handler(
        pay_deal_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='pay'), state='*'
    )