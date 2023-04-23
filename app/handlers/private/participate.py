from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType
from aiogram.utils.markdown import hide_link

from app.database.services.repos import DealRepo, PostRepo, UserRepo
from app.keyboards.inline.deal import moderate_deal_kb, deal_cb
from app.states.states import ParticipateSG


async def save_deal_comment(msg: Message, state: FSMContext):
    await msg.reply('Ваш коментар було збережено. Якщо хочете перезаписати його, відправте новий коментар знову.')
    await state.update_data(comment=msg.html_text)


async def close_deal_cmd(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()


async def send_deal_cmd(call: CallbackQuery, state: FSMContext, deal_db: DealRepo, post_db: PostRepo,
                        user_db: UserRepo):
    data = await state.get_data()
    deal_id = data['deal_id']
    comment = data['comment']
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    user = await user_db.get_user(call.from_user.id)
    willing_ids = deal.willing_ids
    if call.from_user.id not in willing_ids:
        willing_ids.append(call.from_user.id)
        await deal_db.update_deal(data['deal_id'], willing_ids=willing_ids)
    done_deals, rating_deals, rating = await deal_db.calculate_user_rating(user.user_id)
    comment = f'Коментар:\n\n{comment}' if comment else ''
    text_to_customer = (
        f'{user.construct_preview_text(rating, done_deals, rating_deals)}\n'
        f'{comment} {hide_link(post.post_url)}'
    )
    await call.bot.send_message(deal.customer_id, text_to_customer, reply_markup=moderate_deal_kb(deal, call.from_user.id))
    await call.message.delete()
    text_to_executor = (
        f'Ви відправили запит на виконання завдання "{post.title}" {hide_link(post.post_url)} 👌'
    )
    await call.message.answer(text_to_executor)
    await state.finish()


async def cancel_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                          user_db: UserRepo):
    deal_id = int(callback_data['deal_id'])
    executor_id = int(callback_data['executor_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    executor = await user_db.get_user(executor_id)
    text_to_customer = (
        f'Ви відхилили запит на виконнання вашого завдання від {executor.full_name} {hide_link(post.post_url)}'
    )
    text_to_executor = (
        f'Ваш запит на виконання завдання був відхилений замовником {hide_link(post.post_url)}'
    )
    await call.message.edit_text(text_to_customer)
    await call.bot.send_message(executor_id, text_to_executor)


def setup(dp: Dispatcher):
    dp.register_message_handler(
        save_deal_comment, ChatTypeFilter(ChatType.PRIVATE), state=ParticipateSG.Comment)
    dp.register_callback_query_handler(
        send_deal_cmd, ChatTypeFilter(ChatType.PRIVATE), deal_cb.filter(action='send'), state='*')
    dp.register_callback_query_handler(
        close_deal_cmd, ChatTypeFilter(ChatType.PRIVATE), deal_cb.filter(action='close'), state='*'
    )
    dp.register_callback_query_handler(
        cancel_deal_cmd, ChatTypeFilter(ChatType.PRIVATE), deal_cb.filter(action='cancel'), state='*'
    )
