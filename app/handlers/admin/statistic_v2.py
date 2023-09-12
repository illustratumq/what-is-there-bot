from datetime import timedelta, datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery

from app.database.services.repos import PostRepo
from app.keyboards import Buttons
from app.keyboards.inline.statistic import menu_statistic_kb, statistic_navigate_kb, statistic_cb, statistic_date_kb
from app.misc.times import now, deltatime


async def admin_statistic_cmd(msg: Message):
    text = (
        'Оберіть який розідл статистики бажаєте переглянути'
    )
    await msg.answer(text, reply_markup=menu_statistic_kb())

async def statistic_date_choose(call: CallbackQuery, callback_data: dict, state: FSMContext):
    if callback_data['date'] == 'custom':
        text = (
            f'[{Buttons.admin.statistic}| {Buttons.admin.statistic_menu.date}]\n\n'
            'Введіть дату або період самостійно:\n\n'
            '1) Введіть дату в форматі ДД.ММ.РР (пошук від цією дати до сьогодні)\n'
            '2) Введіть період в форматі ДД.ММ.РР-ДД.ММ.РР (пошук від першої дати до другої)'
        )
        await call.message.edit_text(text, reply_markup=statistic_date_kb('posts', 'today',
                                                                          only_back=True))
        await state.set_state(state='input_date')
        return
    date = deltatime(callback_data['date'])
    if isinstance(date, datetime):
        date_text = date.strftime('%d.%m.%y')
    else:
        date_text = date[0].strftime('%d.%m.%y') + '-' + date[-1].strftime('%d.%m.%y')
    text = (
        f'[{Buttons.admin.statistic}| {Buttons.admin.statistic_menu.date}]\n\n'
        f'Обрана дата: {date_text}\n\n'
        f'Щоб змінити дату, використовуйте кнопки навігації'
    )
    await call.message.edit_text(text, reply_markup=statistic_date_kb(callback_data['back'], callback_data['date']))

# async def statistic_input_date(msg: Message):

async def posts_statistic(call: CallbackQuery, callback_data: dict, post_db: PostRepo):
    date = callback_data['date']

    # count posts created chosen date

    new_posts_date = await post_db.count_posts(date)
    active_posts_date = await post_db.count_posts(date, 'active')
    busy_posts_date = await post_db.count_posts(date, 'busy')
    disable_posts_date = await post_db.count_posts(date, 'disable')
    moderate_posts_date = await post_db.count_posts(date, 'moderate')
    done_posts_date = await post_db.count_posts(date, 'done')

    # count posts all

    new_posts = await post_db.count_posts('all')
    active_posts = await post_db.count_posts('all', 'active')
    busy_posts = await post_db.count_posts('all', 'busy')
    disable_posts = await post_db.count_posts('all', 'disable')
    moderate_posts = await post_db.count_posts('all', 'moderate')
    done_posts = await post_db.count_posts('all', 'done')

    text = (
        f'[{Buttons.admin.statistic}| {Buttons.admin.statistic_menu.posts}]\n\n'
        f'<b>За обраний період</b> з\'явилось {new_posts_date} постів:\n'
        f'З них є активними - {active_posts_date}\n'
        f'Завершені - {done_posts_date}\n'
        f'В незавершеній угоді - {busy_posts_date}\n'
        f'Відхилені адміном - {disable_posts_date}\n'
        f'Очікуть схвалення публікації - {moderate_posts_date}\n\n'
        f'<b>За весь час</b> створено {new_posts} постів:\n'
        f'З них є активними - {active_posts}\n'
        f'Завершені - {done_posts}\n'
        f'В незавершеній угоді - {busy_posts}\n'
        f'Відхилені адміном - {disable_posts}\n'
        f'Очікуть схвалення публікації - {moderate_posts}\n'
    )
    text += f'\nОстаннє оновлення: {now().strftime("%H:%M:%S")}'
    await call.message.edit_text(text, reply_markup=statistic_navigate_kb('posts', date))

def setup(dp: Dispatcher):
    dp.register_message_handler(admin_statistic_cmd, text=Buttons.admin.statistic, state='*')
    dp.register_callback_query_handler(statistic_date_choose, statistic_cb.filter(action='date'), state='*')
    dp.register_callback_query_handler(posts_statistic, statistic_cb.filter(action='posts'), state='*')
