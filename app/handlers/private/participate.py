import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import JoinStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, JoinRepo, LetterRepo
from app.keyboards.inline.deal import moderate_deal_kb, deal_cb, pagination_deal_kb, comment_cb, send_deal_kb
from app.states.states import ParticipateSG

MAX_CHAR_IN_MESSAGE = 4096

def is_valid_comment(text: str) -> dict:
    for word in text.split(' '):
        if any([re.match(r'@([A-z]+)$', word), re.match(r'https?\S+', word)]):
            return {'status': 'not valid'}
    else:
        if re.match(r'([A-z]+)', text):
            return {'status': 'suspiciously'}
        else:
            return {'status': 'ok'}


async def save_deal_comment(msg: Message, join_db: JoinRepo, config: Config, state: FSMContext):
    await msg.delete()
    data = await state.get_data()
    join = await join_db.get_join(data['join_id'])
    ban = False
    if join:
        text_status = is_valid_comment(msg.text)['status']
        if text_status == 'not valid':
            text = (
                '<b>Твій коментар було відхилено.</b>\n\n'
                'Оскільки він містить заборонені посилання або теги. '
                'Якщо хочеш перезаписати його, відправ новий коментар знову.'
            )
            ban = True
        else:
            text = (
                '<b>Твій коментар було збережено.</b>\n\n'
                'Якщо хочеш перезаписати його, відправ новий коментар знову.\n\n'
                f'Твій коментар: <i>{msg.text}</i>'
            )
            await join_db.update_join(join.join_id, comment=msg.text)
            if text_status != 'ok':
                warning = (
                    f'#ПідозрілийВислів\n\n'
                    f'Користувач {msg.from_user.get_mention()} ({msg.from_user.id}) '
                    f'використав підозрілий вираз в своєму коментарі на виконання запиту:\n\n'
                    f'<i>{msg.text}</i>'
                )
                await msg.bot.send_message(
                    config.misc.admin_channel_id, warning)
        await msg.bot.edit_message_text(text, chat_id=msg.from_user.id, message_id=join.join_msg_id,
                                        reply_markup=send_deal_kb(join, ban=ban))
    else:
        await msg.answer('Нажаль я не можу отримати інформацію про твій запит. Будь ласка спробуй ще раз')


async def close_deal_cmd(call: CallbackQuery, callback_data: dict, join_db: JoinRepo, state: FSMContext):
    await state.finish()
    join = await join_db.get_join(int(callback_data['join_id']))
    if join:
        await call.bot.delete_message(call.from_user.id, join.join_msg_id)
        await call.bot.delete_message(call.from_user.id, join.post_msg_id)
        if join.one_time_join:
            await join_db.delete_join(join.join_id)
    else:
        await call.answer('Нажаль я не можу отримати інформацію про твій запит')
        await call.message.delete()

async def send_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                        user_db: UserRepo, join_db: JoinRepo, state: FSMContext):
    join = await join_db.get_join(int(callback_data['join_id']))
    post = await post_db.get_post(join.post_id)
    user = await user_db.get_user(join.executor_id)
    deal = await deal_db.get_deal(join.deal_id)
    comment = f'\n\nКоментар: {join.comment}' if join.comment else ''
    text_to_customer = (
        f'{await user.construct_preview_text(deal_db)}'
        f'{comment} {hide_link(post.post_url)}\n'
    )
    is_comment_deals = await deal_db.get_comment_deals(call.from_user.id)
    await call.bot.send_message(
        deal.customer_id, text_to_customer,
        reply_markup=moderate_deal_kb(join, is_comment_deals=is_comment_deals))
    await call.bot.delete_message(call.from_user.id, join.post_msg_id)
    text_to_executor = (
        f'<b>Ви відправили запит на виконання завдання 👌</b>\n\n'
        f'Завдання: {post.title} {hide_link(post.post_url)}'
    )
    await join_db.update_join(join.join_id, status=JoinStatusEnum.ACTIVE)
    await call.message.edit_text(text_to_executor)
    await state.finish()


async def pagination_comments_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                  post_db: PostRepo, join_db: JoinRepo):
    join = await join_db.get_join(int(callback_data['join_id']))
    executor = await user_db.get_user(join.executor_id)
    deals = await deal_db.get_comment_deals(executor_id=join.executor_id)

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
    reply_markup = pagination_deal_kb(join.executor_id, deals_id, deal_id, original_id, sort)
    await call.message.edit_text(text, reply_markup=reply_markup)


async def back_send_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                         user_db: UserRepo, join_db: JoinRepo):
    deal_id = int(callback_data['original_id'])
    executor_id = int(callback_data['executor_id'])
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    user = await user_db.get_user(call.from_user.id)
    join = await join_db.get_post_join(deal.customer_id, deal.executor_id, deal.post_id)
    comment = f'Коментар:\n\n{deal.comment}' if deal.comment else ''
    text_to_customer = (
        f'{await user.construct_preview_text(deal_db)}'
        f'{comment} {hide_link(post.post_url)}'
    )
    is_comment_deals = await deal_db.get_comment_deals(executor_id)
    reply_markup = moderate_deal_kb(join=join, is_comment_deals=is_comment_deals)
    await call.message.edit_text(text_to_customer, reply_markup=reply_markup)


async def cancel_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                          user_db: UserRepo, join_db: JoinRepo, letter_db: LetterRepo):
    join = await join_db.get_join(int(callback_data['join_id']))
    post = await post_db.get_post(join.post_id)
    executor = await user_db.get_user(join.executor_id)
    await letter_db.add(
        text=f'Ви відхилили запит на виконнання вашого завдання від {executor.full_name}\n\nЗавдання: {post.title}',
        user_id=join.customer_id, join_id=join.join_id
    )
    await call.message.delete()
    await call.answer(f'Ви відхилили запит на виконнання вашого завдання від {executor.full_name}')
    text_to_executor = (
        f'Ваш запит на виконання завдання був відхилений замовником {hide_link(post.post_url)}'
    )
    await letter_db.add(
        text=text_to_executor, user_id=join.executor_id, join_id=join.join_id
    )
    await call.bot.send_message(join.executor_id, text_to_executor)


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
