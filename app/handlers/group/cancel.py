import logging
import os
from pprint import pprint

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatType, ContentTypes, Message, InputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.enums import DealStatusEnum, RoomStatusEnum, DealTypeEnum, JoinStatusEnum, OrderTypeEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo, CommissionRepo, JoinRepo, LetterRepo, \
    OrderRepo, MerchantRepo
from app.fondy.new_api import FondyApiWrapper
from app.handlers.userbot import UserbotController
from app.keyboards import Buttons
from app.keyboards.inline.chat import close_deal_kb, confirm_moderate_kb, evaluate_deal_kb, room_cb
from app.keyboards.inline.deal import help_admin_kb
from app.keyboards.inline.post import participate_kb
from app.misc.media import make_post_media_template

log = logging.getLogger(__name__)


async def cancel_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    text = (
        'Оберіть тип завершення угоди\n\n'
        '<b>Завершити</b> - угода завершується та сплачені кошти нараховуються виконавцю.\n\n'
        '<b>Відмінити</b> - угода відміняється та сплачені кошти повертаються на баланс замовника.'
    )
    await call.message.edit_text(
        text, reply_markup=close_deal_kb(deal)
    )


async def confirm_done_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                state: FSMContext):
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    text = (
        f'Щоб <u>Завершити</u> угоду, {customer.create_html_link(customer.full_name)} повинен'
        f'підтвердити своє рішення. Для '
        f'цього він має натиснути кнопку "{Buttons.chat.confirm}", після цього <b>чат буде видалено.</b>\n\n'
        f'<b>Будь ласка, не забудьте зберігти матеріали угоди надіслані Виконавцем.</b>'
    )
    await call.message.edit_text(text=text, reply_markup=confirm_moderate_kb(deal, 'done_deal'))
    await state.storage.set_state(chat=call.message.chat.id, user=deal.customer_id, state='conf_done_deal')
    await state.storage.set_state(chat=call.message.chat.id, user=deal.executor_id, state='conf_done_deal')
    await state.storage.update_data(chat=call.message.chat.id, user=deal.executor_id, voted=False)
    await state.storage.update_data(chat=call.message.chat.id, user=deal.customer_id, voted=False)


async def confirm_cancel_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                  state: FSMContext):
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text = (
        f'Щоб <u>Відмінити</u> угоду, {customer.create_html_link(customer.full_name)} та '
        f'{executor.create_html_link(executor.full_name)} повинні підтвердити своє рішення. Для '
        f'цього обидва користувачі мають натиснути кнопку "{Buttons.chat.confirm}", після цього чат буде видалено.\n\n'
        f'Будь ласка, не забудьте зберігти матеріали угоди надіслані Виконавцем.'

    )
    await call.message.edit_text(text=text, reply_markup=confirm_moderate_kb(deal, 'cancel_deal'))
    await state.storage.set_state(chat=call.message.chat.id, user=deal.customer_id, state='conf_cancel_deal')
    await state.storage.set_state(chat=call.message.chat.id, user=deal.executor_id, state='conf_cancel_deal')
    await state.storage.update_data(chat=call.message.chat.id, user=deal.executor_id, voted=False)
    await state.storage.update_data(chat=call.message.chat.id, user=deal.customer_id, voted=False)


