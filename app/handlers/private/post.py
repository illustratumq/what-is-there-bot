from contextlib import suppress
from datetime import timedelta, datetime

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, MediaGroupFilter
from aiogram.types import Message, ChatType, ContentType, InputMediaPhoto, InputMediaDocument, MediaGroup, ContentTypes
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import PostStatusText
from app.database.services.repos import PostRepo, DealRepo
from app.keyboards import Buttons
from app.keyboards.inline.moderate import moderate_post_kb
from app.keyboards.reply.menu import basic_kb, menu_kb
from app.misc.times import now
from app.states.states import PostSG

cancel_kb = basic_kb([Buttons.action.cancel])


async def new_post_title(msg: Message, state: FSMContext):
    text = (
        'Напишіть назву предмету або що потрібно зробити'
    )
    message = await msg.answer(text, reply_markup=cancel_kb)
    await state.update_data(last_msg_id=message.message_id)
    await PostSG.Title.set()


async def new_post_about(msg: Message, state: FSMContext):
    await clear_last_message(await state.get_data(), msg)
    data = {}
    if await check_is_title_ok(msg, data):
        await state.update_data(title_message_id=msg.message_id)
        text = 'Максимально докладно опишіть завдання'
        await PostSG.About.set()
    else:
        text = f'Ваша назва предмету повинна містити від 3 до 30 символів (зараз {len(msg.text)})'
    message = await msg.answer(text, reply_markup=cancel_kb)
    await state.update_data(**data, last_msg_id=message.message_id)


async def new_post_price(msg: Message, state: FSMContext):
    await clear_last_message(await state.get_data(), msg)
    data = {}
    if await check_is_about_ok(msg, data):
        text = 'Надішліть ціну за завдання (ціле число)'
        buttons = [Buttons.post.contract], [Buttons.action.cancel]
        data.update(about_message_id=msg.message_id)
        await PostSG.Price.set()
    else:
        text = f'Ваш опис завдання повинен містити від 10 до 500 символів (зараз {len(msg.text)})'
        buttons = [Buttons.action.cancel]
    message = await msg.answer(text, reply_markup=basic_kb(buttons))
    data.update(last_msg_id=message.message_id)
    await state.update_data(**data)


async def new_post_media(msg: Message, state: FSMContext):
    await clear_last_message(await state.get_data(), msg)
    data = {}
    if not check_is_price_ok(msg.text, data):
        message = await msg.answer('Ваша ціна за завдання має бути від 10 до 10000', reply_markup=cancel_kb)
        await state.update_data(last_msg_id=message.message_id)
        return
    text = (
        f'Надішліть інші матеріали, що стосуються завдання.\n\n'
        f'Це можуть бути файли або фото. Після закінчення натисніть кнопку <b>{Buttons.action.confirm}</b>'
    )
    await msg.answer(text, reply_markup=basic_kb(([Buttons.action.confirm], [Buttons.action.cancel])))
    await PostSG.Media.set()
    await state.update_data(**data, price_message_id=msg.message_id,
                            media=[], media_url=None, media_type=None, media_id=None)


async def add_media_group_to_post(msg: Message, state: FSMContext, media: list[Message]):
    new_media = []
    for m in media:
        await append_new_media(new_media, m, media[0].content_type)
    await process_add_new_media(msg, state, media[0].content_type, new_media)


async def add_media_to_post(msg: Message, state: FSMContext):
    new_media_type = msg.content_type
    new_media = []
    await append_new_media(new_media, msg, new_media_type)
    await process_add_new_media(msg, state, new_media_type, new_media)


async def new_post_confirm_media(msg: Message, state: FSMContext, config: Config):
    data = await state.get_data()
    if data['media']:
        data = await publish_channel_media(state, data, config.misc.media_channel_chat_id, msg.bot)
    post_msg = await msg.answer(construct_post_text(data))
    await state.update_data(post_message_id=post_msg.message_id)
    await msg.answer(
        f'<b>Пост готовий!</b>\n\n'
        f'Щоб змінити вміст посту, просто відредагуйте повідомлення, з яких він був зібраний (окрім матеріалів).\n\n'
        f'Якщо все правильно, натисніть кнопку "{Buttons.post.publish}", щоб опублікувати пост на каналі.\n\n'
        f'Щоб зробити ціну договірною, змініть її на "0".',
        reply_markup=basic_kb(([Buttons.post.publish], [Buttons.action.cancel]))
    )
    await PostSG.Confirm.set()


async def edit_new_post_data(msg: Message, state: FSMContext):
    data = await state.get_data()
    post_message_id = data['post_message_id']
    edited_message_id = msg.message_id
    edited_data = {}
    if data['title_message_id'] == edited_message_id:
        if not await check_is_title_ok(msg, edited_data):
            await msg.answer(f'Ваша назва предмету повинна містити від 3 до 30 символів (зараз {len(msg.text)})')
            return
    elif data['about_message_id'] == edited_message_id:
        if not await check_is_about_ok(msg, edited_data):
            await msg.answer(f'Ваш опис завдання повинен містити від 10 до 500 символів (зараз {len(msg.text)})')
            return
    elif data['price_message_id'] == edited_message_id:
        if not check_is_price_ok(msg.text, edited_data):
            await msg.answer('Ваша ціна за завдання має бути від 10 до 10000')
    else:
        return
    data.update(edited_data)
    await state.update_data(**edited_data)
    await msg.bot.edit_message_text(
        text=construct_post_text(data), chat_id=msg.from_user.id, message_id=post_message_id
    )


