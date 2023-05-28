

class Menu:
    to_markers: str = '◀ До сповіщень'
    to_rating: str = '◀ До рейтингу'
    markers: str = 'Підписки 📚'
    work_times: str = 'Час роботи ⏱'
    new_marker: str = 'Додати'
    del_marker: str = 'Видалити'
    new_post: str = 'Новий пост ➕'
    new_deal: str = 'Нова угода 🤝'
    my_posts: str = 'Мої пости 📑'
    my_chats: str = 'Мої чати 💬'
    my_money: str = 'Мої кошти 💸'
    my_rating: str = 'Мій рейтинг ⭐'
    notifications: str = 'Сповіщення 🔔'
    payout: str = 'Вивести кошти'
    about: str = 'Додати опис ➕'
    comment: str = 'Відгуки про мене 💭'
    admin: str = '🔁 В адмін-панель'
    back: str = '◀ Назад'


class Action:
    cancel: str = 'Відмінити'
    confirm: str = 'Готово ✅'
    delete: str = 'Так, видалити ✔'


class DealAdmin:
    enter_chat: str = 'Стати адміністратором чату ✅'
    refuse_chat: str = 'Відмовитися'
    done_deal: str = 'Завершити угоду'
    cancel_deal: str = 'Відмінити угоду'
    ban_user: str = '🔒 Блокувати користувача'
    restrict_user: str = '🔐 Обмежити користувача'
    customer: str = 'Замовник'
    executor: str = 'Виконавець'
    close: str = 'Закрити'
    confirm: str = 'Так, я на 100% впевнений'
    back: str = '◀ Назад'


class Deal:
    admin = DealAdmin()
    chat: str = '💬 Зв\'язатися'
    cancel: str = 'Відхилити'
    sort: str = 'Відсортувати: {}'
    comment: str = '💭 Залишити відгук'
    confirm_activity: str = 'Так, угода акутальна'
    read_comments: str = 'Читати відгуки...'
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
    manage_post: str = 'Керувати постом 📝'
    publish_all: str = 'Опублікувати всі'
    back: str = 'Назад'


class Chat:
    pay: str = '💳 Оплатити'
    edit_price: str = '💸 Редагувати ціну'
    end_deal: str = '⏹ Завершити угоду'
    admin: str = '👨‍💻👩‍💻 Виклик адміністратора'
    media: str = '📂 Матеріали завдання'
    done_deal: str = 'Завершити угоду'
    cancel_deal: str = 'Відмінити угоду'
    confirm: str = 'Підтверджую ✔'
    cancel: str = '◀ Назад'


class Pay:
    pay_deal_fully = 'Оплатити всю суму угоди'
    pay_deal_partially = 'Зняти частину з балансу'
    pay_deal_balance = 'Зняти всю суму з балансу'
    confirm: str = 'Підтверджую ✔'
    cancel: str = 'Відмінити'


class Admin:
    statistic: str = '📊 Статистика'
    commission: str = '💵 Комісія'
    setting: str = '⚙ Налаштування'
    user: str = '🗂 Юзери'
    menu: str = '🔁 В головне меню'
    back: str = '◀ В адмін панель'


class Buttons:
    menu = Menu()
    action = Action()
    post = Post()
    deal = Deal()
    chat = Chat()
    admin = Admin()
    pay = Pay()
