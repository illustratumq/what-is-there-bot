from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatType
from aiogram.utils.markdown import hide_link

from app.database.services.enums import OrderStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, CommissionRepo, OrderRepo
from app.fondy.api import FondyApiWrapper
from app.handlers.group.price import pay_method_choose
from app.keyboards.inline.deal import to_bot_kb
from app.keyboards.inline.pay import confirm_pay_kb, pay_cb, pay_deal_kb


async def confirm_pay_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                           user_db: UserRepo, commission_db: CommissionRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    need_to_pay = deal.price - deal.payed
    user = await user_db.get_user(call.from_user.id)

    commission_package = await commission_db.get_commission(user.commission_id)
    commission = commission_package.deal_commission(deal)

    if callback_data['action'] == 'pay_from_balance':
        pay_method = 'використавши всю суму з балансу'
    elif callback_data['action'] == 'pay_fully':
        pay_method = 'сплативши всю суму через платіжну систему'
    else:
        pay_method = 'списавши частину з балансу, а решту сплатити через платіжну систему'
    text = (
        f'➡️ Ви бажаєте оплатити угоду "{post.title}" у розмірі {need_to_pay + commission} грн,  '
        f'<b>{pay_method}</b>.\n\n Будь-ласка підтвердіть своє рішення'
    )
    await call.message.edit_text(text, reply_markup=confirm_pay_kb(deal, callback_data['action']))


async def pay_from_fondy_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                             user_db: UserRepo, commission_db: CommissionRepo, fondy: FondyApiWrapper,
                             order_db: OrderRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    order = await order_db.get_order_deal(deal.deal_id)
    need_to_pay = deal.price - deal.payed
    commission_package = await commission_db.get_commission(customer.commission_id)
    commission = commission_package.deal_commission(deal)
    pay_from_balance = False

    if callback_data['action'] == 'conf_pay_partially':
        if 0 < customer.balance < need_to_pay + commission:
            need_to_pay -= customer.balance
            pay_from_balance = customer.balance
            await user_db.update_user(customer.user_id, balance=0)
        else:
            await call.answer('Упс, на вашому рахунку вже більше коштів, ніж необхідно для часткової оплати з балансу.'
                              'Будь-ласка поверніться назад та оберіть метод оплати ще раз.', show_alert=True)
            return
    if order and order.status == OrderStatusEnum.PROCESSING and order.url:
        url = order.url
    else:
        response, order = await fondy.create_order(deal, user_db, post_db, order_db, need_to_pay + commission)
        if response['response']['response_status'] != 'success':
            await call.message.answer(response)
            return
        url = response['response']['checkout_url']
        await order_db.update_order(order.id, status=OrderStatusEnum.PROCESSING, url=url)
        if pay_from_balance:
            body = order.body
            body.update(pay_from_balance=pay_from_balance)
            await order_db.update_order(order.id, body=body)
    await call.message.delete()
    text = (
        f'🧾 <b>Ваш чек на оплату угоди #{deal.deal_id}</b>\n\n'
        f'Будь-ласка оплатіть угоду натиснувши на кнопку {hide_link(url)}'
    )
    await call.message.answer(text, reply_markup=to_bot_kb(url=url, text='Оплатити'))

async def pay_from_balance_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                               user_db: UserRepo, commission_db: CommissionRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    need_to_pay = deal.price - deal.payed
    customer = await user_db.get_user(deal.customer_id)
    commission_package = await commission_db.get_commission(customer.commission_id)
    commission = commission_package.deal_commission(deal)
    if customer.balance < need_to_pay:
        await call.answer('На вашому рахунку бракує коштів', show_alert=True)
        return
    await call.message.delete()
    post = await post_db.get_post(deal.post_id)
    executor = await user_db.get_user(deal.executor_id)
    await user_db.update_user(deal.customer_id, balance=customer.balance - need_to_pay - commission)
    await deal_db.update_deal(deal.deal_id, payed=deal.payed + need_to_pay, commission=deal.commission + commission)
    text_to_chat = (
        f'<b>💳 Угода була успішно сплачена, кошти зберігаються на балансі сервісу.</b>\n\n'
        f'{executor.create_html_link(executor.full_name)} можете приступати до роботи, '
        f'{customer.create_html_link(customer.full_name)}, чекайте на рішення.'
    )
    text_to_customer = (
        f'<i>Угода #{deal.deal_id} успішно оплачена. З вашого рахунку списано {need_to_pay + commission} грн.</i>'
    )
    await call.message.answer(text_to_customer)
    await call.bot.send_message(deal.chat_id, text_to_chat)


async def back_to_pay_method(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                             post_db: PostRepo, commission_db: CommissionRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    post = await post_db.get_post(deal.post_id)
    await call.message.delete()
    await pay_method_choose(call.message, deal, customer, post, commission_db)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        confirm_pay_deal, ChatTypeFilter(ChatType.PRIVATE),
        pay_cb.filter(action=['pay_from_balance', 'pay_fully', 'pay_partially']), state='*'),
    dp.register_callback_query_handler(
        pay_from_fondy_cmd, ChatTypeFilter(ChatType.PRIVATE),
        pay_cb.filter(action=['conf_pay_fully', 'conf_pay_partially']), state='*')
    dp.register_callback_query_handler(
        back_to_pay_method, ChatTypeFilter(ChatType.PRIVATE), pay_cb.filter(action='cancel_pay'), state='*')
    dp.register_callback_query_handler(
        pay_from_balance_cmd, ChatTypeFilter(ChatType.PRIVATE), pay_cb.filter(action='conf_pay_from_balance'),
        state='*')