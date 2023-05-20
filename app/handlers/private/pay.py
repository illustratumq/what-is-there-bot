from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatType

from app.database.services.repos import DealRepo, PostRepo, UserRepo, CommissionRepo
from app.keyboards.inline.pay import confirm_pay_kb, pay_cb, pay_deal_kb


async def confirm_pay_deal_from_balance(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                                        user_db: UserRepo, commission_db: CommissionRepo):
    await call.message.delete()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    need_to_pay = deal.price - deal.payed
    user = await user_db.get_user(call.from_user.id)
    commission = await commission_db.get_commission(user.commission_id)
    commission = commission.calculate_commission(need_to_pay)
    text = (
        f'Ви бажаєте оплатити угоду "{post.title}" у розмірі {need_to_pay + commission} грн '
        f'({need_to_pay} + {commission} комісія) з вашого балансу, будь-ласка підтвердіть своє рішення.'
    )
    await call.message.answer(text, reply_markup=confirm_pay_kb(deal, callback_data['action']))


async def pay_from_balance_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                               user_db: UserRepo, commission_db: CommissionRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    need_to_pay = deal.price - deal.payed
    customer = await user_db.get_user(deal.customer_id)
    commission = await commission_db.get_commission(customer.commission_id)
    commission = commission.calculate_commission(need_to_pay)
    if customer.balance < need_to_pay:
        await call.answer('На вашому рахунку бракує коштів', show_alert=True)
        return
    await call.message.delete()
    post = await post_db.get_post(deal.post_id)
    executor = await user_db.get_user(deal.executor_id)
    await user_db.update_user(deal.customer_id, balance=customer.balance - need_to_pay - commission)
    await deal_db.update_deal(deal.deal_id, payed=need_to_pay)
    text_to_chat = (
        f'💸 Угода була успішно сплачена, кошти зберігаються на балансі сервісу.\n\n'
        f'{executor.create_html_link("Виконавець")} можете приступати до роботи!\n\n'
        f'Відкрити меню чату /menu'
    )
    text_to_executor = (
        f'🔔 Замовник оплатив угоду "{post.title}", можете приступати до виконання завдання.'
    )
    text_to_customer = (
        f'Угода успішно оплачена. З вашого рахунку списано {need_to_pay + commission} грн.'
    )
    await call.message.answer(text_to_customer)
    await call.bot.send_message(deal.executor_id, text_to_executor)
    await call.bot.send_message(deal.chat_id, text_to_chat)


async def back_to_pay_method(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                             post_db: PostRepo, commission_db: CommissionRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    post = await post_db.get_post(deal.post_id)
    await call.message.delete()
    need_to_pay = deal.price - deal.payed
    commission = await commission_db.get_commission(customer.commission_id)
    commission = commission.calculate_commission(need_to_pay)
    text = (
        f'Ви бажаєте оплатити угоду для вашого поста "{post.title}".\n\n'
        f'Встановлена ціна {deal.price} грн.\n'
        f'Сплачено: {deal.payed} грн.\n'
        f'Необхідно сплатити: {need_to_pay} грн + {commission} грн комісія сервісу.\n\n'
    )
    if customer.balance > 0 and customer.balance >= need_to_pay + commission:
        text += (
            f'На вашому рахунку {customer.balance} грн. Ви можете використати кошти на балансі. '
            f'Або оплатити всю суму угоди окремим платежем.\n\nБудь-ласка оберіть метод оплати.'
        )
        reply_markup = pay_deal_kb(deal, balance=True)
    elif 0 < customer.balance < need_to_pay + commission:
        text += (
            f'На вашому рахунку {customer.balance} грн. Ви можете використати частину коштів з балансу, '
            f'та оплатити решту у розмірі {need_to_pay - customer.balance} грн. '
            f'Або оплатити всю суму угоди окремим платежем.\n\n'
            f'Будь-ласка оберіть метод оплати.'
        )
        reply_markup = pay_deal_kb(deal, partially=True)
    else:
        text += (
            f'Будь-ласка сплатіть угоду, натиснувши кнопку нижче.'
        )
        reply_markup = pay_deal_kb(deal)

    await call.message.answer(text, reply_markup=reply_markup)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        confirm_pay_deal_from_balance, ChatTypeFilter(ChatType.PRIVATE), pay_cb.filter(action='pay_from_balance'),
        state='*')
    dp.register_callback_query_handler(
        back_to_pay_method, ChatTypeFilter(ChatType.PRIVATE), pay_cb.filter(action='cancel_pay'), state='*')
    dp.register_callback_query_handler(
        pay_from_balance_cmd, ChatTypeFilter(ChatType.PRIVATE), pay_cb.filter(action='conf_pay_from_balance'), state='*')