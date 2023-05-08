from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import AllowedUpdates, Message, CallbackQuery, ChatType

from app.config import Config
from app.database.services.enums import UserTypeEnum, UserStatusEnum
from app.database.services.repos import UserRepo


class ACLMiddleware(BaseMiddleware):
    allowed_updates = (AllowedUpdates.MESSAGE, AllowedUpdates.CALLBACK_QUERY)

    greeting_text = (
        'Цей бот дозволяє вам опублікувати та керувати постами на каналі А ШО ТАМ?.\n\n'
        'Нижче в чаті ви побачите кнопки, які дозволяють вам взаємодіяти з ботом. 👇\n\n'
        'Новий пост ➕ - Опублікувати новий пост на каналі.\n'
        'Мої чати 💬 -  Переглянути ваші активні чати.\n'
        'Мій рейтинг ⭐️ - Переглянути ваш рейтинг у сервісі та додати опис про себе.\n'
        'Мої пости 📑 -  Переглянути та керувати своїми постами на каналі.\n'
        'Мої кошти 💸 - Перевірити ваш баланс та вивести кошти з рахунку каналу.\n'
        'Сповіщення 🔔 -  Налаштувати сповіщення про нові пости на каналі.\n\n'
        'Якщо у вас є запитання щодо реклами, співпраці або будь-яких інших питань, '
        'а також якщо у вас є ідеї щодо покращення сервісу, ви можете зв\'язатися з адміністрацією'
        ' каналу за допомогою контакту @'

    )

    @staticmethod
    async def setup_chat(msg: Message, user_db: UserRepo, config: Config) -> None:
        if not msg.from_user.is_bot:
            user = await user_db.get_user(msg.from_user.id)
            if not user:
                await user_db.add(
                    full_name=msg.from_user.full_name, mention=msg.from_user.get_mention(), user_id=msg.from_user.id
                )
                if msg.from_user.id in config.bot.admin_ids:
                    await user_db.update_user(msg.from_user.id, type=UserTypeEnum.ADMIN)
                elif msg.from_user.id in config.bot.moder_ids:
                    await user_db.update_user(msg.from_user.id, type=UserTypeEnum.MODERATOR)
                await msg.answer(ACLMiddleware.greeting_text)
            elif user.status == UserStatusEnum.BANNED:
                text = (
                    f'Вам обмежено доступ до даного сервісу. Причина:\n\n<i>{user.ban_comment}</i>'
                )
                await msg.bot.send_message(msg.from_user.id, text)
                raise CancelHandler()
            else:
                values_to_update = dict()
                if user.full_name != msg.from_user.full_name:
                    values_to_update.update(full_name=msg.from_user.full_name)
                if user.mention != msg.from_user.get_mention():
                    values_to_update.update(mention=msg.from_user.get_mention())
                if values_to_update:
                    await user_db.update_user(msg.from_user.id, **values_to_update)

    async def on_pre_process_message(self, msg: Message, data: dict) -> None:
        if not bool(msg.media_group_id):
            if msg.chat.type == ChatType.PRIVATE:
                await self.setup_chat(msg, data['user_db'], Config.from_env())

    async def on_pre_process_callback_query(self, call: CallbackQuery, data: dict) -> None:
        if call.message.chat.type == ChatType.PRIVATE:
            await self.setup_chat(call.message, data['user_db'], Config.from_env())