async def cancel_deal_processing(bot: Bot, deal: DealRepo.model, state: FSMContext, userbot: UserbotController,
                                 config: Config, fondy: FondyApiWrapper, session: sessionmaker,
                                 message: str = None, reset_state: bool = True):
    session: AsyncSession
    deal_db = DealRepo(session); post_db = PostRepo(session); room_db = RoomRepo(session)
    join_db = JoinRepo(session); user_db = UserRepo(session); order_db = OrderRepo(session)
    merchant_db = MerchantRepo(session)

    post = await post_db.get_post(deal.post_id)
    customer = await user_db.get_user(deal.customer_id)
    orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)

    deal_log_text = f'Угода відмінена.'

    reversed_orders = []
    for order in orders:
        merchant = await merchant_db.get_merchant(order.merchant_id)
        response = await fondy.check_order(order, merchant)
        if response['response']['order_status'] == 'approved':
            response = await fondy.reverse_order(order, merchant, 'Угода була відмінена' if not message else message)
            reversed_orders.append(order)
            if response['response']['reverse_status'] != 'approved':
                await bot.send_message(config.misc.admin_help_channel_id,
                                       text=f'🔴💳 Не вдалось зробити <b>reverse</b>\n\n{order.id=}')
    for user_id in deal.participants:
        text = f'Угода "{post.title}" була відмінена.' if not message else message
        await bot.send_message(user_id, text)
    if reversed_orders:
        reversal_amount = sum([int(order.request_body["amount"]/100) for order in reversed_orders])
        text = f'↪️💳 На ваш рахунок невдовзі буде повернено {reversal_amount} грн.'
        await bot.send_message(deal.customer_id, text)
        reversed_orders_str = ", ".join([str(order.id) for order in reversed_orders])
        deal_log_text += f'На рахунок {customer.full_name} повернено платежі: {reversed_orders_str}'

    await post_db.update_post(post.post_id, status=DealStatusEnum.ACTIVE)
    if deal.type == DealTypeEnum.PUBLIC:
        if deal.no_media:
            new_post_photo = make_post_media_template(post.title, post.about, post.price)
            photo_message = await bot.send_photo(config.misc.media_channel_chat_id, InputFile(new_post_photo))
            await post_db.update_post(post.post_id, media_url=photo_message.url)
            os.remove(new_post_photo)
        if post.message_id:
            await bot.delete_message(config.misc.post_channel_chat_id, post.message_id)
            post_channel = await bot.send_message(
                config.misc.post_channel_chat_id, post.construct_post_text(),
                reply_markup=participate_kb(await post.participate_link),
                disable_web_page_preview=True if not post.message_id else False
            )
            await post_db.update_post(post.post_id, message_id=post_channel.message_id, post_url=post_channel.url)
        if post.reserv_message_id:
            await bot.delete_message(config.misc.reserv_channel_id, post.reserv_message_id)
            reserv_channel = await bot.send_message(
                config.misc.reserv_channel_id, post.construct_post_text(),
                reply_markup=participate_kb(await post.participate_link),
                disable_web_page_preview=True if not post.message_id else False
            )
            await post_db.update_post(post.post_id, reserv_message_id=reserv_channel.message_id)

    await room_db.update_room(deal.chat_id, status=RoomStatusEnum.AVAILABLE, admin_required=False, admin_id=None,
                              message_id=None)
    if reset_state:
        await state.storage.reset_data(chat=deal.chat_id, user=deal.customer_id)
        await state.storage.reset_data(chat=deal.chat_id, user=deal.executor_id)

    await deal_db.update_deal(deal.deal_id, status=DealStatusEnum.DONE)
    room = await room_db.get_room(deal.chat_id)
    for user_id in [deal.customer_id, deal.executor_id, room.admin_id]:
        try:
            if user_id:
                if user_id not in (await userbot.get_client_user_id(), (await bot.me).id):
                    await userbot.kick_chat_member(room.chat_id, user_id)
        except Exception as error:
            log.error(str(error) + f'\n{deal.deal_id=}')

    if deal.type == DealTypeEnum.PRIVATE:
        if deal.customer_id == post.user_id:
            await deal_db.update_deal(deal.deal_id, executor_id=None)
        else:
            await deal_db.update_deal(deal.deal_id, customer_id=None)
    join = await join_db.get_post_join(deal.customer_id, deal.executor_id, post.post_id)
    await join_db.update_join(join.join_id, status=JoinStatusEnum.USED)
    await deal_db.update_deal(deal.deal_id, status=DealStatusEnum.ACTIVE, price=post.price,
                              payed=0, chat_id=None, executor_id=None, next_activity_date=None, activity_confirm=True)
    await deal.create_log(deal_db, deal_log_text)
    await session.commit()
    await session.close()