async def publish_post_cmd(msg: Message, state: FSMContext, post_db: PostRepo, deal_db: DealRepo, config: Config):
    data = await state.get_data()
    post = await post_db.add(
        title=data['title'], about=data['about'], price=data['price'],
        media_id=data['media_id'], media_url=data['media_url'], user_id=msg.from_user.id,
    )
    deal = await deal_db.add(
        post_id=post.post_id, customer_id=msg.from_user.id, price=post.price,
    )
    message = await msg.bot.send_message(config.misc.admin_channel_id, post.construct_post_text(use_bot_link=False),
                                         reply_markup=moderate_post_kb(post))
    await post_db.update_post(post.post_id, admin_message_id=message.message_id, deal_id=deal.deal_id)
    text = (
        'Ваш пост відправлений на модерацію 👌'
    )
    await msg.answer(text, reply_markup=menu_kb())
    await state.finish()


def setup(dp: Dispatcher):
    dp.register_message_handler(new_post_title, text=Buttons.menu.new_post, state='*')
    dp.register_message_handler(new_post_about, ChatTypeFilter(ChatType.PRIVATE), state=PostSG.Title)
    dp.register_message_handler(new_post_price, ChatTypeFilter(ChatType.PRIVATE), state=PostSG.About)
    dp.register_message_handler(new_post_media, ChatTypeFilter(ChatType.PRIVATE), state=PostSG.Price)
    dp.register_message_handler(
        add_media_group_to_post, ChatTypeFilter(ChatType.PRIVATE), MediaGroupFilter(True),
        content_types=ContentTypes.PHOTO | ContentTypes.DOCUMENT, state=PostSG.Media,

    )
    dp.register_message_handler(
        add_media_to_post, ChatTypeFilter(ChatType.PRIVATE), MediaGroupFilter(False),
        content_types=ContentTypes.PHOTO | ContentTypes.DOCUMENT, state=PostSG.Media

    )
    dp.register_message_handler(
        new_post_confirm_media, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.action.confirm, state=PostSG.Media
    )
    dp.register_edited_message_handler(edit_new_post_data, ChatTypeFilter(ChatType.PRIVATE), state=PostSG.Confirm)
    dp.register_message_handler(publish_post_cmd, state=PostSG.Confirm, text=Buttons.post.publish)


async def clear_last_message(data: dict, msg: Message) -> None:
    msg_id = data.get('last_msg_id')
    with suppress(Exception):
        await msg.bot.delete_message(msg.from_user.id, msg_id)


async def check_is_title_ok(msg: Message, data: dict) -> bool:
    title = msg.text
    if len(title) < 3 or len(title) > 30:
        return False
    else:
        if data is not None:
            data.update(title=msg.text)
        return True


async def check_is_about_ok(msg: Message, data: dict) -> bool:
    about = msg.text
    if len(about) < 10 or len(about) > 500:
        return False
    else:
        if data is not None:
            data.update(about=msg.text)
        return True


def check_is_price_ok(price: str, data: dict) -> bool:
    if price == Buttons.post.contract:
        data.update({'price': 0})
        return True
    elif price.isnumeric():
        price = int(price)
        if 10 <= price <= 10000 or price == 0:
            data.update({'price': price})
            return True
    else:
        return False


async def process_add_new_media(msg: Message, state: FSMContext, new_media_type: str, new_media: list[str]) -> None:
    async with state.proxy() as data:
        current_media_type = data['media_type']
        current_media = data['media']
        if current_media_type is None:
            data['media_type'] = new_media_type
            current_media_type = new_media_type
        if current_media_type != new_media_type:
            await msg.answer('Не можна додавати матеріали різних типів (АБО документ, АБО фото)')
            return
        elif len(current_media) + len(new_media) > 10:
            await msg.answer('Ви не можете додати більше 10 матеріалів')
            return
        data['media'].extend(new_media)
        await msg.answer('Матеріали додано')


async def append_new_media(media_array: list, media: Message, media_type: str) -> None:
    if media_type == ContentType.PHOTO:
        media_array.append(media.photo[-1].file_id)
    else:
        media_array.append(media.document.file_id)


async def publish_channel_media(state: FSMContext, data: dict, channel_id: int, bot: Bot):
    _InputMedia = InputMediaPhoto if data['media_type'] == ContentType.PHOTO else InputMediaDocument
    media_group = MediaGroup([_InputMedia(file_id) for file_id in data['media']])
    media_group_msg = await bot.send_media_group(channel_id, media_group)
    media_group_url = media_group_msg[-1].url
    media_group_id = media_group_msg[-1].message_id
    await state.update_data(media_url=media_group_url, media_id=media_group_id)
    return await state.get_data()


def construct_post_text(data: dict):
    title = data['title']
    about = data['about']
    price = data['price'] if data['price'] != 0 else 'Договірна'
    media_url = data['media_url']
    text = (
        f'{PostStatusText.ACTIVE}\n\n'
        f'<b>{title}</b>\n\n'
        f'{about}\n\n'
        f'Ціна: {price} {hide_link(media_url)}'
    )
    return text
