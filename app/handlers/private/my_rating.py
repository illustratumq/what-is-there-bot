from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType, CallbackQuery
from aiogram.utils.markdown import hide_link

from app.database.services.enums import DealStatusEnum
from app.database.services.repos import UserRepo, DealRepo, PostRepo
from app.keyboards import Buttons
from app.keyboards.inline.moderate import comment_deal_kb, comment_deal_cb
from app.keyboards.reply.menu import basic_kb
from app.states.states import UserAboutSG


async def my_rating_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user = await user_db.get_user(msg.chat.id)
    await msg.answer(await user.construct_my_rating(deal_db),
                     reply_markup=basic_kb(([Buttons.menu.about, Buttons.menu.comment], [Buttons.menu.back])))


async def add_user_about(msg: Message):
    text = (
        'Будь ласка напишіть короткий опис про себе (до 500 символів)'
    )
    await msg.answer(text, reply_markup=basic_kb([Buttons.menu.to_rating]))
    await UserAboutSG.Input.set()


async def save_user_about(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user_about = msg.html_text
    if len(user_about) > 500:
        error_text = (
            f'Максимальна к-ть символів 500, замість {len(user_about)}, спробуй ще раз'
        )
        await msg.answer(error_text)
        return
    await user_db.update_user(msg.from_user.id, description=user_about)
    await my_rating_cmd(msg, user_db, deal_db)

async def preview_my_comments_cmd(msg: Message, deal_db: DealRepo, post_db: PostRepo, user_db: UserRepo):
    deals = await deal_db.get_deal_executor(executor_id=msg.from_user.id, status=DealStatusEnum.DONE)
    if not deals:
        await msg.answer('Про вас ще немає відгуків. Зверніть увагу, відгук можна залишиити лише про виконавця.')
        return
    await msg.delete()
    deal_id = deals[0].deal_id
    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)
    customer = await user_db.get_user(msg.from_user.id)
    text = (
        f'Угода: {post.title} {hide_link(post.post_url)}\n\n'
        f'Оцінка: {customer.emojize_rating_text(deal.rating)} ({deal.rating}/5)\n\n'
        f'💬 {customer.full_name}: <i>{deal.comment}</i>\n\n'
        f'Відгук {deals.index(deal) + 1} з {len(deals)}'
    )
    await msg.answer(text, reply_markup=comment_deal_kb(deals, deal_id))


async def view_my_comments_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                               user_db: UserRepo):
    if callback_data['action'] == 'cancel':
        await call.message.delete()
        await my_rating_cmd(call.message, user_db, deal_db)
        return

    customer = await user_db.get_user(call.from_user.id)
    deals = await deal_db.get_deal_executor(executor_id=call.from_user.id, status=DealStatusEnum.DONE)

    if len(deals) == 1:
        await call.answer('У вас тільки один відгук', show_alert=True)
        return

    if 'deal_id' in callback_data.keys():
        deal_id = int(callback_data['deal_id'])
    else:
        deal_id = deals[0].deal_id
        callback_data.update(sort='default')

    sort_switch = callback_data['action'] == 'sort_switch'
    if sort_switch:
        modes = ['default', 'max', 'min']
        callback_data.update(sort=modes[(modes.index(callback_data['sort']) + 1) % 3])

    if callback_data['sort'] == 'max':
        deals.sort(key=lambda d: d.rating, reverse=True)
        if sort_switch:
            deal_id = deals[0].deal_id
    elif callback_data['sort'] == 'min':
        deals.sort(key=lambda d: d.rating, reverse=False)
        if sort_switch:
            deal_id = deals[0].deal_id
    else:
        deals.sort(key=lambda d: d.updated_at)
        if sort_switch:
            deal_id = deals[0].deal_id

    deal = await deal_db.get_deal(deal_id)
    post = await post_db.get_post(deal.post_id)

    text = (
        f'Угода: {post.title} {hide_link(post.post_url)}\n\n'
        f'Оцінка: {customer.emojize_rating_text(deal.rating)} ({deal.rating}/5)\n\n'
        f'💬 {customer.full_name}: <i>{deal.comment}</i>\n\n'
        f'Відгук {deals.index(deal) + 1} з {len(deals)}'
    )
    await call.message.edit_text(text, reply_markup=comment_deal_kb(deals, deal_id, callback_data['sort']))


def setup(dp: Dispatcher):
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.to_rating, state='*')
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_rating, state='*')
    dp.register_message_handler(add_user_about, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.about, state='*')
    dp.register_message_handler(save_user_about, ChatTypeFilter(ChatType.PRIVATE), state=UserAboutSG.Input)

    dp.register_message_handler(preview_my_comments_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.comment,
                                state='*')
    dp.register_callback_query_handler(view_my_comments_cmd, ChatTypeFilter(ChatType.PRIVATE),
                                       comment_deal_cb.filter(), state='*')