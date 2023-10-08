from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery

from app.database.services.repos import LetterRepo
from app.filters.admin import LetterFilter
from app.keyboards import Buttons
from app.keyboards.inline.letter import paginate_letter, letter_cb
from app.misc.times import localize


async def letters_cmd(msg: Message, letter_db: LetterRepo):
    await msg.delete()
    letters_new, letters_old = await letter_db.get_all_user_letters(msg.from_user.id)
    letters = letters_new + letters_old
    if not letters:
        await msg.answer('У вас ще немає повідомлень')
    else:
        await paginate_letters(msg, callback_data={'letter_id': letters[0].letter_id, 'action': 'pag'},
                               letter_db=letter_db)


async def paginate_letters(upd: CallbackQuery | Message, callback_data: dict, letter_db: LetterRepo):

    msg = upd.message if isinstance(upd, CallbackQuery) else upd

    if callback_data['action'] == 'close':
        await msg.delete()
        return

    letter = await letter_db.get_letter(int(callback_data['letter_id']))
    letters_new, letters_old = await letter_db.get_all_user_letters(upd.from_user.id)

    if not letter.read:
        marker = '🆕✉'
    else:
        marker = '✉'

    text = (
        f'<b>{marker} Повідомлення️ №{letter.letter_id}</b>\n'
        f'Непрочитаних: {len(letters_new)}/{len(letters_new) + len(letters_old)}\n\n'
        f'<i>{letter.text.strip()}\n\n'
        f'Отримано {localize(letter.created_at).strftime("%H:%M:%S %d.%m.%y")}</i>\n'
    )

    try:
        await msg.edit_text(text, reply_markup=paginate_letter(letters_new + letters_old, letter.letter_id),
                            disable_web_page_preview=True)
    except:
        await msg.answer(text, reply_markup=paginate_letter(letters_new + letters_old, letter.letter_id),
                         disable_web_page_preview=True)
    await letter_db.update_letter(letter.letter_id, read=True)

def setup(dp: Dispatcher):
    dp.register_message_handler(letters_cmd, LetterFilter(), state='*')
    dp.register_message_handler(letters_cmd, text=Buttons.menu.letter, state='*')
    dp.register_callback_query_handler(paginate_letters, letter_cb.filter(), state='*')