from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatType, ContentTypes, Message

from app.config import Config
from app.database.services.enums import DealStatusEnum, RoomStatusEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo
from app.handlers.userbot import UserbotController
from app.keyboards import Buttons
from app.keyboards.inline.chat import close_deal_kb, confirm_moderate_kb, evaluate_deal_kb, room_cb
from app.keyboards.inline.post import participate_kb
from app.misc.pirce import PriceList


async def cancel_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo):
    await call.message.delete()
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    text = (
        'Оберіть тип завершення угоди\n\n'
        '<b>Завершити</b> - угода завершується та сплачені кошти нараховуються виконавцю.\n\n'
        '<b>Відмінити</b> - угода відміняється та сплачені кошти повертаються на баланс замовника.'
    )
    await call.message.answer(
        text, reply_markup=close_deal_kb(deal)
    )


async def cancel_action_cmd(call: CallbackQuery, deal_db: DealRepo, state: FSMContext):
    await call.message.delete()
    deal = await deal_db.get_deal_chat(call.message.chat.id)
    await state.storage.reset_data(chat=call.message.chat.id, user=deal.customer_id)
    await state.storage.reset_data(chat=call.message.chat.id, user=deal.executor_id)
    await call.message.answer('Дія була відмінена')


async def confirm_done_deal_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                state: FSMContext):
    await call.answer()
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    text = (
        f'Щоб <u>Завершити</u> угоду, {executor.create_html_link("Виконавець")} та '
        f'{customer.create_html_link("Замовник")} повинні підтвердити своє рішення. Для '
        f'цього обидва користувачі мають натиснути кнопку "{Buttons.chat.confirm}", після цього чат буде видалено.\n\n'
        f'Будь ласка, не забудьте зберігти матеріали угоди надіслані Виконавцем.'

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
        f'Щоб <u>Відмінити</u> угоду, {executor.create_html_link("Виконавець")} та '
        f'{customer.create_html_link("Замовник")} повинні підтвердити своє рішення. Для '
        f'цього обидва користувачі мають натиснути кнопку "{Buttons.chat.confirm}", після цього чат буде видалено.\n\n'
        f'Будь ласка, не забудьте зберігти матеріали угоди надіслані Виконавцем.'

    )
    await call.message.edit_text(text=text, reply_markup=confirm_moderate_kb(deal, 'cancel_deal'))
    await state.storage.set_state(chat=call.message.chat.id, user=deal.customer_id, state='conf_cancel_deal')
    await state.storage.set_state(chat=call.message.chat.id, user=deal.executor_id, state='conf_cancel_deal')
    await state.storage.update_data(chat=call.message.chat.id, user=deal.executor_id, voted=False)
    await state.storage.update_data(chat=call.message.chat.id, user=deal.customer_id, voted=False)


async def cancel_deal_processing(bot: Bot, deal: DealRepo.model, post: PostRepo.model,
                                 customer: UserRepo.model, state: FSMContext, deal_db: DealRepo, post_db: PostRepo,
                                 user_db: UserRepo, room_db: RoomRepo, userbot: UserbotController, config: Config,
                                 message: str = None, reset_state: bool = True):
    if deal.payed > 0:
        back_to_customer = deal.payed
        commission = PriceList.calculate_commission(deal.payed)
        customer_balance = customer.balance + back_to_customer + commission
        await user_db.update_user(customer.user_id, balance=customer_balance)
        text = (
            f'На ваш рахунок повернено {back_to_customer + commission} грн.'
        )
        await bot.send_message(deal.customer_id, text)
    await post_db.update_post(post.post_id, status=DealStatusEnum.ACTIVE)
    if post.message_id:
        await bot.delete_message(config.misc.post_channel_chat_id, post.message_id)
        post_channel = await bot.send_message(
            config.misc.post_channel_chat_id, post.construct_post_text(),
            reply_markup=participate_kb(await post.construct_participate_link()),
            disable_web_page_preview=True if not post.message_id else False
        )
        await post_db.update_post(post.post_id, message_id=post_channel.message_id, post_url=post_channel.url)
    await bot.delete_message(config.misc.reserv_channel_id, post.reserv_message_id)
    reserv_channel = await bot.send_message(
        config.misc.reserv_channel_id, post.construct_post_text(),
        reply_markup=participate_kb(await post.construct_participate_link()),
        disable_web_page_preview=True if not post.message_id else False
    )
    await post_db.update_post(post.post_id, reserv_message_id=reserv_channel.message_id)
    default_text = f'Угода "{post.title}" була відмінена.'
    for user_id in deal.participants:
        text = default_text if not message else message
        await bot.send_message(user_id, text)
    await room_db.update_room(deal.chat_id, status=RoomStatusEnum.AVAILABLE)
    if reset_state:
        await state.storage.reset_data(chat=deal.chat_id, user=deal.customer_id)
        await state.storage.reset_data(chat=deal.chat_id, user=deal.executor_id)
    # await userbot.clean_chat_history(chat_id=deal.chat_id)
    try:
        for user_id in deal.participants:
            await bot.kick_chat_member(deal.chat_id, user_id=user_id)
    except:
        pass
    await deal_db.update_deal(deal.deal_id, status=DealStatusEnum.ACTIVE, price=post.price,
                              payed=0, chat_id=None, executor_id=None)


