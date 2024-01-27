import re

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType, CallbackQuery
from marshmallow import pprint

from app.config import Config
from app.database.services.enums import DealStatusEnum, OrderTypeEnum
from app.database.services.repos import UserRepo, OrderRepo, DealRepo, MerchantRepo
from app.fondy.new_api import FondyApiWrapper
from app.keyboards import Buttons
from app.keyboards.inline.pay import payout_kb, payout_cb
from app.keyboards.reply.menu import basic_kb


def is_valid_credit_card(card_number):
    pattern = re.compile(r'^[4-6]\d{3}-?\d{4}-?\d{4}-?\d{4}$')
    if re.match(pattern, card_number):
        return True
    else:
        return False

async def my_balance_cmd(msg: Message, user_db: UserRepo):
    user = await user_db.get_user(msg.from_user.id)
    await msg.answer(f'Ваш баланс {user.balance} грн',
                     reply_markup=basic_kb(([Buttons.menu.payout], [Buttons.menu.inn], [Buttons.menu.back])))


async def payout_cmd(msg: Message, order_db: OrderRepo, deal_db: DealRepo, state: FSMContext):
    deals = await deal_db.get_deal_executor(msg.from_user.id, DealStatusEnum.DONE)
    orders_to_pay = []
    cards = set()
    for deal in deals:
        orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)
        orders_payouted = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.PAYOUT)
        for order in orders:
            if order.request_answer['response']['order_status'] == 'approved':
                orders_to_pay.append(order)
        for order in orders_payouted:
            if order.request_answer['response']['order_status'] == 'approved':
                cards.add(order.request_body['receiver_card_number'])
    if orders_to_pay:
        cards = list(cards)
        payout = round(sum([order.calculate_payout() for order in orders_to_pay]) / 100, 2)
        text = f'Вам доступна сума до виплати {payout} грн'
        if cards:
            await msg.answer(text, reply_markup=payout_kb(cards, msg.from_user.id))
        else:
            await msg.answer(text + '\n\nВкажіть карту на яку зарахуються кошти 👇')
            await state.set_state(state='card_input')
    else:
        await msg.answer('На вашому рахуку немає коштів')

async def save_card_and_make_payout(upd: Message | CallbackQuery, state: FSMContext, fondy: FondyApiWrapper,
                                    deal_db: DealRepo, order_db: OrderRepo, merchant_db: MerchantRepo,
                                    callback_data: dict = None):
    if isinstance(upd, Message):
        msg = upd
        card_number = msg.text.replace(' ', '').strip()
    else:
        card_number = callback_data['card']
        msg = upd.message
    if not is_valid_credit_card(card_number):
        await msg.answer('Вказано невірний номер карти, перевір будь ласка та спробуй ще раз')
        return
    deals = await deal_db.get_deal_executor(msg.from_user.id, DealStatusEnum.DONE)
    orders_to_pay = {}
    for deal in deals:
        orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)
        for order in orders:
            if order.request_answer['response']['order_status'] == 'approved':
                if order.merchant_id in orders_to_pay.keys():
                    orders_to_pay.update({order.merchant_id: orders_to_pay[order.merchant_id] + [order]})
                else:
                    orders_to_pay.update({order.merchant_id: [order]})
    successful_payout = []
    for merchant in orders_to_pay.keys():
        orders = orders_to_pay.get(merchant)
        merchant = await merchant_db.get_merchant(merchant)
        for order in orders:
            order: OrderRepo.model
            deal = await deal_db.get_deal(order.deal_id)
            result = await make_payout(
                fondy,
                dict(deal=deal, merchant=merchant, card_number=card_number, amount=order.calculate_payout()),
                msg.bot)
            successful_payout.append(result)
    if any(successful_payout):
        await msg.answer('Виплата пройшла успішно. Очікуйте на зарахування коштів')
    else:
        await msg.answer('Проблеми з виплатою коштів. З\'ясовую причину')
    await state.finish()

async def make_payout(fondy: FondyApiWrapper, payout_data: dict, bot: Bot):
    response, order = await fondy.payout_order(**payout_data)
    if response['response']['order_status'] not in ['approved', 'processing']:
        config = Config.from_env()
        await bot.send_message(config.misc.admin_help_channel_id,
                               f'🔴💳 Не вдалось зробити <b>payout</b>\n\n{order.id=}\n\n'
                               f'<code>{order.request_answer}</code>')
        return False
    else:
        return True

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
        payout_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.payout, state='*')
    dp.register_message_handler(
        input_inn_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.inn, state='*')
    dp.register_message_handler(save_user_inn, ChatTypeFilter(ChatType.PRIVATE), state='inn_set')
    dp.register_message_handler(save_card_and_make_payout, ChatTypeFilter(ChatType.PRIVATE), state='card_input')
    dp.register_callback_query_handler(save_card_and_make_payout, payout_cb.filter(action='payout'))

