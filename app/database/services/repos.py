from datetime import datetime, timedelta

from sqlalchemy import select, cast
from sqlalchemy.orm import joinedload

from app.database.models import *
from app.database.services.db_ctx import BaseRepo
from app.database.services.enums import DealStatusEnum, RoomStatusEnum, DealTypeEnum, OrderStatusEnum
from app.misc.times import now, deltatime, localize


class UserRepo(BaseRepo[User]):
    model = User

    async def get_user(self, user_id: int) -> User:
        return await self.get_one(self.model.user_id == user_id)

    async def get_users_commission(self, commission_id: int, count: bool = False):
        if count:
            return await self.count(self.model.commission_id == commission_id)
        else:
            return await self.get_all(self.model.commission_id == commission_id)

    async def update_user(self, user_id: int, **kwargs) -> None:
        return await self.update(self.model.user_id == user_id, **kwargs)

    async def delete_user(self, user_id: int):
        return await self.delete(self.model.user_id == user_id)


class PostRepo(BaseRepo[Post]):
    model = Post

    async def get_post(self, post_id: int) -> Post:
        return await self.get_one(self.model.post_id == post_id)

    async def get_posts_user(self, user_id: int) -> list[Post]:
        return await self.get_all(self.model.user_id == user_id)

    async def get_posts_status(self, status: DealStatusEnum) -> list[Post]:
        return await self.get_all(self.model.status == status)

    async def get_post_admin_channel(self, message_id: int) -> Post:
        return await self.get_one(self.model.admin_message_id == message_id)

    async def count_posts(self, date: str, mode: str = '*'):
        search = []
        if '-' in date or date in ('month', 'week'):
            start, end = deltatime(date)
            search.append(self.model.created_at >= start.date())
            search.append(self.model.created_at <= end.date())
        elif date == 'all':
            pass
        else:
            search.append(self.model.created_at >= deltatime(date).date())

        if mode != '*':
            modes = {
                'active': self.model.status == DealStatusEnum.ACTIVE,
                'busy': self.model.status == DealStatusEnum.BUSY,
                'disable': self.model.status == DealStatusEnum.DISABLES,
                'moderate': self.model.status == DealStatusEnum.MODERATE,
                'done': self.model.status == DealStatusEnum.DONE
            }
            search.append(modes[mode])

        return await self.count(*search)

    async def update_post(self, post_id: int, **kwargs) -> None:
        return await self.update(self.model.post_id == post_id, **kwargs)

    async def delete_post(self, post_id: int):
        return await self.delete(self.model.post_id == post_id)


class DealRepo(BaseRepo[Deal]):
    model = Deal

    async def get_deal(self, deal_id: int) -> Deal:
        return await self.get_one(self.model.deal_id == deal_id)

    async def get_deal_chat(self, chat_id: int) -> Deal:
        return await self.get_one(self.model.chat_id == chat_id)

    async def get_deal_status(self, status: DealStatusEnum) -> list[Deal]:
        return await self.get_all(self.model.status == status)

    async def get_deal_type(self, deal_type: DealTypeEnum, status: DealStatusEnum, user_id: int) -> list[Deal]:
        deals = await self.get_all(self.model.type == deal_type, self.model.status == status,
                                   self.model.customer_id == user_id)
        deals += await self.get_all(self.model.type == deal_type, self.model.status == status,
                                    self.model.executor_id == user_id)
        return deals

    async def get_deal_customer(self, customer_id: int, status: DealStatusEnum) -> list[Deal]:
        if isinstance(status, DealStatusEnum):
            return await self.get_all(self.model.customer_id == customer_id, self.model.status == status)
        elif status == '*':
            return await self.get_all(self.model.customer_id == customer_id)

    async def get_deal_post(self, post_id: int) -> Deal:
        return await self.get_one(self.model.post_id == post_id)

    async def get_comment_deals(self, executor_id: int):
        return await self.get_all(self.model.executor_id == executor_id,
                                  self.model.comment != None,
                                  self.model.status == DealStatusEnum.DONE)

    async def get_deal_executor(self, executor_id: int, status: DealStatusEnum) -> list[Deal]:
        if isinstance(status, DealStatusEnum):
            return await self.get_all(self.model.executor_id == executor_id, self.model.status == status)
        elif status == '*':
            return await self.get_all(self.model.executor_id == executor_id)

    async def calculate_user_rating(self, user_id: int) -> tuple:
        deals = await self.get_all(self.model.executor_id == user_id, self.model.status == DealStatusEnum.DONE)
        evaluated = [d for d in deals if d.rating]
        rating = round(sum([d.rating for d in evaluated])/len(evaluated), 2) if evaluated else 0
        return rating, len(evaluated), len(deals)

    async def update_deal(self, deal_id: int, **kwargs) -> None:
        return await self.update(self.model.deal_id == deal_id, **kwargs)

    async def delete_deal(self, deal_id: int):
        return await self.delete(self.model.deal_id == deal_id)


