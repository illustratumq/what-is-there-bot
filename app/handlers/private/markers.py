from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.repos import MarkerRepo, UserRepo
from app.keyboards.reply.menu import basic_kb, Buttons
from app.states.states import MarkerSG, UserTimeSG


async def markers_cmd(msg: Message, state: FSMContext):
    text = (
        '<b>Як працюють сповіщення?</b>\n\n'
        'Додайте ключові слова в список ваших підписок. Після появи нового поста, '
        'бот шукає збіги у назві із вашими підписками. У разі, якщо такі є, ви отримаєте сповіщення.\n\n'
        f'<b>{Buttons.menu.markers}</b> — налаштування бажаних підписок.\n'
        f'<b>{Buttons.menu.work_times}</b> — вказати робочий час. '
        f'У цей період бот буде надсилати пости повідомленням зі звуком. В решту часу — беззвучно.\n\n'
    )
    reply_markup = basic_kb(([Buttons.menu.markers, Buttons.menu.work_times], [Buttons.menu.back]))
    await msg.answer(text, reply_markup=reply_markup)
    await state.finish()


async def moderate_markers_cmd(msg: Message, marker_db: MarkerRepo):
    text = (
        'Додайте або видаліть підписки використовуючи кнопки нижче\n\n'
    )
    markers = await marker_db.get_markers_user(msg.from_user.id)
    if markers:
        markers_html = ',\n'.join([f'<code>{m.text}</code>' for m in markers])
        text += f' 📚 Ваші підписки:\n\n{markers_html}'
    else:
        text += 'У вас немає підписок :('
    await msg.answer(text, reply_markup=basic_kb(([Buttons.menu.new_marker, Buttons.menu.del_marker],
                                                  [Buttons.menu.to_markers])))


async def save_marker_cmd(msg: Message, marker_db: MarkerRepo, state: FSMContext):
    marker_text = msg.text.lower()
    markers = await marker_db.get_markers_user(msg.from_user.id)
    if len(marker_text) > 20:
        await msg.reply(f'Максимальна довжина 20 літер (замість {len(marker_text)} літер)',
                        reply_markup=basic_kb([Buttons.menu.back]))
    elif len(markers) == 10:
        await msg.answer('Ви досягли максимальної кількості підписок 😐')
        await state.finish()
        await markers_cmd(msg, state)
    elif marker_text in [m.text for m in markers]:
        await msg.answer('Така підписка вже існує')
        await add_marker_cmd(msg)
    else:
        await msg.delete()
        await marker_db.add(user_id=msg.from_user.id, text=marker_text)
        reply_markup = basic_kb(([Buttons.menu.new_marker, Buttons.menu.del_marker],
                                 [Buttons.menu.to_markers]))
        await msg.answer(f'Підписка <code>{marker_text}</code> успішно додана', reply_markup=reply_markup)
        await moderate_markers_cmd(msg, marker_db)
        await state.finish()


async def add_marker_cmd(msg: Message):
    await msg.answer('Надішліть ключове слово, максимальна довжина 20 літер.')
    await MarkerSG.Add.set()


async def input_marker_delete(msg: Message, marker_db: MarkerRepo, state: FSMContext):
    markers = await marker_db.get_markers_user(msg.from_user.id)
    markers = [marker.text for marker in markers]
    if markers:
        reply_markup = basic_kb([markers[i:i+2] for i in range(0, len(markers), 2)] + [[Buttons.menu.to_markers]])
        await msg.answer('Наділшіть підписку, яку хочете видалити',
                         reply_markup=reply_markup)
        await MarkerSG.Delete.set()
    else:
        await msg.answer('У вас немає підписок')
        await markers_cmd(msg, state)

async def delete_marker_cmd(msg: Message, marker_db: MarkerRepo):
    marker_text = msg.text.lower()
    marker = await marker_db.get_marker_text(msg.from_user.id, marker_text)
    if not marker:
        await msg.answer(f'Підписка <code>{marker_text}</code> не знайдена, спробуйте ще раз',
                         reply_markup=basic_kb([Buttons.menu.to_markers]))
    else:
        await msg.delete()
        await marker_db.delete_marker(msg.from_user.id, marker_text)
        markers = await marker_db.get_markers_user(msg.from_user.id)
        markers = [marker.text for marker in markers]
        if markers:
            reply_markup = basic_kb([markers[i:i + 2] for i in range(0, len(markers), 2)] + [[Buttons.menu.to_markers]])
            await msg.answer(f'Підписка <code>{marker_text}</code> успішно видалена', reply_markup=reply_markup)
        else:
            await msg.answer('Ви видалили всі підписки')
            await moderate_markers_cmd(msg, marker_db)

async def set_marker_time(msg: Message, user_db: UserRepo):
    user = await user_db.get_user(msg.from_user.id)
    current_time = user.time if user.time != '*' else 'будь-який'
    await msg.answer(f'Вкажіть час коли вам можна писати в форматі ГГ-ГГ, наприклад 08-18\n'
                     f'\nПоточний час: {current_time}',
                     reply_markup=basic_kb([Buttons.menu.to_markers]))
    await UserTimeSG.Input.set()


async def save_marker_time(msg: Message, user_db: UserRepo, state: FSMContext):
    try:
        start, end = msg.text.split('-')
        if int(end) < int(start):
            await msg.answer('Години мають бути вказані від меншої до більшої, спробуйте ще раз')
            return
        await user_db.update_user(msg.from_user.id, time=f'{int(start)}-{int(end)}')
        await msg.answer('Години успішно збережені')
        await markers_cmd(msg, state)
        await state.finish()
    except:
        await msg.answer('Упс, формат даних некоректний, спробуй ще раз')


def setup(dp: Dispatcher):
    dp.register_message_handler(
        markers_cmd, ChatTypeFilter(ChatType.PRIVATE), text=[Buttons.menu.notifications, Buttons.menu.to_markers],
        state='*')
    dp.register_message_handler(
        moderate_markers_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.markers, state='*')
    dp.register_message_handler(
        add_marker_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.new_marker, state='*')
    dp.register_message_handler(delete_marker_cmd, ChatTypeFilter(ChatType.PRIVATE), state=MarkerSG.Delete)
    dp.register_message_handler(save_marker_cmd, ChatTypeFilter(ChatType.PRIVATE), state=MarkerSG.Add)
    dp.register_message_handler(
        input_marker_delete, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.del_marker, state='*')
    dp.register_message_handler(set_marker_time, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.work_times)
    dp.register_message_handler(save_marker_time, ChatTypeFilter(ChatType.PRIVATE), state=UserTimeSG.Input)
