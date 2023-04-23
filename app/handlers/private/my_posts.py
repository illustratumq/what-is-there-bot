from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, CallbackQuery, ChatType
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.models import Post
from app.database.services.enums import PostStatusText, DealStatusEnum
from app.database.services.repos import PostRepo, DealRepo
from app.handlers.private.start import start_cmd
from app.keyboards import Buttons
from app.keyboards.inline.post import construct_posts_list_kb, post_cb, moderate_post_kb, participate_kb, delete_post_kb
from app.keyboards.reply.menu import basic_kb
from app.misc.times import localize, now


async def my_posts_cmd(msg: Message, post_db: PostRepo):
    posts = await post_db.get_posts_user(msg.from_user.id, DealStatusEnum.ACTIVE)
    if not posts:
        await msg.answer('Спочатку опублікуйте хоча б один пост 🙂')
        return
    posts.sort(key=lambda post: post.created_at)
    text = (
        f'📑 Ваші пости, опубліковані на каналі:\n\n'
        f'{construct_posts_list(posts)}\n'
    )
    await msg.answer(text, reply_markup=construct_posts_list_kb(posts))
    text = (
        f'Ви можете видалити або оновити пост в каналі, якщо він має статус '
        f'"{PostStatusText.ACTIVE}".'
    )
    await msg.answer(text, reply_markup=basic_kb([Buttons.menu.back]))


async def edit_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    await call.message.edit_text(
        text=hide_link(post.post_url) + post.construct_post_text(use_bot_link=False),
        reply_markup=moderate_post_kb(post)
    )


async def delete_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    text = (
        f'{hide_link(post.post_url)}{post.construct_post_text(use_bot_link=False)}\n\n'
        f'<b>Ви дійсно бажаєте видалити цей пост?</b>'
    )
    await call.message.edit_text(
        text=text, reply_markup=delete_post_kb(post)
    )


async def confirm_delete_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, deal_db: DealRepo,
                                  config: Config, state: FSMContext):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    await call.bot.delete_message(
        chat_id=config.misc.post_channel_chat_id, message_id=post.message_id
    )
    await call.bot.delete_message(
        chat_id=config.misc.reserv_channel_id, message_id=post.reserv_message_id
    )
    await deal_db.delete_deal(post.deal_id)
    await post_db.delete_post(post_id)
    await call.answer('Пост було видалено', show_alert=True)
    posts = await post_db.get_posts_user(call.from_user.id, DealStatusEnum.ACTIVE)
    if posts:
        await back_posts_list_cmd(call, post_db)
    else:
        await call.message.delete()
        await start_cmd(call.message, state)


async def update_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, config: Config):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    seconds_after_public = (now() - localize(post.updated_at)).seconds
    if seconds_after_public >= 15*60:
        await call.bot.delete_message(
            config.misc.post_channel_chat_id, post.message_id
        )
        msg = await call.bot.send_message(
            config.misc.post_channel_chat_id, text=post.construct_post_text(),
            reply_markup=participate_kb(await post.construct_participate_link())
        )
        await call.answer('Ваш пост було оновлено в каналі', show_alert=True)
        await post_db.update_post(post.post_id, message_id=msg.message_id, post_url=msg.url)
        await edit_post_cmd(call, callback_data, post_db)
    else:
        text = (
            f'Ви можете оновлювати пост в каналі не раніше ніж 15 хв після його публікації. '
            f'Зачекайте {(15 * 60 - seconds_after_public) // 60} хв...'
        )
        await call.answer(text, show_alert=True)


async def close_posts_cmd(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await start_cmd(call.message, state)


async def back_posts_list_cmd(call: CallbackQuery, post_db: PostRepo):
    posts = await post_db.get_posts_user(call.from_user.id, DealStatusEnum.ACTIVE)
    if not posts:
        await call.message.answer('Спочатку опублікуйте хоча б один пост 🙂')
        return
    posts = [post for post in posts if post.message_id]
    posts.sort(key=lambda post: post.created_at)
    text = (
        f'📑 Ваші пости, опубліковані на каналі:\n\n'
        f'{construct_posts_list(posts)}\n'
        f'Ви можете видалити або оновити пост в каналі, якщо він має статус '
        f'"{PostStatusText.ACTIVE}".'
    )
    await call.message.edit_text(text, reply_markup=construct_posts_list_kb(posts))


def setup(dp: Dispatcher):

    dp.register_message_handler(my_posts_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_posts, state='*')
    dp.register_callback_query_handler(
        close_posts_cmd, ChatTypeFilter(ChatType.PRIVATE), post_cb.filter(action='back'), state='*')
    dp.register_callback_query_handler(
        edit_post_cmd, ChatTypeFilter(ChatType.PRIVATE), post_cb.filter(action='edit'), state='*')
    dp.register_callback_query_handler(
        back_posts_list_cmd, ChatTypeFilter(ChatType.PRIVATE), post_cb.filter(action='back_list'), state='*')
    dp.register_callback_query_handler(
        update_post_cmd, ChatTypeFilter(ChatType.PRIVATE, ), post_cb.filter(action='update'), state='*')
    dp.register_callback_query_handler(
        delete_post_cmd, ChatTypeFilter(ChatType.PRIVATE), post_cb.filter(action='delete'), state='*')
    dp.register_callback_query_handler(
        confirm_delete_post_cmd, ChatTypeFilter(ChatType.PRIVATE), post_cb.filter(action='conf_delete'), state='*')


def construct_posts_list(posts: list[Post]) -> str:
    text = ''
    for post, num in zip(posts, range(1, len(posts) + 1)):
        text += f'{num}. {post.title}\n'
    return text
