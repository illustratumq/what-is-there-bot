from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InputFile
from matplotlib.axes import Axes

from app.database.models.base import TimedBaseModel
from app.database.services.enums import UserStatusEnum, OrderTypeEnum
from app.database.services.repos import UserRepo, OrderRepo, DealRepo
from app.keyboards import Buttons
from app.keyboards.inline.statistic import menu_statistic_kb, statistic_mini_bar, statistic_cb, go_to_bar
from app.misc.times import now


PATH_TO_SAVE = 'app/handlers/admin/statistic_files/{}'
PATH_TO_STYLE = 'app/handlers/admin/statistic_files/rose-pine.mplstyle'

def datetime_to_str(time: datetime, splitter: str = '.') -> str:
    return datetime.strftime(time, f'%d{splitter}%m{splitter}%Y')

def str_to_datetime(time: str, splitter: str = '.') -> datetime:
    return datetime.strptime(time, f'%d{splitter}%m{splitter}%Y')

def replace_time_null(time: datetime) -> datetime:
    return time.replace(hour=0, minute=0, second=0, microsecond=0)

def generate_time_range(dates: list[str, str]):
    start = replace_time_null(str_to_datetime(dates[0]))
    end = replace_time_null(str_to_datetime(dates[1]))
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def sorted_by_time(models: list[TimedBaseModel]):
    models = sorted(models, key=lambda m: m.created_at)
    models_by_time = {}
    for model in models:
        model_create_time = datetime_to_str(model.created_at)
        if model_create_time in models_by_time.keys():
            models_by_time[model_create_time].append(model)
        else:
            models_by_time.update({model_create_time: [model]})
    return models_by_time


def select_by_time(models_by_time: dict, dates: list[str, str]) -> dict:
    selected_models = {}
    for selected_time in generate_time_range(dates):
        time_str = datetime_to_str(selected_time)
        if time_str in models_by_time.keys():
            selected_models.update({time_str: models_by_time[time_str]})
        else:
            selected_models.update({time_str: []})
    return selected_models


async def statistic_cmd(msg: Message):
    await msg.answer(
        'Оберіть який розділ статистики бажаєте переглянути',
        reply_markup=menu_statistic_kb()
    )

