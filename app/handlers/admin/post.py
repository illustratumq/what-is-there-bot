from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hide_link
from apscheduler_di import ContextSchedulerDecorator

from app.config import Config
from app.database.models import Post
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import PostRepo, UserRepo, DealRepo, MarkerRepo
from app.filters import IsAdminFilter
from app.keyboards.inline.moderate import confirm_post_moderate, moderate_post_kb, moderate_post_cb
from app.keyboards.inline.post import participate_kb
from app.misc.times import next_run_time


async def back_moderate_post(call: CallbackQuery, callback_data: dict, post_db: PostRepo, user_db: UserRepo,
                             config: Config):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    await call.bot.edit_message_text(
        chat_id=config.misc.admin_channel_id, message_id=post.message_id, text=post.construct_post_text(use_bot_link=False),
        reply_markup=moderate_post_kb(post)

    )


async def approve_post_publish(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                               user_db: UserRepo, config: Config):
    post_id = int(callback_data['post_id'])
    admin = await user_db.get_user(call.from_user.id)
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
                           deal_db: DealRepo, config: Config):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    admin_channel_text = (
        f'<b>Пост #{post.post_id} відхилено</b>\n\n'
        f'{post.construct_post_text(use_bot_link=False)}'
    )
    await deal_db.delete_deal(post.deal_id)
    await post_db.delete_post(post.post_id)
    await call.message.edit_text(admin_channel_text, disable_web_page_preview=True if post.media_url else False)
    await call.bot.send_message(post.user_id, text=f'Ваш пост "{post.title}" було відхилено адміністрацією')


async def admin_approve_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo, deal_db: DealRepo,
                            marker_db: MarkerRepo, user_db: UserRepo, config: Config,
                            scheduler: ContextSchedulerDecorator):
    admin_id = int(callback_data['admin_id'])
    admin = await user_db.get_user(admin_id)
    if call.from_user.id != admin_id:
        return await call.answer(f'Цей пост вже модерує {admin.full_name}', show_alert=True)

    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    message = await call.bot.send_message(
        config.misc.reserv_channel_id, post.construct_post_text(),
        reply_markup=participate_kb(await post.construct_participate_link()),
        disable_web_page_preview=True if not post.media_id else False
    )
    await post_db.update_post(post_id, status=DealStatusEnum.ACTIVE, reserv_message_id=message.message_id)
    await deal_db.update_deal(post.deal_id, status=DealStatusEnum.ACTIVE)
    scheduler.add_job(
        publish_post_base_channel, trigger='date', next_run_time=next_run_time(60), misfire_grace_time=600,
        kwargs=dict(post=post, bot=call.bot, post_db=post_db, marker_db=marker_db),
        name=f'Публікація поста #{post.post_id} на основному каналі'
    )
    await call.answer('Публікацію підтверджено')
    admin_channel_text = (
        f'<b>Статус:</b> Пост #{post.post_id} схвалено ✔\n'
        f'<b>Модератор:</b> {call.from_user.mention}\n\n'
        f'{post.construct_post_text(use_bot_link=False)}'
    )
    await call.message.edit_text(text=admin_channel_text, disable_web_page_preview=True if post.media_url else False)


async def publish_post_base_channel(post: Post, bot: Bot, post_db: PostRepo, marker_db: MarkerRepo, config: Config):
    post = await post_db.get_post(post.post_id)
    reply_markup = participate_kb(await post.construct_participate_link()) if post.status == DealStatusEnum.ACTIVE else None
    message = await bot.send_message(
        config.misc.post_channel_chat_id, post.construct_post_text(),
        reply_markup=reply_markup, disable_web_page_preview=True if not post.media_id else False
    )
    await post_db.update_post(post.post_id, message_id=message.message_id, post_url=message.url)
    await bot.send_message(post.user_id, text=f'Ваш пост "{post.title}" опубліковано {hide_link(message.url)}')
    markers = await marker_db.get_markers_title(post.title)
    for marker in markers:
        try:
            await bot.send_message(
                marker.user_id,
                text=f'На каналі з\'явився пост по вашій підписці "{marker.text}"{hide_link(message.url)}'
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
