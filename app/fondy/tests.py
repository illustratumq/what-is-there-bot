import asyncio
import sys

from app.database.services.repos import OrderRepo, MerchantRepo

# sys.path.append(r'\Users\pasho\FreelanceProject\what-is-there-bot')
from app.config import Config
config = Config.from_env()

from app.fondy.new_api import FondyApiWrapper


async def test(session):
    pass
    # fondy = FondyApiWrapper(session)
    # order_db = OrderRepo(session)
    # merchant_db = MerchantRepo(session)
    # order = await order_db.get_order(6)
    # merchant = await merchant_db.get_merchant(order.merchant_id)
    # print(order, merchant)
    # await fondy.payout_order(order, merchant, '4731185670621553')
    # print(await fondy.make_capture(order, merchant))
    # input('>>')



