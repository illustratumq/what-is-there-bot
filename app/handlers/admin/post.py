from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hide_link
from apscheduler_di import ContextSchedulerDecorator

from app.config import Config
from app.database.models import Post
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import PostRepo, UserRepo, DealRepo, MarkerRepo, LetterRepo
from app.filters import IsAdminFilter
from app.keyboards.inline.moderate import confirm_post_moderate, moderate_post_kb, moderate_post_cb, \
    after_public_edit_kb, public_all_post_cb, public_post_cb
from app.keyboards.inline.post import participate_kb
from app.misc.times import next_run_time, now


async def back_moderate_post(call: CallbackQuery, callback_data: dict, post_db: PostRepo, user_db: UserRepo,
                             config: Config, state: FSMContext):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    await state.finish()
    await call.bot.edit_message_text(
        chat_id=config.misc.admin_channel_id, message_id=post.admin_message_id,
        text=post.construct_post_text(use_bot_link=False),
        reply_markup=moderate_post_kb(post)
    )


async def publish_all_confirm(call: CallbackQuery, callback_data: dict, post_db: PostRepo, user_db: UserRepo,
                              state: FSMContext):
    admin_id = int(callback_data['admin_id'])
    post_id = int(callback_data['post_id'])
    admin = await user_db.get_user(admin_id)
    post = await post_db.get_post(post_id)

    if admin and call.from_user.id != admin_id:
        return await call.answer(f'Цю дію вже модерує {admin.full_name}', show_alert=True)
    if not admin:
        admin = await user_db.get_user(call.from_user.id)

    data = await state.get_data()
    delay = data['current_delay'] if 'current_delay' in data.keys() else 30

    if callback_data['action'] == 'set_delay':
        delay = int(callback_data['delay'])
    elif callback_data['action'] == 'plus_delay':
        delay += int(callback_data['delay'])
    elif callback_data['action'] == 'minus_delay':
        delay -= int(callback_data['delay'])

    if delay < 10:
        await state.update_data(current_delay=10)
        await call.answer('Мінімальна затримка 10 секунд', show_alert=True)
        return

    posts = await post_db.get_posts_status(DealStatusEnum.MODERATE)
    end_published_time = now() + timedelta(seconds=len(posts) * delay)
    text = (
        f'Ви хочете опублікувати {len(posts)} постів?\n\n'
        f'Пости будуть опубліковані з затримкою {delay} секунд, орієнтовний час останньої публікації '
        f'{end_published_time.strftime("%H:%M:%S")}. Для того щоб змінити затримку між публікаціями '
        f'використовуйте кнопки нижче.\n\n'
        f'Будь-ласка, підтвердіть публікацію всіх постів.'
    )
    await call.message.edit_text(text, reply_markup=public_all_post_cb(admin, post, delay))
    await state.update_data(current_delay=delay)


async def publish_all_posts_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, user_db: UserRepo,
                                deal_db: DealRepo, marker_db: MarkerRepo, state: FSMContext, letter_db: LetterRepo,
                                scheduler: ContextSchedulerDecorator, config: Config):
    await state.finish()
    delay = int(callback_data['delay'])
    posts = await post_db.get_posts_status(DealStatusEnum.MODERATE)
    for post in posts:
        if post.admin_message_id:
            await post_db.update_post(post.post_id, status=DealStatusEnum.WAIT)
            await call.bot.edit_message_text(chat_id=config.misc.admin_channel_id, message_id=post.admin_message_id,
                                             text=post.construct_post_text(use_bot_link=False),
                                             disable_web_page_preview=False if post.media_url else True)
        scheduler.add_job(
            func=publish_all_posts_processing, name=f'Публікація поста в резервному каналі через {delay} c.',
            next_run_time=next_run_time(delay), trigger='date', misfire_grace_time=300,
            kwargs=dict(call=call, callback_data=callback_data, post_db=post_db, deal_db=deal_db,
                        marker_db=marker_db, user_db=user_db, letter_db=letter_db)
        )
        delay += delay
    await call.answer('Публікація постів успішно запланована', show_alert=True)
    await call.message.delete_reply_markup()


async def approve_post_publish(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                               user_db: UserRepo, config: Config):
    post_id = int(callback_data['post_id'])
    admin = await user_db.get_user(call.from_user.id)
    if not admin:
        await call.answer('Спочатку зареєструйтесь в боті (команда /start)', show_alert=True)
    post = await post_db.get_post(post_id)
    text = (
        f'{post.construct_post_text_shorted()}\n\n'
        f'Підтвредіть публікацію поста 👇'
    )
    await call.bot.edit_message_text(
        chat_id=config.misc.admin_channel_id, message_id=post.admin_message_id, text=text,
        reply_markup=confirm_post_moderate('approve', post, admin)
    )


async def cancel_post_publish(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                              user_db: UserRepo, config: Config):
    post_id = int(callback_data['post_id'])
    admin = await user_db.get_user(call.from_user.id)
    post = await post_db.get_post(post_id)
    text = (
        f'{post.construct_post_text_shorted()}\n\n'
        f'Підтвредіть скасування поста 👇'
    )
    await call.bot.edit_message_text(
        chat_id=config.misc.admin_channel_id, message_id=post.admin_message_id, text=text,
        reply_markup=confirm_post_moderate('cancel', post, admin)
    )


