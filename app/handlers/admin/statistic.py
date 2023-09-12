import os
import random
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, InputFile
from matplotlib.axes import Axes
from scipy import interpolate

from app.database.models.base import TimedBaseModel
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo
from app.keyboards import Buttons
from app.keyboards.reply.menu import basic_kb
from app.misc.times import localize, now


async def admin_statistic_cmd_old(msg: Message, deal_db: DealRepo, post_db: PostRepo, user_db: UserRepo, state: FSMContext):
    msg = await msg.answer('Збираю статистику...')
    deals = await deal_db.get_deal_status(DealStatusEnum.DONE)
    users = await user_db.get_all()
    posts = await post_db.get_all()
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
    plt.rcParams.update({'font.size': 16})
    fig = plt.figure(figsize=(15, 25), dpi=250)
    ax1 = plt.subplot2grid((3, 10), (0, 0), colspan=6)
    ax2 = plt.subplot2grid((3, 10), (0, 7), colspan=3)
    ax3 = plt.subplot2grid((3, 10), (1, 0), colspan=10)
    ax4 = plt.subplot2grid((3, 10), (2, 0), colspan=10)

    data = await state.get_data()
    if 'dates' in data.keys():
        dates = (
            now().strptime(data['dates'].split('-')[0].strip(), '%d.%m.%y'),
            now().strptime(data['dates'].split('-')[1].strip(), '%d.%m.%y')
        )
    else:
        dates = (now() - timedelta(days=7), now())

    await msg.bot.send_chat_action(msg.from_user.id, 'upload_photo')
    commissions_sum, price_sum = await admin_statistic_finance([ax1, ax2], deals, dates)
    posts_sum, deals_sum = await admin_statistic_posts(ax3, posts, deals, dates)
    user_sum = await admin_statistic_users(ax4, users, dates)
    text = (
        f'[{Buttons.admin.statistic}]\n\n'
        f'<b>За період {dates[0].strftime("%d.%m.%y")} - {dates[-1].strftime("%d.%m.%y")}</b>\n\n'
        f'Всього користувачів: {user_sum}\n\n'
        f'Всього постів: {posts_sum}\n'
        f'Виконаних угод: {deals_sum}\n\n'
        f'Загальна комісія: {commissions_sum} грн.\n'
        f'Загальний оборот: {price_sum} грн.'
    )
    plt.savefig('app/data/stat.png', dpi=250)
    await msg.delete()
    await msg.answer_photo(InputFile('app/data/stat.png'), caption=text,
                           reply_markup=basic_kb([[Buttons.admin.dates], [Buttons.admin.to_admin]]))
    os.remove('app/data/stat.png')


async def input_statistic_dates(msg: Message, state: FSMContext):
    text = (
        'Введіть початок та кінець періоду, за який хочете подивитись статистику, в форматі '
        'dd.mm.yy - dd.mm.yy (Наприклад 01.01.23 - 07.01.23)'
    )
    await state.set_state(state='dates')
    await msg.answer(text, reply_markup=basic_kb([Buttons.admin.to_admin]))


async def save_statistic_states(msg: Message, deal_db: DealRepo, post_db: PostRepo, user_db: UserRepo,
                                state: FSMContext):
    dates = msg.text
    try:
        dates = (
            now().strptime(dates.split('-')[0].strip(), '%d.%m.%y'),
            now().strptime(dates.split('-')[1].strip(), '%d.%m.%y')
        )
        await state.update_data(dates=msg.text)
        # await admin_statistic_cmd(msg, deal_db, post_db, user_db, state)
    except:
        await msg.answer('Щось пішло не так, спробуйте ще раз')


def setup(dp: Dispatcher):
    # dp.register_message_handler(admin_statistic_cmd, text=Buttons.admin.statistic, state='*')
    dp.register_message_handler(input_statistic_dates, text=Buttons.admin.dates, state='*')
    dp.register_message_handler(save_statistic_states, state='dates')


async def admin_statistic_users(ax: Axes, users: list[UserRepo.model], dates: tuple[datetime, datetime]):
    users = select_models_date(models=users, dates=dates)
    users_sum, x_ticks_date = [], []
    for day in range((dates[-1] - dates[0]).days):
        day = dates[0] + timedelta(days=day)
        user_day = sum([1 for user in users if is_created_at.date(user, day)])
        users_sum.append(user_day)
        x_ticks_date.append(day.strftime('%d.%m.%y'))
    x_ticks_date_range = np.arange(len(x_ticks_date))
    f = interpolate.interp1d(x_ticks_date_range, users_sum, kind='quadratic')
    x_new = np.linspace(x_ticks_date_range[0], x_ticks_date_range[-1], 1000)
    y_new = f(x_new)
    ax.fill_between(x_new, y_new, color='#ea4cbd', interpolate=True, alpha=0.3)
    ax.scatter(x_ticks_date, users_sum, color='#ea4cbd', lw=6)
    ax.plot(x_new, y_new, color='#ea4cbd', lw=5)

    ax.grid()
    ax.set_ylabel('Нові користувачі', fontweight='bold')
    step = 4 if len(x_ticks_date_range) > 7 else 1
    ax.set_xticks(x_ticks_date_range[::step], x_ticks_date[::step], rotation=50)
    return sum(users_sum)