async def done_deal_processing(call: CallbackQuery, deal: DealRepo.model, post: PostRepo.model, customer: UserRepo.model,
                               executor: UserRepo.model,  state: FSMContext, deal_db: DealRepo, post_db: PostRepo,
                               user_db: UserRepo, room_db: RoomRepo, userbot: UserbotController, config: Config):
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
        commission = PriceList.calculate_commission(deal.price)
        balance = executor.balance + deal.price - commission
        await user_db.update_user(executor.user_id, balance=balance)
        text = (
            f'На ваш рахунок зараховано {deal.price-commission} грн. Комісія становить {commission} грн. '
            f'Ви можете вивести ці кошти на банківську карту, або використати для оплати іншої угоди.\n\n'
            f'Дякуємо за використання нашого сервісу.'
        )
        await call.bot.send_message(deal.executor_id, text)
        if deal.payed > deal.price:
            back_to_customer = deal.payed - deal.price
            customer_balance = customer.balance + back_to_customer
            await user_db.update_user(customer.user_id, balance=customer_balance)
            text = (
                f'На ваш рахунок повернено {back_to_customer} грн.'
            )
            await call.bot.send_message(deal.customer_id, text)
        text = (
            f'Угода "{post.title}" була завершена. Оцініть роботу виконавця від 1 до 5.'
        )
        await call.bot.send_message(deal.customer_id, text, reply_markup=evaluate_deal_kb(deal))
        await deal_db.update_deal(deal.deal_id, status=DealStatusEnum.DONE, chat_id=None)
        await post_db.update_post(post.post_id, status=DealStatusEnum.DONE)
        await call.bot.edit_message_text(
            post.construct_post_text(), config.misc.reserv_channel_id, post.reserv_message_id
        )
        if post.message_id:
            await call.bot.edit_message_text(
                post.construct_post_text(), config.misc.post_channel_chat_id, post.message_id
            )
        await room_db.update_room(call.message.chat.id, status=RoomStatusEnum.AVAILABLE)
        await state.storage.reset_data(chat=call.message.chat.id, user=deal.customer_id)
        await state.storage.reset_data(chat=call.message.chat.id, user=deal.executor_id)
        # await userbot.clean_chat_history(chat_id=call.message.chat.id)
        try:
            for user_id in deal.participants:
                await call.message.chat.kick(user_id=user_id)
        except:
            pass


async def handle_confirm_done_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                   post_db: PostRepo, state: FSMContext, room_db: RoomRepo, userbot: UserbotController,
                                   config: Config):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    await state.storage.update_data(chat=call.message.chat.id, user=call.from_user.id, voted=True)
    customer_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.customer_id)
    executor_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.executor_id)
    if customer_data['voted'] and executor_data['voted']:
        post = await post_db.get_post(deal.post_id)
        await done_deal_processing(call, deal, post, customer, executor, state, deal_db, post_db, user_db, room_db,
                                   userbot, config)
    else:
        user = customer if call.from_user.id == executor.user_id else executor
        await call.message.reply(f'Ваш голос зараховано!\nОчікуємо на голос {user.mention}.')


async def handle_confirm_cancel_deal(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, user_db: UserRepo,
                                     post_db: PostRepo, state: FSMContext, room_db: RoomRepo, userbot: UserbotController,
                                     config: Config):
    deal_id = int(callback_data['deal_id'])
    deal = await deal_db.get_deal(deal_id)
    customer = await user_db.get_user(deal.customer_id)
    executor = await user_db.get_user(deal.executor_id)
    await state.storage.update_data(chat=call.message.chat.id, user=call.from_user.id, voted=True)
    customer_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.customer_id)
    executor_data = await state.storage.get_data(chat=call.message.chat.id, user=deal.executor_id)
    if customer_data['voted'] and executor_data['voted']:
        post = await post_db.get_post(deal.post_id)
        await call.message.delete_reply_markup()
        await cancel_deal_processing(call.bot, deal, post, customer, state, deal_db, post_db, user_db, room_db,
                                     userbot, config)
    else:
        user = customer if call.from_user.id == executor.user_id else executor
        await call.message.reply(f'Ваш голос зараховано!\nОчікуємо на голос {user.mention}.')


async def left_chat_member_cancel(msg: Message, deal_db: DealRepo, user_db: UserRepo,
                                  post_db: PostRepo, state: FSMContext, room_db: RoomRepo, userbot: UserbotController,
                                  config: Config):
    deal = await deal_db.get_deal_chat(msg.chat.id)
    customer = await user_db.get_user(deal.customer_id)
    post = await post_db.get_post(deal.post_id)
    user = 'Замовник' if msg.from_user.id == customer.user_id else 'Виконавець'
    text = (
        f'Угода "{post.title}" була автоматично відмінена. Причина: {user} покинув чат.'
    )
    await cancel_deal_processing(msg.bot, deal, post, customer, state, deal_db, post_db, user_db, room_db,
                                 userbot, config, message=text)


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
    dp.register_message_handler(
        left_chat_member_cancel, ChatTypeFilter(ChatType.GROUP), content_types=ContentTypes.LEFT_CHAT_MEMBER, state='*')
    dp.register_callback_query_handler(
        cancel_action_cmd, ChatTypeFilter(ChatType.GROUP), room_cb.filter(action='back'), state='*')


