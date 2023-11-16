from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType, CallbackQuery

from app.config import Config
from app.database.services.repos import CommissionRepo, UserRepo, AdminSettingRepo
from app.filters import IsAdminFilter
from app.keyboards.inline.admin import admin_setting_kb, admin_setting_cb
from app.keyboards.reply.admin import admin_kb, Buttons, construct_packs_kb, keyboard_constructor, edit_commission_kb
from app.states.states import CommissionAdminSG

filters = (
    IsAdminFilter(), ChatTypeFilter(ChatType.PRIVATE)
)


async def admin_cmd(msg: Message, state: FSMContext, config: Config):
    await state.finish()
    text = (
        'Ви перейшли в адмін панель\n\n'
        f'Веб адмінка: {config.django.base_link}\n'
        f'Логін: <code>{config.django.login}</code>\n'
        f'Пароль: <code>{config.django.password}</code>'
    )
    await msg.answer(text, reply_markup=admin_kb())

async def setting_cmd(upd: Message | CallbackQuery, admin_setting_db: AdminSettingRepo):
    settings = await admin_setting_db.get_all()
    kwargs = dict(text='Налаштування', reply_markup=admin_setting_kb(settings))
    if isinstance(upd, Message):
        await upd.answer(**kwargs)
    else:
        await upd.message.edit_text(**kwargs)

async def setting_update_cmd(call: CallbackQuery, callback_data: dict, admin_setting_db: AdminSettingRepo):
    setting = await admin_setting_db.get_setting(int(callback_data['setting_id']))
    await admin_setting_db.update_setting(setting.setting_id, setting_status=False if setting.setting_status else True)
    await setting_cmd(call, admin_setting_db)

async def commission_cmd(msg: Message, commission_db: CommissionRepo):
    packs = await commission_db.get_all()
    text = (
        'Оберіть комісійний пакет, або додайте новий\n\n'
        f'{construct_commission_info(packs)}'
    )
    reply_markup = construct_packs_kb([pack.name for pack in packs])
    await msg.answer(text, reply_markup=reply_markup)
    await CommissionAdminSG.Select.set()


async def select_commission_pack(msg: Message, commission_db: CommissionRepo, user_db: UserRepo, state: FSMContext):
    data = await state.get_data()
    if 'pack_id' in data.keys():
        commission = await commission_db.get_commission(data['pack_id'])
    else:
        commission = await commission_db.get_commission_name(msg.text)
    if not commission:
        await msg.answer('Упс, незнайшов такого пакету, спробуйте ще раз')
        return
    else:
        users = await user_db.get_users_commission(commission.pack_id, count=True)
        text = (
            f'Пакет [{commission.name}]\n\n'
            f'<b>Опис:</b> {commission.description}\n'
            f'<b>Користувачів</b>: {users}\n\n'
            f'<b>Відсоток:</b> {commission.commission}% якщо ціна більше {commission.trigger} грн.\n'
            f'<b>Інші платежі:</b>  {commission.under} грн. якщо ціна менше або дорівнює {commission.trigger} грн.\n'
            f'<b>Ціновий діапазон:</b>  від {commission.minimal} грн. до {commission.maximal} грн.\n'
        )
        await msg.answer(text, reply_markup=keyboard_constructor([Buttons.admin.edit], [Buttons.admin.to_packs]))
        await CommissionAdminSG.Edit.set()
        await state.update_data(pack_id=commission.pack_id)


async def edit_commission(msg: Message, state: FSMContext, commission_db: CommissionRepo):
    data = await state.get_data()
    commission = await commission_db.get_commission(data['pack_id'])
    text = (
        f'Пакет [{commission.name}]\n\n'
        f'<b>Назва</b> - назва комісійного пакету\n'
        f'<b>Опис</b> - опис комісійного пакету\n'
        f'<b>Гранична ціна</b> - максимальна ціна угоди для фіксованої комімісії, зараз {commission.trigger} грн.\n'
        f'<b>Відсоток</b> - відсоток комісії сервісу, діє при ціні вище граничної, зараз {commission.commission}%\n'
        f'<b>Фіксована комісія</b> - комісія сервісу, діє при ціні нижче або рівній граничній, зараз {commission.under} грн.\n'
        f'<b>Мінімальна ціна</b> - мінімально доспустима ціна угоди, зараз {commission.minimal} грн.\n'
        f'<b>Максимальна ціна</b> - максимально допустима ціна угоди, зараз {commission.maximal} грн.\n\n'
        f'Оберіть параметр, яке хочете редагувати'
    )
    await msg.answer(text, reply_markup=edit_commission_kb())
    await CommissionAdminSG.Parameter.set()


