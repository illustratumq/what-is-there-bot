import re

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, Message, ChatType, InlineQuery, InlineQueryResultArticle, \
    InputTextMessageContent
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import JoinStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, JoinRepo, LetterRepo
from app.filters.admin import CommentFilter
from app.keyboards.inline.deal import moderate_deal_kb, deal_cb, pagination_deal_kb, comment_cb, send_deal_kb, \
    executor_comments_kb
from app.states.states import ParticipateSG


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
                    f'🔴 #ПідозрілийВислів\n\n'
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
    text_to_executor = (
        f'<b>Ви відправили запит на виконання завдання 👌</b>\n\n'
        f'Завдання: {post.title} {hide_link(post.post_url)}'
    )
    await join_db.update_join(join.join_id, status=JoinStatusEnum.ACTIVE)
    await call.message.edit_text(text_to_executor)
    await state.finish()


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


async def cancel_deal_cmd(call: CallbackQuery):
    await call.message.delete()


async def send_comments_about_executor(call: CallbackQuery, callback_data: dict, user_db: UserRepo,
                                       join_db: JoinRepo):
    join = await join_db.get_join(int(callback_data.get('join_id')))
    await call.message.edit_reply_markup(reply_markup=moderate_deal_kb(join, is_comment_deals=[]))
    executor = await user_db.get_user(join.executor_id)
    await call.message.answer(
        text=f'Відгуки про {executor.full_name}', reply_markup=executor_comments_kb(join.executor_id)
    )


async def executor_comments_list(query: InlineQuery, deal_db: DealRepo, user_db: UserRepo):
    print('HERE')
    results = []
    query_split_data = query.query.split('@')
    if query_split_data[-1] != '':
        executor_id = int(query_split_data[-1])
    else:
        executor_id = 0
    deals = await deal_db.get_comment_deals(executor_id)
    if not deals:
        results.append(
            InlineQueryResultArticle(
                id='unknown',
                title=f'Відгуки не знайдені',
                input_message_content=InputTextMessageContent('Нажаль у цього виконавця ще немає відгуків'),
            )
        )
    else:
        for deal in await deal_db.get_comment_deals(executor_id):
            customer = await user_db.get_user(deal.customer_id)
            comment = f' {deal.comment}' if deal.comment else 'Без коментаря'
            results.append(
                InlineQueryResultArticle(
                    id=deal.deal_id,
                    title=f'{customer.emojize_rating_text(deal.rating)} від {customer.full_name}',
                    description=f'{deal.updated_at.strftime("%d.%m.%Y")} {comment}',
                    input_message_content=InputTextMessageContent(comment),
                )
            )
    await query.answer(results)

def setup(dp: Dispatcher):
    dp.register_inline_handler(executor_comments_list,
                               CommentFilter(), state='*')
    dp.register_callback_query_handler(send_comments_about_executor, ChatTypeFilter(ChatType.PRIVATE),
                                       deal_cb.filter(action='read_comments'), state='*')
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
