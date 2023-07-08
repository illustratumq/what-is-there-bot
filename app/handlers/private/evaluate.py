from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.services.repos import DealRepo, UserRepo
from app.keyboards.inline.chat import evaluate_deal_kb, evaluate_cb, Buttons
from app.keyboards.reply.menu import menu_kb
from app.states.states import CommentSG


async def evaluate_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo):
    deal_id = int(callback_data['deal_id'])
    value = int(callback_data['value'])
    deal = await deal_db.get_deal(deal_id)
    await deal_db.update_deal(deal_id, rating=value)
    text = (
        'Бажаєте поділитися своїм досвідом про роботу цього виконавця?'
    )
    await call.message.edit_text(text, reply_markup=evaluate_deal_kb(deal, comment=True))


async def comment_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo,
                           state: FSMContext):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    text = (
        f'{call.message.text}\n\n'
        f'Будь-ласка, напишіть свій відгук (до 500 символів) 👇'
    )
    msg = await call.message.edit_text(text, reply_markup=evaluate_deal_kb(deal, only_close=True))
    await state.update_data(deal_id=deal_id, last_msg_id=msg.message_id)
    await CommentSG.Input.set()


async def save_comment_deal(msg: Message, deal_db: DealRepo, user_db: UserRepo, state: FSMContext):
    data = await state.get_data()
    deal_id = data['deal_id']
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    last_msg_id = data['last_msg_id']
    comment = msg.html_text
    await msg.delete()
    if len(comment) > 300:
        await msg.answer(f'Упс, ваш відгук занадто великий ({len(comment)}/500), будь-ласка спробуйте ще раз.')
        return
    await deal_db.update_deal(deal_id, comment=comment)
    await msg.bot.delete_message(msg.from_user.id, last_msg_id)
    await msg.answer('Дякуємо за ваш відгук!', reply_markup=menu_kb())
    await msg.bot.send_message(deal.executor_id, f'Замовник {customer.create_html_link(customer.full_name)} '
                                                 f'залишив відгук, про роботу з вами. Передивитись його можна в розділі'
                                                 f'"{Buttons.menu.my_rating}"')
    await state.finish()


async def cancel_evaluate_deal(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.finish()


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(evaluate_deal_cmd, evaluate_cb.filter(action='eval'), state='*')
    dp.register_callback_query_handler(comment_deal_cmd, evaluate_cb.filter(action='comment'), state='*')
    dp.register_callback_query_handler(cancel_evaluate_deal, evaluate_cb.filter(action='close'), state='*')
    dp.register_message_handler(save_comment_deal, state=CommentSG.Input)
