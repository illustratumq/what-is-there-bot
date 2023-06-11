from PIL import ImageFont, ImageDraw, Image


def make_post_media_template(title: str, description: str, price: int):
    price = 'Договірна' if price == 0 else f'{price} грн.'
    logo = Image.open("app/data/template.png")
    font = ImageFont.truetype('calibri.ttf', 65)
    drawer = ImageDraw.Draw(logo)
    drawer.text((50, 120), split_string(title, n=22), fill='black', font=font, stroke_width=1)
    font = ImageFont.truetype('calibri.ttf', 35)
    y_pos = 215 + 50 * (len(title) // 23)
    drawer.text((50, y_pos), split_string(description), fill='#afafaf', font=font)
    drawer.text((50, 500), f'Ціна: {price}', fill='#afafaf', font=font)
    new_path = f'app/data/{title}.png'
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
    new_path = f'app/data/{room_name}.png'
    logo.save(new_path)
    return new_path


def make_chat_photo_template(number: int):
    logo = Image.open(f'app/data/chat_photo.png')
    font = ImageFont.truetype('calibri.ttf', 100)
    drawer = ImageDraw.Draw(logo)
    y_pos = 300 - 30 * (len(str(number)) - 1)
    drawer.text((y_pos, 265), f'{number}', fill='#333333', font=font, stroke_width=1)
    new_path = f'app/data/chat_photo_{number}.png'
    logo.save(new_path)
    return new_path


def split_string(string: str, n: int = 45):
    new_string = ''
    for word in string.split(' '):
        if len(new_string.split('\n')[-1] + word) > n:
            new_string += f'\n{word}'
        else:
            new_string += word
        new_string += ' '
    return new_string





