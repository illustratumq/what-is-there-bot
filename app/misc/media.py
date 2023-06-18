import os

from PIL import ImageFont, ImageDraw, Image


def create_new_filename():
    return f'app/data/photo_{len(os.listdir("app/data/"))+1}.png'

def make_post_media_template(title: str, description: str, price: int, version: str = 'orig'):
    price = 'Договірна' if price == 0 else f'{price} грн.'
    logo = Image.open(f"app/data/template-{version}.png")
    font = ImageFont.truetype('calibri.ttf', 65)
    drawer = ImageDraw.Draw(logo)
    drawer.text((50, 110), split_string(title, 22), fill='black', font=font, stroke_width=1)
    font = ImageFont.truetype('calibri.ttf', 35)
    y_pos = 205 + 50 * (len(title) // 23)
    drawer.text((50, y_pos), split_string(description), fill='#afafaf', font=font)
    drawer.text((50, 500), f'Ціна: {price}', fill='#afafaf', font=font)
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def make_admin_media_template(room_name: str, reason: str, status: str, file: str):
    logo = Image.open(f'app/data/template-admin-{file}.png')
    font = ImageFont.truetype('calibri.ttf', 55)
    drawer = ImageDraw.Draw(logo)
    drawer.text((50, 70), f'Адміністратор в {room_name}', fill='black', font=font, stroke_width=1)
    font = ImageFont.truetype('calibri.ttf', 35)
    drawer.text((50, 155), split_string(reason), fill='#afafaf', font=font)
    drawer.text((50, 325), f'Статус: {status}', fill='#afafaf', font=font)
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def make_chat_photo_template(number: int):
    logo = Image.open(f'app/data/chat_photo.png')
    font = ImageFont.truetype('calibri.ttf', 100)
    drawer = ImageDraw.Draw(logo)
    y_pos = 300 - 30 * (len(str(number)) - 1)
    drawer.text((y_pos, 265), f'{number}', fill='#333333', font=font, stroke_width=1)
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def split_string(text: str, max_string_length: int = 45, max_text_length: int = 255):
    text = text.replace('\n', ' ').replace('.', '. ').replace('!', '! ').replace('?', '? ')
    text = text.replace('.  ', '. ').replace('!  ', '! ').replace('?  ', '? ')
    words = text.split(' ')
    new_text = ''
    for word, c in zip(words, range(len(words))):
        index = 0 if c == 0 else c - 1
        is_capitalize = any(['.' in words[index].strip(), '!' in words[index].strip(), '?' in words[index].strip()])
        if is_capitalize:
            word = word.capitalize()
        if len(new_text.split('\n')[-1] + word) > max_string_length:
            new_text += '\n' + word
        else:
            new_text += word
        if len(new_text) >= max_text_length:
            new_text += '[...]'
            break
        else:
            new_text += ' '
    return new_text