async def input_parameter(msg: Message, state: FSMContext, commission_db: CommissionRepo):
    data = await state.get_data()
    commission = await commission_db.get_commission(data['pack_id'])
    parameters = {
        Buttons.admin.commission_edit.name: 'name',
        Buttons.admin.commission_edit.description: 'description',
        Buttons.admin.commission_edit.trigger: 'trigger',
        Buttons.admin.commission_edit.under: 'under',
        Buttons.admin.commission_edit.commission: 'commission',
        Buttons.admin.commission_edit.minimal: 'minimal',
        Buttons.admin.commission_edit.maximal: 'maximal'
    }
    parameter = parameters[msg.text]
    await state.update_data(parameter=parameter)
    await msg.answer(f'Будь-ласка відправте нове значення для параметру "{parameter.lower()}"\n\n'
                     f'Поточне значення: <code>{commission.as_dict()[parameter]}</code>',
                     reply_markup=keyboard_constructor(Buttons.admin.cancel))
    await CommissionAdminSG.Save.set()


async def save_parameter(msg: Message, state: FSMContext, commission_db: CommissionRepo, user_db: UserRepo):
    data = await state.get_data()
    value = msg.text
    if data['parameter'] == 'name' and check_length_failed(value, 255):
        await msg.answer(f'Назва завелика, максимальна к-ть символів 255, замість {len(value)}, спробуйте ще раз')
        return
    elif data['parameter'] == 'description' and check_length_failed(value, 500):
        await msg.answer(f'Опис завеликий, максимальна к-ть символів 500, замість {len(value)}, спробуйте ще раз')
        return
    else:
        if not value.replace('.', '').replace(',', '').isnumeric():
            await msg.answer('Цей параметр має бути числом, спробуйте ще раз')
            return
        else:
            value = int(value)
    await commission_db.update_commission(data['pack_id'], **{data['parameter']: value})
    await edit_commission(msg, state, commission_db)


def setup(dp: Dispatcher):
    #  Back handlers
    dp.register_message_handler(commission_cmd, *filters, text=Buttons.admin.to_packs, state=CommissionAdminSG.Edit)
    dp.register_message_handler(select_commission_pack, *filters, text=Buttons.admin.cancel,
                                state=[CommissionAdminSG.Parameter, CommissionAdminSG.Save])
    #  Main handlers
    dp.register_message_handler(admin_cmd, *filters, state='*', text=(Buttons.menu.admin, Buttons.admin.to_admin))
    dp.register_message_handler(commission_cmd, *filters, state='*', text=Buttons.admin.commission)
    dp.register_message_handler(setting_cmd, text=Buttons.admin.setting, state='*')
    dp.register_message_handler(select_commission_pack, *filters, state=CommissionAdminSG.Select)
    dp.register_message_handler(edit_commission, *filters, state=CommissionAdminSG.Edit, text=Buttons.admin.edit)
    dp.register_message_handler(input_parameter, *filters, state=CommissionAdminSG.Parameter)
    dp.register_message_handler(save_parameter, *filters, state=CommissionAdminSG.Save)

    dp.register_callback_query_handler(setting_update_cmd, admin_setting_cb.filter(), state='*')

def construct_commission_info(commissions: list[CommissionRepo.model]):
    text = ''
    for pack, num in zip(commissions, range(1, len(commissions) + 1)):
        text += f'{num}. {pack.name}\n'
    return text


def check_length_failed(text: str, length: int):
    return len(text) > length