async def admin_cancel_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, user_db: UserRepo,
                           deal_db: DealRepo):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    admin_channel_text = (
        f'<b>Статус:</b> Пост #{post.post_id} відхилено\n'
        f'<b>Модератор:</b> {call.from_user.mention}\n\n'
        f'{post.construct_post_text(use_bot_link=False)}'
    )
    await deal_db.delete_deal(post.deal_id)
    await post_db.update_post(post.post_id, status=DealStatusEnum.DISABLES)
    # await post_db.delete_post(post.post_id)
    await call.message.edit_text(admin_channel_text, disable_web_page_preview=False if post.media_url else True)
    await call.bot.send_message(post.user_id, text=f'Ваш пост "{post.title}" було відхилено адміністрацією')


async def publish_all_posts_processing(call: CallbackQuery, callback_data: dict, post_db: PostRepo, deal_db: DealRepo,
                                       marker_db: MarkerRepo, user_db: UserRepo, config: Config, letter_db: LetterRepo,
                                       scheduler: ContextSchedulerDecorator):
    posts = await post_db.get_posts_status(DealStatusEnum.WAIT)
    posts.sort(key=lambda p: p.created_at)
    post = posts[0]
    callback_data.update(post_id=post.post_id)
    await admin_approve_cmd(call, callback_data, post_db, deal_db, marker_db, user_db, letter_db, config, scheduler)


async def admin_approve_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, deal_db: DealRepo,
                            marker_db: MarkerRepo, user_db: UserRepo, letter_db: LetterRepo, config: Config,
                            scheduler: ContextSchedulerDecorator):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    await post_db.update_post(post_id, status=DealStatusEnum.ACTIVE)
    message = await call.bot.send_message(
        config.misc.reserv_channel_id, post.construct_post_text(),
        reply_markup=participate_kb(await post.participate_link),
        disable_web_page_preview=True if not post.media_id else False
    )
    await post_db.update_post(post_id, reserv_message_id=message.message_id)
    await deal_db.update_deal(post.deal_id, status=DealStatusEnum.ACTIVE)
    scheduler.add_job(
        publish_post_base_channel, trigger='date', next_run_time=next_run_time(60), misfire_grace_time=600,
        kwargs=dict(post=post, bot=call.bot, post_db=post_db, marker_db=marker_db, user_db=user_db,
                    letter_db=letter_db, config=config),
        name=f'Публікація поста #{post.post_id} на основному каналі'
    )
    admin_channel_text = (
        f'<b>Статус:</b> Пост #{post.post_id} схвалено ✔\n'
        f'<b>Модератор:</b> {call.from_user.mention}\n\n'
        f'{post.construct_post_text(use_bot_link=False)}'
    )
    await call.bot.edit_message_text(text=admin_channel_text, chat_id=config.misc.admin_channel_id,
                                     message_id=post.admin_message_id, reply_markup=await after_public_edit_kb(post),
                                     disable_web_page_preview=False if post.media_url else True)


async def publish_post_base_channel(post: Post, bot: Bot, post_db: PostRepo, marker_db: MarkerRepo, user_db: UserRepo,
                                    letter_db: LetterRepo, config: Config):
    post = await post_db.get_post(post.post_id)
    if post:
        reply_markup = participate_kb(await post.participate_link) if post.status == DealStatusEnum.ACTIVE else None
        message = await bot.send_message(
            config.misc.post_channel_chat_id, post.construct_post_text(),
            reply_markup=reply_markup, disable_web_page_preview=True if not post.media_id else False
        )
        await post_db.update_post(post.post_id, message_id=message.message_id, post_url=message.url)
        await bot.send_message(post.user_id, text=f'Ваш пост опубліковано {hide_link(message.url)}')
        await letter_db.add(
            text=f'Ваш {post.construct_html_link("пост")} було опубліковано',
            user_id=post.user_id, post_id=post.post_id
        )
        await markers_post_processing(marker_db, post, bot, message.url, user_db)


async def markers_post_processing(marker_db: MarkerRepo, post: Post, bot: Bot, url: str, user_db: UserRepo):
    markers = await marker_db.get_markers_title(post.title)
    for marker in markers:
        try:
            user = await user_db.get_user(marker.user_id)
            start = int(user.time.split('-')[0])
            end = int(user.time.split('-')[1])
            if start < int(now().strftime('%H')) <= end:
                await bot.send_message(
                    marker.user_id,
                    text=f'На каналі з\'явився пост по вашій підписці "{marker.text}"{hide_link(url)}'
                )
        except:
            pass


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        back_moderate_post, IsAdminFilter(), moderate_post_cb.filter(action='back'), state='*'
    )
    dp.register_callback_query_handler(
        approve_post_publish, IsAdminFilter(), moderate_post_cb.filter(action='approve'), state='*')
    dp.register_callback_query_handler(
        cancel_post_publish, IsAdminFilter(), moderate_post_cb.filter(action='cancel'), state='*')
    dp.register_callback_query_handler(
        admin_approve_cmd, IsAdminFilter(), moderate_post_cb.filter(action='conf_approve'), state='*')
    dp.register_callback_query_handler(
        admin_cancel_cmd, IsAdminFilter(), moderate_post_cb.filter(action='conf_cancel'), state='*')
    dp.register_callback_query_handler(
        publish_all_confirm, IsAdminFilter(), moderate_post_cb.filter(action='publish_all'), state='*')
    dp.register_callback_query_handler(
        publish_all_posts_cmd, IsAdminFilter(), public_post_cb.filter(action='publish_all'), state='*')
    dp.register_callback_query_handler(
        publish_all_confirm, IsAdminFilter(), public_post_cb.filter(), state='*')
