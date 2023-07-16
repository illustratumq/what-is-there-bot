import json
import os
import shutil
from datetime import datetime

import pandas as pd
from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter, Command
from aiogram.types import Message, InputFile, ChatType

from app.database.services.enums import *
from app.database.services.repos import UserRepo, DealRepo, PostRepo, RoomRepo, CommissionRepo, MarkerRepo, SettingRepo
from app.misc.times import now


async def save_database(user_db: UserRepo, deal_db: DealRepo, post_db: PostRepo,
                        room_db: RoomRepo):

    users = await user_db.get_all()
    deals = await deal_db.get_all()
    posts = await post_db.get_all()
    rooms = await room_db.get_all()

    users_data, deals_data, posts_data, rooms_data = {}, {}, {}, {}

    for selection, selection_data in zip([users, deals, posts, rooms], [users_data, deals_data, posts_data, rooms_data]):

        selection_data.update({
            'created_at': [], 'updated_at': []
        })

        if selection:
            keys_data = selection[0].__dict__
        else:
            keys_data = {}
        keys = list(keys_data.keys())
        keys.sort()
        for key in keys:
            if key not in ('_sa_instance_state', 'created_at', 'updated_at'):
                selection_data.update({key: []})

        for obj in selection:
            obj_data = obj.__dict__
            obj_data.update({'created_at': obj.created_at.strftime('%d.%m.%y %H:%M:%S')})
            obj_data.update({'updated_at': obj.updated_at.strftime('%d.%m.%y %H:%M:%S')})
            for key in obj_data:
                if key != '_sa_instance_state':
                    selection_data[key].append(obj_data[key])

    path = f'app/data/database{now().strftime("_%d_%m_%y")}.xlsx'

    with pd.ExcelWriter(path, engine='openpyxl') as writer:

        selection_data_names = ['Користувачі', 'Угоди', 'Пости', 'Кімнати']

        for selection_data, i in zip([users_data, deals_data, posts_data, rooms_data], range(len(selection_data_names))):
            pd.DataFrame(selection_data).to_excel(writer, sheet_name=selection_data_names[i])

    return path


async def save_database_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo, post_db: PostRepo,
                            room_db: RoomRepo, commission_db: CommissionRepo, marker_db: MarkerRepo,
                            setting_db: SettingRepo):
    # path = await save_database(user_db, deal_db, post_db, room_db)
    path = await save_database_json(user_db, deal_db, post_db, room_db, commission_db,
                                    marker_db, setting_db)
    await msg.answer_document(InputFile(path))
    os.remove(path)

async def save_database_json(user_db: UserRepo, deal_db: DealRepo, post_db: PostRepo,
                             room_db: RoomRepo, commission_db: CommissionRepo, marker_db: MarkerRepo,
                             setting_db: SettingRepo):
    names = ['users', 'deals', 'posts', 'rooms', 'commissions', 'markers', 'settings']
    repos = [user_db, deal_db, post_db, room_db, commission_db, marker_db, setting_db]

    if not os.path.exists('app/database/archive'):
        os.mkdir('app/database/archive')

    enums = [UserStatusEnum, UserTypeEnum, PostStatusText,  RoomStatusEnum, DealStatusEnum, DealTypeEnum]

    for repo, name in zip(repos, names):
        repo_data = {'models': []}
        models = await repo.get_all()
        if models:
            keys = models[0]._get_attributes()
            for model in models:
                model_data = {}
                for key in keys:
                    if type(model.__dict__[key]) in enums:
                        model_data.update({key: str(model.__dict__[key])})
                    elif isinstance(model.__dict__[key], datetime):
                        model_data.update({key: model.__dict__[key].strftime('%d.%m.%y %H:%M:%S')})
                    else:
                        model_data.update({key: model.__dict__[key]})
                repo_data['models'].append(model_data)
        with open('app/database/archive/' + name + '_database.json', mode='w', encoding='utf-8') as file:
            json.dump(repo_data, file, indent=4)
    archive = shutil.make_archive('app/database/database', 'zip', 'app/database/archive')
    shutil.rmtree('app/database/archive')
    return archive

def setup(dp: Dispatcher):
    dp.register_message_handler(save_database_cmd, ChatTypeFilter(ChatType.PRIVATE), Command('database'), state='*')