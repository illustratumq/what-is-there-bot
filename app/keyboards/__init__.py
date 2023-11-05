

class Menu:
    to_markers: str = '◀ До сповіщень'
    letter: str = 'Повідомлення ✉️'
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
    about: str = 'Змінити опис про мене ✍️'
    comment: str = 'Відгуки про мене 💭'
    admin: str = '🔁 В адмін-панель'
    back: str = '◀ Назад'

    @staticmethod
    def new_letter(n):
        return f'Повідомлення 📩 ({n})'


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
    sort: str = 'Сортувати: {}'
    comment: str = '💭 Залишити відгук'
    read_comments: str = 'Відгуки про виконавця'
    read: str = 'Читати'
    close: str = 'Закрити'
    customer: str = 'Я замовник'
    executor: str = 'Я виконавець'


class Post:
    channel: str = 'Переглянути пост'
    update: str = 'Оновити 🔄'
    delete: str = 'Видалити 🗑'
    contract: str = 'Договірна'
    publish: str = 'Опубліковати 📬'
    cancel: str = 'Скасувати'
    understand = 'Зрозуміло 👌'
    confirm: str = 'Підтвержую ✔'
    participate: str = 'Долучитися'
    send_deal: str = 'Надіслати запит 📤'
    manage_post: str = 'Керувати постом 📝'
    publish_all: str = 'Опублікувати всі'
    back: str = 'Назад'


class Chat:
    call_user: str = '🗣 Покликати {}'
    pay: str = '💳 Оплатити'
    edit_price: str = '💸 Редагувати ціну'
    end_deal: str = 'Завершити/Відмінти угоду'
    admin: str = '👨‍💻👩‍💻 Виклик адміністратора'
    media: str = '📂 Матеріали завдання'
    done_deal: str = '✅ Завершити угоду'
    cancel_deal: str = '❌ Відмінити угоду'
    confirm: str = 'Підтверджую ✔'
    cancel: str = '◀ Назад'


class Pay:
    pay_deal_fully = 'Оплатити всю суму угоди 💳'
    pay_deal_partially = 'Зняти частину з балансу'
    pay_deal_balance = 'Зняти всю суму з балансу'
    confirm: str = 'Підтверджую ✔'
    cancel: str = 'Відмінити'


class Commission:
    name: str = 'Назва'
    description: str = 'Опис'
    minimal: str = 'Мінімальна ціна'
    maximal: str = 'Макимальна ціна'
    commission: str = 'Відсоток'
    under: str = 'Фіксована комісія'
    trigger: str = 'Гранична ціна'


class AdminPost:
    delete: str = 'Видалити пост 🗑'
    server: str = 'В адмін панель 🖥'
    delete_comment: str = 'Видалити коментар / оцінку'
    delete_force: str = 'Видалити примусово'
    main: str = '◀ Назад'
    back: str = 'Закрити'

class Date:
    week: str = 'Цей тиждень'
    month: str = 'Цей місяць'
    day: str = 'Сьогодні'
    select_date: str = 'Власна дата'

class Statistic:
    date_menu = Date()
    deals: str = 'Угоди 🤝'
    posts: str = 'Пости 📬'
    finance: str = 'Фінанси 💸'
    users: str = 'Користувачі 👤'
    update: str = 'Оновити 🔄'
    date: str = 'Період 🗓'

class Admin:
    statistic = 'Статистика 📊'
    statistic_menu = Statistic()
    post = AdminPost()
    commission_edit = Commission()
    commission: str = '💵 Комісія'
    setting: str = '⚙ Налаштування'
    user: str = '🗂 Юзери'
    menu: str = '🔁 В головне меню'
    edit: str = 'Редагувати'
    cancel: str = 'Відмінити'
    to_admin: str = '◀ В адмін панель'
    to_packs: str = '◀ До пакунків'
    user_detail: str = 'Переглянути всю інформацію'


class Buttons:
    menu = Menu()
    action = Action()
    post = Post()
    deal = Deal()
    chat = Chat()
    admin = Admin()
    pay = Pay()