async def admin_statistic_posts(ax: Axes, posts: list[PostRepo.model], deals: list[PostRepo.model],
                                dates: tuple[datetime, datetime]):
    posts = select_models_date(models=posts, dates=dates)
    deals = select_models_date(models=deals, dates=dates)
    posts_sum, deals_sum, x_ticks_date = [], [], []
    for day in range((dates[-1] - dates[0]).days):
        day = dates[0] + timedelta(days=day)
        posts_day = sum([1 for post in posts if is_created_at.date(post, day)])
        deals_day = sum([1 for deal in deals if is_created_at.date(deal, day)])
        posts_sum.append(posts_day)
        deals_sum.append(deals_day)
        x_ticks_date.append(day.strftime('%d.%m.%y'))
    x_ticks_date_range = np.arange(len(x_ticks_date))
    # posts_sum = [random.randint(1, 100) for i in range(len(x_ticks_date))]
    # deals_sum = [random.randint(3, 70) for i in range(len(x_ticks_date))]

    f = interpolate.interp1d(x_ticks_date_range, posts_sum, kind='quadratic')
    x_new = np.linspace(x_ticks_date_range[0], x_ticks_date_range[-1], 1000)
    y_new = f(x_new)
    ax.fill_between(x_new, y_new, color='#FFB516', interpolate=True, alpha=0.3)
    ax.scatter(x_ticks_date, posts_sum, color='#FFB516', lw=6)
    ax.plot(x_new, y_new, color='#FFB516', lw=5, label='Пости')

    f = interpolate.interp1d(x_ticks_date_range, deals_sum, kind='quadratic')
    x_new = np.linspace(x_ticks_date_range[0], x_ticks_date_range[-1], 1000)
    y_new = f(x_new)
    ax.fill_between(x_new, y_new, color='#675fce', interpolate=True, alpha=0.3)
    ax.scatter(x_ticks_date, deals_sum, color='#675fce', lw=6)
    ax.plot(x_new, y_new, color='#675fce', lw=5, label='Завершені угоди')

    ax.grid()
    ax.legend()
    ax.set_ylabel('Пости та угоди', fontweight='bold')
    step = 4 if len(x_ticks_date_range) > 7 else 1
    ax.set_xticks(x_ticks_date_range[::step], x_ticks_date[::step], rotation=50)
    return sum(posts_sum), sum(deals_sum)


async def admin_statistic_finance(axes: [Axes, Axes], deals: list[DealRepo.model], dates: tuple[datetime, datetime]):
    deals = select_models_date(models=deals, dates=dates, created=False)
    commission_sum, price_sum, x_ticks_date = [], [], []
    for day in range((dates[-1] - dates[0]).days):
        day = dates[0] + timedelta(days=day)
        commission = sum([deal.commission for deal in deals if is_created_at.date(deal, day, created_at=False)])
        price = sum([deal.price for deal in deals if is_created_at.date(deal, day, created_at=False)])
        x_ticks_date.append(day.strftime('%d.%m.%y'))
        commission_sum.append(commission)
        price_sum.append(price)
    x_ticks_date_range = np.arange(len(x_ticks_date))
    # commission_sum = [random.randint(5, 500) for i in range(len(x_ticks_date))]
    # price_sum = [random.randint(30, 1000) for i in range(len(x_ticks_date))]
    axes[0].bar(x_ticks_date_range, commission_sum, width=0.25, color='#2CEA75', edgecolor='black', linewidth=1.2,
                zorder=2, label='Комісія')
    axes[0].bar(x_ticks_date_range + 0.25, price_sum, width=0.25, color='#2E79EA', edgecolor='black', linewidth=1.2,
                zorder=2, label='Загальний обороот')
    if len(x_ticks_date_range) <= 7:
        for c in commission_sum:
            if c != 0:
                axes[0].text(x_ticks_date_range[commission_sum.index(c)] + .05, c + 20, c,
                             rotation=90, rotation_mode='anchor', fontsize=14)
        for p in price_sum:
            if p != 0:
                axes[0].text(x_ticks_date_range[price_sum.index(p)] + .25 + .05, p + 20, p,
                             rotation=90, rotation_mode='anchor', fontsize=14)
    axes[0].grid(ls='--', zorder=1)
    step = 4 if len(x_ticks_date_range) > 7 else 1
    axes[0].legend()
    axes[0].set_xticks(x_ticks_date_range[::step], x_ticks_date[::step], rotation=50)
    axes[0].set_ylim(0, max(price_sum) * 1.2)
    axes[0].set_ylabel('Фінанси', fontweight='bold')
    if sum(commission_sum) > 0 and sum(price_sum) > 0:
        axes[1].pie([sum(commission_sum), sum(price_sum)],
                    labels=(f'Комісія\n{sum(commission_sum)}, грн', f'Загальний оборот\n{sum(price_sum)}, грн'),
                    colors=['#2CEA75', '#2E79EA'], wedgeprops=dict(width=0.3, edgecolor='k'),
                    startangle=80)
    return sum(commission_sum), sum(price_sum)

def select_models_date(models: list[TimedBaseModel], dates: tuple[datetime, datetime], created: bool = True) -> list:
    models.sort(key=lambda m: m.created_at if created else m.updated_at)
    models_date = []
    for model in models:
        chek_date = model.created_at if created else model.updated_at
        if localize(dates[0]) <= localize(chek_date) <= localize(dates[-1]):
            models_date.append(model)
    return models_date


class is_created_at:

    @staticmethod
    def date(model: TimedBaseModel, date: [datetime], created_at: bool = True, **kwargs) -> bool:
        kwargs = kwargs if kwargs else dict(days=1)
        model_time = model.created_at if created_at else model.updated_at
        return date <= localize(model_time) <= date + timedelta(**kwargs)