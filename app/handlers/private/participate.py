from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType
from aiogram.utils.markdown import hide_link

from app.database.services.repos import DealRepo, PostRepo, UserRepo
from app.keyboards.inline.deal import moderate_deal_kb, deal_cb, pagination_deal_kb, comment_cb
from app.states.states import ParticipateSG


MAX_CHAR_IN_MESSAGE = 4096


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
    comment = f'Коментар:\n\n{comment}' if comment else ''
    text_to_customer = (
        f'{await user.construct_preview_text(deal_db)}'
        f'{comment} {hide_link(post.post_url)}\n'
    )
    is_comment_deals = await deal_db.get_comment_deals(call.from_user.id)
    await call.bot.send_message(deal.customer_id, text_to_customer,
                                reply_markup=moderate_deal_kb(deal, call.from_user.id, is_comment_deals=is_comment_deals))
    await call.message.delete()
    text_to_executor = (
        f'Ви відправили запит на виконання завдання "{post.title}" {hide_link(post.post_url)} 👌'
    )
    await call.message.answer(text_to_executor)
    await state.finish()


async def pagination_comments_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                  post_db: PostRepo):
    executor_id = int(callback_data['executor_id'])
    executor = await user_db.get_user(executor_id)
    deals = await deal_db.get_comment_deals(executor_id=executor_id)

    sort_type_list = ['None', 'max', 'min']
    sort = callback_data['sort']
    if callback_data['action'] == 'sort':
        sort = sort_type_list[(sort_type_list.index(sort) + 1) % 3]

    if sort == 'max':
        deals.sort(key=lambda d: d.rating, reverse=True)
    elif sort == 'min':
        deals.sort(key=lambda d: d.rating, reverse=False)
    else:
        deals.sort(key=lambda d: d.updated_at)

    deals_id = [deal.deal_id for deal in deals]
    deal_id = deals[0].deal_id if callback_data['action'] in ('start', 'sort') else int(callback_data['deal_id'])
    original_id = int(callback_data['original_id']) if callback_data['action'] == 'start' else int(callback_data['original_id'])

    if callback_data['action'] == 'pag' and len(deals) <= 3:
        await call.answer('Більше відгуків немає')
        return

    text = f'{await executor.construct_preview_text(deal_db)}\n\n<b>Відгуки про роботу з {executor.full_name}:</b>'
    current_deal_index = deals_id.index(deal_id)
    page = '\n\nВідгуки {}-{} з {}'
    comment_counter = 0
    for deal in deals[current_deal_index:current_deal_index + 3]:
        customer = await user_db.get_user(deal.customer_id)
        post = await post_db.get_post(deal.post_id)
        comment = (
            f'\n\n{post.title}. Оцінка {deal.rating}.\n'
            f'💬 {customer.full_name}: <i>{deal.comment}</i>'
        )
        text += comment
        if len(text) > MAX_CHAR_IN_MESSAGE:
            text[(MAX_CHAR_IN_MESSAGE - len(page) - 10):] = '...'
            break
        comment_counter += 1
    text += page.format(current_deal_index + 1, current_deal_index + comment_counter, len(deals_id))
    reply_markup = pagination_deal_kb(executor_id, deals_id, deal_id, original_id, sort)
    await call.message.edit_text(text, reply_markup=reply_markup)


async def back_send_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                         user_db: UserRepo):
    deal_id = int(callback_data['original_id'])
    executor_id = int(callback_data['executor_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    user = await user_db.get_user(call.from_user.id)
    comment = f'Коментар:\n\n{deal.comment}' if deal.comment else ''
    text_to_customer = (
        f'{await user.construct_preview_text(deal_db)}'
        f'{comment} {hide_link(post.post_url)}'
    )
    is_comment_deals = await deal_db.get_comment_deals(executor_id)
    reply_markup = moderate_deal_kb(deal, executor_id, is_comment_deals=is_comment_deals)
    await call.message.edit_text(text_to_customer, reply_markup=reply_markup)


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
    dp.register_callback_query_handler(
        back_send_deal, ChatTypeFilter(ChatType.PRIVATE), comment_cb.filter(action='back'), state='*'
    )
    dp.register_callback_query_handler(
        pagination_comments_cmd, ChatTypeFilter(ChatType.PRIVATE), comment_cb.filter(), state='*'
    )