async def choose_dates_cmd(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await state.update_data(bar=callback_data['bar'])
    await call.message.answer('Введіть час за який хочете подивитись статистику в форматі:\n\n'
                              'початок - кінець (ДД.ММ.РРРР)')
    await state.set_state(state='time_choose')


async def input_time_cmd(msg: Message, state: FSMContext):
    try:
        time = msg.text.split('-')
        start = time[0].strip()
        end = time[1].strip()
        if str_to_datetime(start, ) and str_to_datetime(end, ):
            data = await state.get_data()
            await msg.answer(f'Порахувати статистику для {msg.text}',
                             reply_markup=go_to_bar(msg.text))
            await state.finish()
    except:
        await msg.answer('Некоректно введені дані, спробуйте ще раз')

async def user_bar_cmd(call: CallbackQuery, callback_data: dict, user_db: UserRepo):
    if callback_data['param'] != '':
        times = callback_data['param'].split('-')
    else:
        times = (datetime_to_str(now().replace(day=1)), datetime_to_str(now()))
    all_users = await user_db.get_all()
    banned_users = await user_db.get_users_status(UserStatusEnum.BANNED)
    dates, users = calculate_len_to_plot(select_by_time(sorted_by_time(all_users), times))
    await call.message.delete()
    text = (
        f'<b>{Buttons.admin.statistic_menu.users}</b>\n'
        f'📅 {times[0]} - {times[1]}\n\n'
        f'Всього користувачів: {len(all_users)} (+{sum(users)} за цей період)\n'
        f'Забанено користувачів: {len(banned_users)}'
    )
    await call.message.answer_photo(
        InputFile(plot(dates, users)), caption=text, reply_markup=statistic_mini_bar(callback_data['bar'],
                                                                                     callback_data['param'])
    )

async def finance_bar_cmd(call: CallbackQuery, callback_data: dict, order_db: OrderRepo, deal_db: DealRepo):
    if callback_data['param'] != '':
        times = callback_data['param'].split('-')
    else:
        times = (datetime_to_str(now().replace(day=1)), datetime_to_str(now()))
    all_orders = await order_db.get_all()
    orders_pay = await order_db.get_orders(OrderTypeEnum.ORDER)
    orders_payout = await order_db.get_orders(OrderTypeEnum.PAYOUT)
    dates, orders_price, orders_commission = calculate_orders_to_plot(select_by_time(sorted_by_time(all_orders), times))
    await call.message.delete()
    text = (
        f'<b>{Buttons.admin.statistic_menu.finance}</b>\n'
        f'📅 {times[0]} - {times[1]}\n\n'
        f'Всього транзакцій: {len(all_orders)}\n'
        f'З них на оплату: {len(orders_pay)}\n'
        f'З них на виплату: {len(orders_payout)}\n\n'
        f'Всього сплачено: {round(sum(orders_price), 2)} грн.\n'
        f'Всього отримано: {round(sum(orders_commission), 2)} грн.'
    )
    await call.message.answer_photo(
        InputFile(plot_bar(dates, orders_price, orders_commission)),
        caption=text, reply_markup=statistic_mini_bar(callback_data['bar'], callback_data['param'])
    )


def setup(dp: Dispatcher):
    dp.register_message_handler(statistic_cmd, text=Buttons.admin.statistic, state='*')
    dp.register_callback_query_handler(user_bar_cmd, statistic_cb.filter(action='switch_to', bar='users'),
                                       state='*')
    dp.register_callback_query_handler(finance_bar_cmd, statistic_cb.filter(action='switch_to', bar='finance'),
                                       state='*')
    dp.register_callback_query_handler(choose_dates_cmd, statistic_cb.filter(action='date', param='input'),
                                       state='*')
    dp.register_message_handler(input_time_cmd, state='time_choose')

def plot(dates: list, models: list, **kwargs) -> str:
    with plt.style.context(PATH_TO_STYLE):
        fig, ax = plt.subplots(figsize = (10, 6))
        ax: Axes
        ax.plot(dates, models)
        ax.scatter(dates, models, edgecolors='#eb6f92', color='yellow', alpha=0.8)
        ax.fill_between(dates, models, color='#eb6f92', alpha=0.1)
        ax.set_xticks(over(dates, 10))
        ax.set(**kwargs)
        plt.xticks(rotation=30, ha='right')
        path = PATH_TO_SAVE.format('users.png')
        plt.savefig(path, dpi=350)
        return path


def plot_bar(dates: list, order_price: list, order_commission, **kwargs):
    with plt.style.context(PATH_TO_STYLE):
        fig, ax = plt.subplots(figsize = (10, 6))
        ax: Axes
        x = np.arange(len(dates))
        bar_width = 0.4
        ax.bar(x, order_price, bar_width, label='Ціна угоди')
        ax.bar(x + bar_width, order_commission, bar_width, label='Комісія сервісу')
        ax.set_xticklabels(over(dates, 10))
        ax.set(**kwargs)
        plt.xticks(rotation=30, ha='right')
        ax.legend()
        path = PATH_TO_SAVE.format('finance.png')
        plt.savefig(path, dpi=350)
        return path

def over(lst: list, n: int):
    size = len(lst)
    if size / n > size // n:
        n = size // n + 1
    else:
        n = size // n
    new_lst = [lst[0]]
    for i in range(len(lst)):
        if (i + 1) % n == 0:
            new_lst.append(lst[i])
    return new_lst

def calculate_len_to_plot(models: dict) -> tuple[list, list]:
    dates = []
    models_calculated = []
    for key in models.keys():
        dates.append(key)
        models_calculated.append(len(models[key]))
    return dates, models_calculated


def calculate_orders_to_plot(orders: dict):
    dates = []
    order_price = []
    order_commission = []
    for key in orders.keys():
        dates.append(key)
        order: OrderRepo.model
        order_price.append(sum([order.calculate_payout() / 100 for order in orders[key]]))
        order_commission.append(sum([order.calculate_payout(True) / 100 for order in orders[key]]))
    return dates, order_price, order_commission