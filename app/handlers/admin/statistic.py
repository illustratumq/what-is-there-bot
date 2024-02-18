import random
from datetime import datetime, timedelta

import numpy as np
from aiogram import Dispatcher
from aiogram.types import Message, InputFile
from matplotlib.axes import Axes

from app.database.models.base import TimedBaseModel
from app.database.services.enums import OrderTypeEnum
from app.database.services.repos import UserRepo, OrderRepo, DealRepo
from app.keyboards import Buttons
import matplotlib.pyplot as plt

from app.misc.times import now


def datetime_to_str(time: datetime) -> str:
    return datetime.strftime(time, '%m-%d-%Y')


def sorted_by_time(models: list[TimedBaseModel]):
    models = sorted(models, key=lambda m: m.created_at)
    dates = {}
    dates_list = set()
    for model in models:
        model_create_time = datetime_to_str(model.created_at)
        if model_create_time in dates.keys():
            dates[model_create_time].append(model)
        else:
            dates.update({model_create_time: [model]})
            dates_list.add(model.created_at)
    return dates, sorted(list(dates_list))

def plot(dates: list[datetime], y, name: str, label: str, ax):
    ax.grid(ls='--')
    ax.scatter(dates, y)
    ax.plot(dates, y, label=label)
    ax.fill_between(dates, y, color='#eb6f92', alpha=0.2)
    plt.xticks(rotation=30, ha='right')
    ax.legend()
    path = f'{name}.png'
    plt.savefig(path, dpi=250)
    return path

def user_statistic(users: list[UserRepo.model]):
    users, dates = sorted_by_time(users)
    models_number = []
    days = (now() - dates[0]).days
    dates = [datetime_to_str(dates[0] + timedelta(days=i)) for i in range(0, days + 1)]
    for date in dates:
        models_number.append(len(users[date]) if date in users.keys() else 0)
    fig, ax = plt.subplots(figsize=(10, 6))
    path = plot(dates, models_number, 'users', 'Користувачі', ax)
    text = (
        '👥 <b>Статистика користувачів</b>\n\n'
        f'🗓 {dates[0]} - {dates[-1]}\n'
        f'Всього: {len(users)} (+{sum(models_number)})'
    )
    return path, text

async def finance_statistic(orders: list[OrderRepo.model], deal_db: DealRepo):
    orders, dates = sorted_by_time(orders)
    print(orders)
    days = (now() - dates[0]).days
    dates = [datetime_to_str(dates[0] + timedelta(days=i)) for i in range(0, days + 1)]
    order_to_plot = []
    commission_to_plot = []
    for date in dates:
        order_sum = 0
        commission_sum = 0
        if date in orders.keys():
            for order in orders[date]:
                order: OrderRepo.model
                deal = await deal_db.get_deal(order.deal_id)
                order_sum += order.calculate_payout() / 100
                commission_sum += order.calculate_payout(commission=True) / 100
        order_to_plot.append(order_sum)
        commission_to_plot.append(commission_sum)
    fig, ax = plt.subplots(figsize=(10, 6))
    plot(dates, order_to_plot, 'orders', 'Платежі', ax)
    path = plot(dates, commission_to_plot, 'commission', 'Комісія', ax)
    text = (
        '👥 <b>Статистика фінансів</b>\n\n'
        f'🗓 {dates[0]} - {dates[-1]}\n'
    )
    return path, text




async def test(msg: Message, user_db: UserRepo, order_db: OrderRepo, deal_db: DealRepo):
    with plt.style.context('app/handlers/admin/rose-pine.mplstyle'):
        path1, text1 = user_statistic(await user_db.get_all())
        path2, text2 = await finance_statistic(await order_db.get_orders(OrderTypeEnum.ORDER), deal_db)
    await msg.answer_photo(InputFile(path1), caption=text1)
    await msg.answer_photo(InputFile(path2), caption=text2)



def setup(dp: Dispatcher):
    dp.register_message_handler(test, text=Buttons.admin.statistic, state='*')