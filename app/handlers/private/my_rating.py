from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, \
    CallbackQuery

from app.config import Config
from app.database.services.repos import UserRepo, DealRepo
from app.keyboards import Buttons
from app.keyboards.inline.moderate import comment_deals_kb
from app.keyboards.reply.menu import basic_kb
from app.states.states import UserAboutSG
from app.handlers.private.participate import is_valid_comment

async def my_rating_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user = await user_db.get_user(msg.chat.id)
    await msg.answer(await user.construct_my_rating(deal_db),
                     reply_markup=comment_deals_kb())

async def add_user_about(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    text = (
        'Будь ласка напишіть короткий опис про себе (до 500 символів)'
    )
    last_msg = await call.message.answer(text, reply_markup=basic_kb([Buttons.menu.back]))
    await state.update_data(last_msg_id=last_msg.message_id)
    await UserAboutSG.Input.set()


async def save_user_about(msg: Message, user_db: UserRepo, deal_db: DealRepo, state: FSMContext, config: Config):
    data = await state.get_data()
    if 'last_msg_id' in data.keys():
        try:
            await msg.bot.delete_message(msg.from_user.id, data['last_msg_id'])
        except:
            pass
    await msg.delete()
    user_about = msg.html_text
    if len(user_about) > 500:
        error_text = (
            f'Максимальна к-ть символів 500, замість {len(user_about)}, спробуй ще раз'
        )
        await msg.answer(error_text)
        return
    valid_about = is_valid_comment(user_about)['status']
    if valid_about == 'not valid':
        await msg.answer('Твій опис було  відхилено. Оскільки він містить заборонені посилання або теги. '
                         'Ти можеш написати його знову.')
        return
    elif valid_about == 'suspiciously':
        warning = (
            f'🔴 #ПідозрілийВислів\n\n'
            f'Користувач {msg.from_user.get_mention()} ({msg.from_user.id}) '
            f'використав підозрілий вираз в своєму описі\n\n'
            f'<i>{msg.text}</i>'
        )
        await msg.bot.send_message(
            config.misc.admin_channel_id, warning)
    await user_db.update_user(msg.from_user.id, description=user_about)
    await my_rating_cmd(msg, user_db, deal_db)


async def user_comments_list(query: InlineQuery, deal_db: DealRepo, user_db: UserRepo):
    results = []
    deals = await deal_db.get_comment_deals(query.from_user.id)
    if not deals:
        results.append(
            InlineQueryResultArticle(
                id='unknown',
                title=f'Відгуки про тебе не знайдені',
                input_message_content=InputTextMessageContent('Нажаль у цього виконавця ще немає відгуків'),
            )
        )
    else:
        for deal in deals:
            customer = await user_db.get_user(deal.customer_id)
            comment = f' {deal.comment}' if deal.comment else 'Без коментаря'
            text = (
                f'{customer.emojize_rating_text(deal.rating)} від {customer.full_name}\n'
                f'{deal.updated_at.strftime("%d.%m.%Y")} {comment}'
            )
            results.append(
                InlineQueryResultArticle(
                    id=deal.deal_id,
                    title=f'{customer.emojize_rating_text(deal.rating)} від {customer.full_name}',
                    description=f'{deal.updated_at.strftime("%d.%m.%Y")} {comment}',
                    input_message_content=InputTextMessageContent(text),
                )
            )

    await query.answer(results, is_personal=True, cache_time=5)


def setup(dp: Dispatcher):
    dp.register_inline_handler(user_comments_list, text='Відгуки', state='*')
    dp.register_callback_query_handler(add_user_about, text='edit_about', state='*')
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE),
                                text=Buttons.menu.my_rating, state='*')
    dp.register_message_handler(save_user_about, ChatTypeFilter(ChatType.PRIVATE), state=UserAboutSG.Input)