async def done_deal_processing(call: CallbackQuery, deal: DealRepo.model, state: FSMContext, userbot: UserbotController,
                               config: Config, fondy: FondyApiWrapper, session: sessionmaker):
    session: AsyncSession
    deal_db = DealRepo(session); post_db = PostRepo(session); room_db = RoomRepo(session); join_db = JoinRepo(session)
    user_db = UserRepo(session); order_db = OrderRepo(session); merchant_db = MerchantRepo(session)
    letter_db = LetterRepo(session)
    await call.message.delete_reply_markup()
    if deal.price == 0:
        text = (
            'Ціна угоди ще не визначена, для того щоб завершити угоду встановіть ціну та оплатіть її /menu'
        )
        await call.message.answer(text)
        return
    elif deal.payed == 0:
        text = (
            'Угода неоплачена, для того щоб завершити угоду будь ласка оплатіть її /menu'
        )
        await call.message.answer(text)
        return
    elif deal.price > deal.payed:
        text = (
            f'Угода була не повінстю сплачена. Ціна угоди становить: {deal.price} грн, з них сплачено '
            f'{deal.payed} грн. Для того, щоб завершити угоду сплатіть її повністю, або змініть ціну угоди.'
        )
        await call.message.answer(text)
        return
    else:
        deal_log_text = 'Угода завершилась за згодою користувачів.'
        orders = await order_db.get_orders_deal(deal.deal_id, OrderTypeEnum.ORDER)
        commission_for_executor = 0
        for order in orders:
            merchant = await merchant_db.get_merchant(order.merchant_id)
            response = await fondy.check_order(order, merchant)
            if response['response']['order_status'] == 'approved':
                response = await fondy.make_capture(order, merchant)
                if response['response']['capture_status'] != 'captured':
                    await call.bot.send_message(config.misc.admin_help_channel_id,
                                                text=f'🔴💳 Не вдалось зробити <b>capture</b>\n\n{order.id=}')
                actual_amount = int(response['response']['actual_amount'])
                amount = int(response['response']['amount'])
                commission_for_executor += round((actual_amount - amount) / 100, 2)
        executor = await user_db.get_user(deal.executor_id)
        customer = await user_db.get_user(deal.customer_id)
        balance_for_executor = executor.balance + deal.price - commission_for_executor
        await user_db.update_user(executor.user_id, balance=balance_for_executor)
        text = (
            f'На ваш рахунок зараховано {deal.price-commission_for_executor} грн. '
            f'Комісія становить {commission_for_executor} грн. '
            f'Ви можете вивести ці кошти на банківську карту, або використати для оплати іншої угоди.\n\n'
            f'Дякуємо за використання нашого сервісу.'
        )
        deal_log_text += f' {executor.full_name} нараховано {deal.price - commission_for_executor} грн.'
        await call.bot.send_message(deal.executor_id, text)
        room = await room_db.get_room(deal.chat_id)
        post = await post_db.get_post(deal.post_id)
        text = f'Угода "{post.title}" була завершена. Оцініть роботу виконавця від 1 до 5.'
        await call.bot.send_message(deal.customer_id, text, reply_markup=evaluate_deal_kb(deal))
        await post_db.update_post(post.post_id, status=DealStatusEnum.DONE)
        if deal.type == DealTypeEnum.PUBLIC:
            if deal.no_media:
                new_post_photo = make_post_media_template(post.title, post.about, post.price, version='done')
                photo_message = await call.bot.send_photo(config.misc.media_channel_chat_id, InputFile(new_post_photo))
                await post_db.update_post(post.post_id, media_url=photo_message.url)
                os.remove(new_post_photo)
            await call.bot.edit_message_text(
                post.construct_post_text(), config.misc.reserv_channel_id, post.reserv_message_id
            )
            if post.message_id:
                await call.bot.edit_message_text(
                    post.construct_post_text(), config.misc.post_channel_chat_id, post.message_id
                )
        await state.storage.reset_data(chat=call.message.chat.id, user=deal.customer_id)
        await state.storage.reset_data(chat=call.message.chat.id, user=deal.executor_id)

        await deal_db.update_deal(deal.deal_id, status=DealStatusEnum.DONE)
        for user_id in [deal.customer_id, deal.executor_id, room.admin_id]:
            try:
                if user_id:
                    if user_id not in (await userbot.get_client_user_id(), (await call.bot.me).id):
                        await userbot.kick_chat_member(deal.chat_id, user_id=user_id)
            except Exception as error:
                log.error(str(error) + f'\n{deal.deal_id=}')
        if deal.type == DealTypeEnum.PRIVATE:
            if deal.customer_id == post.user_id:
                await deal_db.update_deal(deal.deal_id, executor_id=None)
            else:
                await deal_db.update_deal(deal.deal_id, customer_id=None)
        letter_executor = f'Ви закінчили угоду "{post.title}", вам нараховано {deal.price - commission_for_executor} грн.'
        await letter_db.add(user_id=executor.user_id, text=letter_executor)
        await copy_and_delete_history(userbot, room, deal, customer, executor, config, call.bot)
        join = await join_db.get_post_join(deal.customer_id, deal.executor_id, post.post_id)
        if join:
            await join_db.update_join(join.join_id, status=JoinStatusEnum.USED)
        await room_db.update_room(deal.chat_id, status=RoomStatusEnum.AVAILABLE, admin_required=False, admin_id=None,
                                  message_id=None)
        await deal_db.update_deal(deal.deal_id, chat_id=None)
        await room_db.delete_room(room.chat_id)
        await deal.create_log(deal_db, deal_log_text)
        await session.commit()
        await session.close()


async def handle_confirm_done_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                   state: FSMContext, userbot: UserbotController, config: Config,
                                   fondy: FondyApiWrapper, session: sessionmaker):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    await state.storage.update_data(chat=call.message.chat.id, user=call.from_user.id, voted=True)
    customer_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.customer_id)
    if customer_data['voted']:
        await done_deal_processing(call, deal, state, userbot, config, fondy, session)
    else:
        user = customer if call.from_user.id == executor.user_id else executor
        await call.message.reply(f'Ваш голос зараховано!\nОчікуємо на голос {user.mention}.')


