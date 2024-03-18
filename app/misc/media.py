import os

from PIL import ImageFont, ImageDraw, Image

from app.database.services.enums import PostStatusText


def create_new_filename():
    test = False
    if test:
        return 'app/data/photo.png'
    else:
        return f'app/data/photo_{len(os.listdir("app/data/"))+1}.jpg'

def make_post_media_template(title: str, description: str, price: int, version: str = 'active'):
    price = 'Договірна' if price == 0 else f'{price} грн'
    logo = Image.open(f"app/data/{version}.jpg")
    font = ImageFont.truetype('RockStar-Bold.ttf', 96)
    drawer = ImageDraw.Draw(logo)
    drawer.text((110, 130), split_string(title, 18), fill='#000000', font=font)
    font = ImageFont.truetype('RockStar-Bold.ttf', 45)
    y_pos = 280 + 50 * (len(title) // 18)
    drawer.text((110, y_pos), split_string(description), fill='#4D4D4D', font=font)
    font = ImageFont.truetype('RockStar-Bold.ttf', 58)
    status = {
        'active': PostStatusText.ACTIVE,
        'process': PostStatusText.BUSY,
        'done': PostStatusText.DONE
    }
    drawer.text((220, 560), status[version].split(' ')[-1], fill='#000000', font=font)
    drawer.text((220, 680), f'{price}', fill='#000000', font=font)
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def make_admin_media_template(room_name: str, reason: str, status: str, file: str):
    logo = Image.open(f'app/data/{file}-admin.jpg')
    font = ImageFont.truetype('RockStar-Bold.ttf', 80)
    drawer = ImageDraw.Draw(logo)
    drawer.text((110, 130), f'Адміністратор в {room_name}', fill='#000000', font=font)
    font = ImageFont.truetype('RockStar-Bold.ttf', 50)
    drawer.text((110, 250), split_string(reason), fill='#4D4D4D', font=font)
    font = ImageFont.truetype('RockStar-Bold.ttf', 58)
    drawer.text((220, 680), f'{status}', fill='#000000', font=font)
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def make_chat_photo_template(path: str, number: int):
    logo = Image.open(path)
    font = ImageFont.truetype('Helvetica 77 Bold Condensed.otf', 180)
    drawer = ImageDraw.Draw(logo)
    drawer.text((367, 367), f'#{number}', fill='#0087EB', font=font, anchor='mm')
    new_path = create_new_filename()
    logo.save(new_path)
    return new_path


def split_string(text: str, max_string_length: int = 32, max_text_length: int = 110):
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
            new_text += '...'
            break
        else:
            new_text += ' '
    return new_text
