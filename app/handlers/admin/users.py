from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.database.services.enums import UserStatusEnum
from app.database.services.repos import UserRepo, DealRepo, PostRepo, SettingRepo
from app.keyboards import Buttons
from app.keyboards.inline.admin import user_info_kb, user_search_cb, user_full_settings_kb
from app.keyboards.inline.back import back_kb
from app.keyboards.reply.menu import basic_kb


async def search_user_cmd(msg: Message, state: FSMContext, config: Config):
    admin_channel = await msg.bot.get_chat(config.misc.admin_channel_id)
    text = (
        'ℹ️ <b>Для того щоб знайти користувача, використайте будь-який з наступних методів пошуку</b>:\n\n'
        '<pre>1) Перешліть повідомлення від користувача\n'
        f'2) Перешліть пост з <a href="{admin_channel.invite_link}">адмін каналу</a>,'
        f'в якому брав участь цей користувач\n'
        '3) Напишіть номер (ID) угоди цілим числом, в якій брав участь цей користувач\n'
        '4) Напишіть повне або частину ім\'я користувача (мінімум 2 літери)</pre>'
    )
    await msg.answer(text, reply_markup=basic_kb([Buttons.admin.to_admin]), disable_web_page_preview=True)
    await state.set_state(state='admin_search')


async def send_user_info(msg: Message, user: UserRepo.model):
    await msg.answer(f'Знайдено користувача {user.create_html_link(user.full_name)}',
                     reply_markup=user_info_kb(user))


async def detail_user_info(upd: CallbackQuery | Message, callback_data: dict, user_db: UserRepo, deal_db: DealRepo,
                           setting_db: SettingRepo, state: FSMContext):
    user = await user_db.get_user(int(callback_data['user_id']))
    status = {
        UserStatusEnum.ACTIVE: '🟢 Активний',
        UserStatusEnum.BANNED: '🔴 Забанений'
    }
    text = (
        f'Повне ім\'я: {user.create_html_link(user.full_name)}\n'
        f'ТелеграмID: <code>{user.user_id}</code>\n'
        f'Баланс: {user.balance} грн.\n'
        f'Статус: {status[user.status]}\n'
    )
    deals_executor = await deal_db.get_deal_executor(user.user_id, '*')
    deals_customer = await deal_db.get_deal_customer(user.user_id, '*')
    rating = (await deal_db.calculate_user_rating(user.user_id))[0]
    setting = await setting_db.get_setting(user.user_id)

    text += (
        '\nАктивність:\n\n'
        f'Рейтинг: {rating} {user.emojize_rating_text(rating)}\n'
        f'В ролі замовника: {len(deals_customer)} угод\n'
        f'В ролі виконавця: {len(deals_executor)} угод\n\n'
    )
    if isinstance(upd, CallbackQuery):
        await upd.message.edit_text(text, reply_markup=user_full_settings_kb(setting, user))
    else:
        await upd.answer(text, reply_markup=user_full_settings_kb(setting, user))

async def search_user_database(msg: Message, user_db: UserRepo, deal_db: DealRepo,
                               post_db: PostRepo, state: FSMContext):
    if msg.forward_from:
        user = await user_db.get_user(msg.forward_from.id)
        if user:
            await send_user_info(msg, user)
            return
    elif msg.forward_from_message_id:
        post = await post_db.get_post_admin_channel(msg.forward_from_message_id)
        if post:
            deal = await deal_db.get_deal_post(post.post_id)
            if deal.customer_id and deal.executor_id:
                customer = await user_db.get_user(deal.customer_id)
                executor = await user_db.get_user(deal.executor_id)
                await send_user_info(msg, customer)
                await send_user_info(msg, executor)
                return
            else:
                user = await user_db.get_user(post.user_id)
                await send_user_info(msg, user)
                return
    else:
        if str(msg.text).isnumeric():
            deal = await deal_db.get_deal(int(msg.text))
            if deal:
                if deal.customer_id and deal.executor_id:
                    customer = await user_db.get_user(deal.customer_id)
                    executor = await user_db.get_user(deal.executor_id)
                    await send_user_info(msg, customer)
                    await send_user_info(msg, executor)
                    return
                else:
                    user = await user_db.get_user(deal.customer_id)
                    await send_user_info(msg, user)
                    return
        else:
            if len(msg.text) >= 2:
                users = []

                for user in await user_db.get_all():
                    msg_input = msg.text.lower().replace(f'#{user.user_id}', '')
                    if user.full_name.lower() == msg_input and msg.text[-1] != '+':
                        await send_user_info(msg, user)
                        await msg.answer(f'Щоб побачити інші результати введіть <code>{msg_input}+</code>')
                        return
                    if user.full_name.lower().replace('+', '').startswith(msg.text.lower()):
                        users.append(user)
                    elif msg.text.lower().replace('+', '') in user.full_name.lower():
                        users.append(user)
                if users:
                    text = f'Знайдено {len(users)} користувачів із текстовим збігом "{msg.text}":\n\n'
                    for user, n in zip(users, range(len(users))):
                        text += f'{n+1}. <code>{user.full_name}#{user.user_id}</code>'
                    await msg.answer(text)
                    return
            else:
                await msg.answer('Ви надіслали занадто малий текст для пошуку')
                return
    await msg.answer('Не зміг знайти користувача :(', reply_markup=basic_kb([Buttons.admin.to_admin]))


def setup(dp: Dispatcher):
    dp.register_message_handler(search_user_cmd, text=Buttons.admin.user, state='*')
    dp.register_message_handler(search_user_database, state='admin_search')
    dp.register_callback_query_handler(detail_user_info, user_search_cb.filter(), state='*')