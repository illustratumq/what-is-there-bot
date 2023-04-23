from app.database.models import *
from app.database.services.db_ctx import BaseRepo
from app.database.services.enums import DealStatusEnum, RoomStatusEnum


class UserRepo(BaseRepo[User]):
    model = User

    async def get_user(self, user_id: int) -> User:
        return await self.get_one(self.model.user_id == user_id)

    async def update_user(self, user_id: int, **kwargs) -> None:
        return await self.update(self.model.user_id == user_id, **kwargs)

    async def delete_user(self, user_id: int):
        return await self.delete(self.model.user_id == user_id)


class PostRepo(BaseRepo[Post]):
    model = Post

    async def get_post(self, post_id: int) -> Post:
        return await self.get_one(self.model.post_id == post_id)

    async def get_posts_user(self, user_id: int, status: DealStatusEnum) -> list[Post]:
        return await self.get_all(self.model.user_id == user_id, self.model.status == status)

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

    async def get_deal_customer(self, customer_id: int, status: DealStatusEnum) -> list[Deal]:
        return await self.get_all(self.model.customer_id == customer_id, self.model.status == status)

    async def get_deal_executor(self, executor_id: int, status: DealStatusEnum) -> list[Deal]:
        return await self.get_all(self.model.executor_id == executor_id, self.model.status == status)

    async def calculate_user_rating(self, user_id: int) -> tuple:
        deals = await self.get_all(self.model.executor_id == user_id, self.model.status == DealStatusEnum.DONE)
        count_deals = len(deals)
        if count_deals == 0:
            return 0, 0, 0
        deals_with_rating = 0
        user_rating = 0
        for deal in deals:
            user_rating += deal.rating if deal.rating else 5
            deals_with_rating += 1 if deal.rating else 0
        return count_deals, deals_with_rating, user_rating / count_deals

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
        for marker in await self.get_all():
            for word in title.split(' '):
                if word.lower().startswith(marker.text.lower()):
                    markers.append(marker)
        return markers

    async def update_marker(self, marker_id: int, **kwargs) -> None:
        return await self.update(self.model.marker_id == marker_id, **kwargs)

    async def delete_marker(self, user_id: int, text: str):
        return await self.delete(self.model.text == text, self.model.user_id == user_id)