async def handle_confirm_cancel_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                     state: FSMContext, userbot: UserbotController, config: Config,
                                     fondy: FondyApiWrapper, session: sessionmaker):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    await state.storage.update_data(chat=call.message.chat.id, user=call.from_user.id, voted=True)
    customer_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.customer_id)
    executor_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.executor_id)
    if customer_data['voted'] and executor_data['voted']:
        await call.message.delete_reply_markup()
        await cancel_deal_processing(call.bot, deal, state, userbot, config, fondy, session)
    else:
        user = customer if call.from_user.id == executor.user_id else executor
        await call.message.reply(f'Ваш голос зараховано!\nОчікуємо на голос {user.mention}.')

async def delete_chat_by_activity(call: CallbackQuery, callback_data: dict, deal_db: DealRepo,
                                  state: FSMContext, userbot: UserbotController, config: Config,
                                  fondy: FondyApiWrapper, session: sessionmaker):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    await cancel_deal_processing(call.bot, deal, state, userbot, config, fondy, session)

async def left_chat_member_cancel(msg: Message, deal_db: DealRepo, user_db: UserRepo,
                                  post_db: PostRepo, state: FSMContext, room_db: RoomRepo, userbot: UserbotController,
                                  config: Config, fondy: FondyApiWrapper, session: sessionmaker):
    deal = await deal_db.get_deal_chat(msg.chat.id)
    if deal and deal.status != DealStatusEnum.DONE:
        customer = await user_db.get_user(deal.customer_id)
        post = await post_db.get_post(deal.post_id)
        user = 'Замовник' if msg.from_user.id == customer.user_id else 'Виконавець'
        if deal.payed == 0:
            text = (
                f'Угода "{post.title}" була автоматично відмінена. Причина: {user} покинув чат.'
            )
            await deal.create_log(deal_db, text)
            await cancel_deal_processing(msg.bot, deal, state, userbot, config, fondy, session, message=text)
        else:
            room = await room_db.get_room(deal.chat_id)
            await room_db.update_room(room.chat_id, reason=f'{user} покинув чат')
            text = await room.construct_admin_moderate_text(room_db, msg.bot, config)
            msg = await msg.bot.send_message(config.misc.admin_channel_id, text,
                                             reply_markup=await help_admin_kb(deal.deal_id))
            await room_db.update_room(room.chat_id, message_id=msg.message_id)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        cancel_deal_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='end_deal'), state='*')
    dp.register_callback_query_handler(
        confirm_done_deal_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='done_deal'), state='*')
    dp.register_callback_query_handler(
        confirm_cancel_deal_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='cancel_deal'), state='*')
    dp.register_callback_query_handler(
        handle_confirm_done_deal, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='conf_done_deal'),
        state='conf_done_deal')
    dp.register_callback_query_handler(
        handle_confirm_cancel_deal, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='conf_cancel_deal'),
        state='conf_cancel_deal')
    dp.register_callback_query_handler(
        delete_chat_by_activity, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='delete_activity'),
        state='*'
    )
    dp.register_message_handler(
        left_chat_member_cancel, ChatTypeFilter(ChatType.GROUP), content_types=ContentTypes.LEFT_CHAT_MEMBER, state='*')


async def copy_and_delete_history(userbot: UserbotController, room: RoomRepo.model, deal: DealRepo.model,
                                  customer: UserRepo.model, executor: UserRepo.model, config: Config,
                                  bot: Bot):
    history_start_msg = (
        '==============================\n'
        f'УГОДУ РОЗПОЧАТО В ЧАТІ {room.chat_id}\n'
        f'Замовник: {customer.mention}\n'
        f'Виконавець: {executor.mention}\n'
        f'🆔 #Угода_номер_{deal.deal_id}\n'
        f'=============================='
    )
    history_end_msg = (
        '==============================\n'
        'УГОДУ ЗАВЕРШЕНО\n'
        f'🆔 #Угода_номер_{deal.deal_id}\n'
        f'=============================='
    )
    await bot.send_message(config.misc.history_channel_id, history_start_msg)
    messages = await userbot.get_chat_history(room.chat_id)
    chat_users = [customer.user_id, executor.user_id]
    data = {
        '0': '🔵',
        '1': '🔴',
        '2': '🟠',
        '3': '🟡',
        '4': '🟢',
        '5': '🔵',
        '6': '🟣',
        '7': '🟠',
        '8': '🟢',
        '9': '🟣'
    }
    for message in messages:
        try:
            client = userbot._client
            if not message.media:
                if message.text:
                    sender_name = f'{message.from_user.mention}: ' if message.from_user.id in chat_users else ''
                    text = f'{sender_name}{message.text} ({data[str(deal.deal_id)[-1]]}{deal.deal_id})'
                    await client.send_message(
                        config.misc.history_channel_id, text
                    )
            else:
                await userbot._client.copy_message(config.misc.history_channel_id, room.chat_id, message.id)
        except:
            pass
    await bot.send_message(config.misc.history_channel_id, history_end_msg)
    await userbot.delete_group(room.chat_id)