class RoomRepo(BaseRepo[Room]):
    model = Room

    async def get_room(self, chat_id: int) -> Room:
        return await self.get_one(self.model.chat_id == chat_id)

    async def get_free_room(self):
        return await self.get_one(self.model.status == RoomStatusEnum.AVAILABLE)

    async def update_room(self, chat_id: int, **kwargs) -> None:
        return await self.update(self.model.chat_id == chat_id, **kwargs)

    async def delete_room(self, chat_id: int):
        return await self.delete(self.model.chat_id == chat_id)


class MarkerRepo(BaseRepo[Marker]):
    model = Marker

    async def get_marker(self, marker_id: int) -> Marker:
        return await self.get_one(self.model.marker_id == marker_id)

    async def get_markers_user(self, user_id: int) -> list[Marker]:
        return await self.get_all(self.model.user_id == user_id)

    async def get_marker_text(self, user_id: int, text: str) -> Marker:
        return await self.get_one(self.model.text == text, self.model.user_id == user_id)

    async def get_markers_title(self, title: str) -> list[Marker]:
        markers = []
        for m in await self.get_all():
            for word in title.split(' '):
                if word.lower().startswith(m.text.lower()):
                    markers.append(m)
        return markers

    async def update_marker(self, marker_id: int, **kwargs) -> None:
        return await self.update(self.model.marker_id == marker_id, **kwargs)

    async def delete_marker(self, user_id: int, text: str):
        return await self.delete(self.model.text == text, self.model.user_id == user_id)


class SettingRepo(BaseRepo[Setting]):
    model = Setting

    async def get_setting(self, user_id: int) -> Setting:
        return await self.get_one(self.model.user_id == user_id)

    async def update_setting(self, user_id: int, **kwargs) -> None:
        return await self.update(self.model.user_id == user_id, **kwargs)

    async def delete_setting(self, user_id: int):
        return await self.delete(self.model.user_id == user_id)


class CommissionRepo(BaseRepo[Commission]):
    model = Commission

    async def get_commission(self, pack_id: int) -> Commission:
        return await self.get_one(self.model.pack_id == pack_id)

    async def get_commission_name(self, name: str) -> Commission:
        return await self.get_one(self.model.name == name)

    async def update_commission(self, pack_id: int, **kwargs) -> None:
        return await self.update(self.model.pack_id == pack_id, **kwargs)

    async def delete_commission(self, pack_id: int):
        return await self.delete(self.model.pack_id == pack_id)


class OrderRepo(BaseRepo[Order]):
    model = Order

    async def get_order(self, order_id: int) -> Order:
        return await self.get_one(self.model.id == order_id)

    async def get_orders_status(self, status: OrderStatusEnum) -> list[Order]:
        return await self.get_all(self.model.status == status)

    async def get_order_deal(self, deal_id: int) -> Order:
        return await self.get_one(self.model.deal_id == deal_id)

    async def update_order(self, order_id: int, **kwargs) -> None:
        return await self.update(self.model.id == order_id, **kwargs)

    async def delete_order(self, order_id: int):
        return await self.delete(self.model.id == order_id)