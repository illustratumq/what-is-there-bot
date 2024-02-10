from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery

from app.database.services.repos import LetterRepo
from app.keyboards import Buttons
from app.keyboards.inline.letter import paginate_letter, letter_cb
from app.misc.times import localize


async def letters_cmd(msg: Message, letter_db: LetterRepo):
    await msg.delete()
    letters = await letter_db.get_all_user_letters(msg.from_user.id)
    if not letters:
        await msg.answer('У вас ще немає повідомлень')
    else:
        await paginate_letters(msg, callback_data={'letter_id': letters[0].letter_id, 'action': 'pag'},
                               letter_db=letter_db)


async def paginate_letters(upd: CallbackQuery | Message, callback_data: dict, letter_db: LetterRepo):

    msg = upd.message if isinstance(upd, CallbackQuery) else upd
    letters = await letter_db.get_all_user_letters(upd.from_user.id)
    letters = sorted(letters, key=lambda l: l.created_at, reverse=True)
    count_letters = len(letters)

    if callback_data['action'] in ['prev', 'next'] and count_letters == 1:
        await upd.answer('У вас тільки одне повідомлення')
        return

    letter = await letter_db.get_letter(int(callback_data['letter_id']))
    new_letters = await letter_db.get_new_letters_user(upd.from_user.id)
    new_letters_count = (len(new_letters) - 1)

    if new_letters_count > 0:
        marker = '📬'
    else:
        marker = '📭'

    unread_letters_text = f' ({new_letters_count + 1})' if new_letters_count > 0 else ''
    letters_ids = [lt.letter_id for lt in letters]
    text = (
        f'<b>{marker} Ваша поштова скринька{unread_letters_text}</b>\n\n'
        f'🗓 {localize(letter.created_at).strftime("%H:%M:%S %d.%m.%y")}\n\n'
        # f'Непрочитаних: {len(letters_new)}/{len(letters_new) + len(letters_old)}\n\n'
        f'<pre>{letter.text.strip()}\n\n[Лист {letters_ids.index(letter.letter_id) + 1} з {count_letters}]</pre>'
    )

    kwargs = dict(text=text, reply_markup=paginate_letter(letters, letter.letter_id), disable_web_page_preview=True)
    if isinstance(upd, CallbackQuery):
        await msg.edit_text(**kwargs)
    else:
        await msg.answer(**kwargs)
    await letter_db.update_letter(letter.letter_id, read=True)

def setup(dp: Dispatcher):
    dp.register_message_handler(letters_cmd, text=[Buttons.menu.letter, Buttons.menu.new_letter], state='*')
    dp.register_message_handler(letters_cmd, text=Buttons.menu.letter, state='*')
    dp.register_callback_query_handler(paginate_letters, letter_cb.filter(), state='*')