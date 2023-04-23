

class Menu:
    to_markers: str = '◀ До сповіщень'
    markers: str = 'Підписки 📚'
    work_times: str = 'Час роботи ⏱'
    new_marker: str = 'Додати ➕'
    del_marker: str = 'Видалити ➖'
    new_post: str = 'Новий пост ➕'
    my_posts: str = 'Мої пости 📑'
    my_chats: str = 'Мої чати 💬'
    my_money: str = 'Мої кошти 💸'
    my_rating: str = 'Мій рейтинг ⭐'
    notifications: str = 'Сповіщення 🔔'
    payout: str = 'Вивести кошти'
    about: str = 'Додати опис ➕'
    comment: str = 'Відгуки про мене 💭'
    back: str = '◀ Назад'


class Action:
    cancel: str = 'Відмінити'
    confirm: str = 'Готово ✅'
    delete: str = 'Так, видалити ✔'


class Deal:
    chat: str = '💬 Зв\'язатися'
    cancel: str = 'Відхилити'
    comment: str = '➕💭 Додати відгук'
    close: str = 'Закрити'


class Post:
    channel: str = 'Переглянути пост'
    update: str = 'Оновити 🔄'
    delete: str = 'Видалити 🗑'
    contract: str = 'Договірна'
    publish: str = 'Опубліковати 📬'
    cancel: str = 'Скасувати'
    confirm: str = 'Підтвержую ✔'
    participate: str = 'Долучитися'
    send_deal: str = 'Надіслати запит ✉'
    back: str = 'Назад'


class Chat:
    pay: str = '💳 Оплатити'
    edit_price: str = '💸 Редагувати ціну'
    end_deal: str = '⏹ Завершити угоду'
    admin: str = '👨‍💻 Виклик адміністратора'
    media: str = '📂 Матеріали завдання'
    done_deal: str = 'Завершити угоду'
    cancel_deal: str = 'Відмінити угоду'
    confirm: str = 'Підтверджую ✔'
    cancel: str = 'Відмінити'


class Buttons:
    menu = Menu()
    action = Action()
    post = Post()
    deal = Deal()
    chat = Chat()