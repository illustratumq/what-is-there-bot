import re

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType, CallbackQuery

from app.config import Config
from app.database.services.enums import DealStatusEnum, OrderTypeEnum
from app.database.services.repos import UserRepo, OrderRepo, DealRepo, MerchantRepo
from app.fondy.new_api import FondyApiWrapper
from app.keyboards import Buttons
from app.keyboards.inline.pay import payout_kb, payout_cb, card_confirm_kb
from app.keyboards.reply.menu import basic_kb


def is_valid_credit_card(card_number):
    pattern = re.compile(r'^[4-6]\d{3}-?\d{4}-?\d{4}-?\d{4}$')
    if re.match(pattern, card_number):
        return True
    else:
        return False

async def my_balance_cmd(msg: Message, order_db: OrderRepo, deal_db: DealRepo,
                         user_db: UserRepo, state: FSMContext):
    user = await user_db.get_user(msg.from_user.id)
    if not user.is_inn_exist():
        await msg.answer('Твій ІПН(РНОКПП) не знайдено, будь ласка заповни цю інформацію 👇')
        await state.set_state(state='inn_set')
        return
    deals = await deal_db.get_deal_executor(msg.from_user.id, DealStatusEnum.DONE)
    orders_to_pay = []
    cards = set()
    for deal in deals:
        orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)
        orders_done = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.PAYOUT)
        for order in orders:
            if order.is_valid_response() and order.is_order_status('approved') and not order.payed:
                orders_to_pay.append(order)
        for order in orders_done:
            if order.is_valid_response() and order.is_order_status('approved'):
                cards.add(order.get_request_body['receiver_card_number'])
    if orders_to_pay:
        cards = list(cards)
        payout = round(sum([order.calculate_payout() for order in orders_to_pay]) / 100, 1)
        text = f'Тобі доступна сума до виплати {payout} грн'
        if cards:
            text += '\n\nОберіть карту для виплати 👇'
            await msg.answer(text, reply_markup=payout_kb(cards, msg.from_user.id))
        else:
            await msg.answer(text + '\n\nВкажи карту, на яку зарахуються кошти 👇',
                            reply_markup=basic_kb([Buttons.menu.back]))
            await state.set_state(state='card_input')
    else:
        await msg.answer('На вашому рахуку немає коштів')

async def save_card(msg: Message, state: FSMContext):
    card_number = msg.text.replace(' ', '').strip()
    if not is_valid_credit_card(card_number):
        await msg.answer('Вказано невірний номер карти, перевір будь ласка та спробуй ще раз')
        return
    else:
        await msg.answer('Ти бажаєш здійснити виплату за даним номером карти?',
                         reply_markup=card_confirm_kb(card_number, msg.from_user.id))
        await state.finish()

async def add_new_card_to_payout(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer('Вкажіть карту на яку зарахуються кошти 👇')
    await state.set_state(state='card_input')

async def save_card_and_make_payout(upd: Message | CallbackQuery, state: FSMContext, fondy: FondyApiWrapper,
                                    deal_db: DealRepo, order_db: OrderRepo, merchant_db: MerchantRepo,
                                    callback_data: dict = None):
    user_id = upd.from_user.id
    if isinstance(upd, Message):
        msg = upd
        card_number = msg.text.replace(' ', '').strip()
    else:
        card_number = callback_data['card']
        msg = upd.message
    await msg.delete()
    deals = await deal_db.get_deal_executor(user_id, DealStatusEnum.DONE)
    orders_to_pay = {}
    for deal in deals:
        orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)
        for order in orders:
            if order.is_valid_response() and order.is_order_status('approved') and not order.payed:
                if order.merchant_id in orders_to_pay.keys():
                    if order.deal_id in orders_to_pay[order.merchant_id].keys():
                        orders_to_pay.update({order.merchant_id:
                                                  {order.deal_id: orders_to_pay[order.merchant_id][order.deal_id] + [order]}
                        })
                    else:
                        orders_to_pay.update({order.merchant_id:
                                                  {order.deal_id: [order]}
                                              })
                else:
                    orders_to_pay.update({order.merchant_id: {order.deal_id: [order]}})
    for merchant in orders_to_pay.keys():
        orders = orders_to_pay.get(merchant)
        for deal in orders.keys():
            merchant = await merchant_db.get_merchant(merchant)
            deal = await deal_db.get_deal(deal)
            price_sum = []
            for order in orders_to_pay[merchant.merchant_id][deal.deal_id]:
                price_sum.append(order.calculate_payout())
                await order_db.update_order(order.id, payed=True)
                await order_db.create_log(order.id, 'Спроба виплатити кошти')
            price_sum = sum(price_sum)
            result, order_payout, error_message = await make_payout(
                fondy,
                dict(deal=deal, merchant=merchant, card_number=card_number, amount=price_sum),
                msg.bot
            )
            await order_db.create_log(order_payout.id,
                                      f'Створено платіж на виплату суми {round(price_sum/100, 2)} грн.')
            if result:
                await msg.answer('Виплата пройшла успішно. Очікуйте на зарахування коштів')
                # await order_db.update_order(order_payout.id, )
                for order in orders_to_pay[merchant.merchant_id][deal.deal_id]:
                    await order_db.create_log(order.id,
                                              f'Платіж успішно виплачено, ID платіжу виплати={order_payout.id}')
            else:
                await msg.answer('🫤 Проблеми з виплатою коштів. З\'ясовую причину\n\nПідтримка: @ENTER_help')
                for order in orders_to_pay[merchant.merchant_id][deal.deal_id]:
                    await order_db.update_order(order.id, payed=False)
                    await order_db.create_log(order.id, f'Невдала спроба виплати коштів: {error_message}')

    await state.finish()

async def make_payout(fondy: FondyApiWrapper, payout_data: dict, bot: Bot):
    response, order = await fondy.payout_order(**payout_data)
    if 'error_message' in response['response'].keys():
        config = Config.from_env()
        await bot.send_message(config.misc.admin_help_channel_id,
                               f'🔴💳 Не вдалось зробити <b>payout</b>\n\n{order.id=}\n\n'
                               f'<code>{order.request_answer}</code>')
        return False, order, order.request_answer['response']['error_message']
    elif response['response']['order_status'] in ['approved', 'processing']:
        return True, order, None

async def input_inn_cmd(msg: Message, user_db: UserRepo, state: FSMContext):
    user = await user_db.get_user(msg.from_user.id)
    if user.inn:
        await msg.answer(f'Твій ІПН: {user.inn}',
                         reply_markup=basic_kb([Buttons.menu.to_payout]))
    else:
        await msg.answer(
            'Твій ІПН не знайдено, будь ласка заповни цю інформацію 👇',
            reply_markup=basic_kb([Buttons.menu.to_payout])
        )
        await state.set_state(state='inn_set')


async def save_user_inn(msg: Message, user_db: UserRepo, state: FSMContext):
    inn = msg.text.strip()
    if inn.isalnum():
        if len(inn) != 10:
            await msg.answer('Кількість цифр має дорівнювати 10, будь ласка повтори спробу')
        else:
            inn = int(inn)
            await user_db.update_user(msg.from_user.id, inn=inn)
            await msg.answer('Твій ІПН успішно додано!',
                             reply_markup=basic_kb([Buttons.menu.to_payout]))
            await state.finish()
    else:
        await msg.answer('ІПН має містити тільки цифри, будь ласка повтори спробу')


def setup(dp: Dispatcher):
    dp.register_message_handler(my_balance_cmd, ChatTypeFilter(ChatType.PRIVATE),
                                text=[Buttons.menu.my_money, Buttons.menu.to_payout], state='*')
    dp.register_message_handler(
        input_inn_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.inn, state='*')
    dp.register_callback_query_handler(add_new_card_to_payout, payout_cb.filter(action='add_new_card'),
                                       state='*')
    dp.register_message_handler(save_card, ChatTypeFilter(ChatType.PRIVATE), state='card_input')
    dp.register_message_handler(save_user_inn, ChatTypeFilter(ChatType.PRIVATE), state='inn_set')
    # dp.register_message_handler(save_card_and_make_payout, ChatTypeFilter(ChatType.PRIVATE), state='card_input')
    dp.register_callback_query_handler(save_card_and_make_payout, payout_cb.filter(action='payout'),
                                       state='*')

