import hashlib

import aiohttp
from aiogram.utils.json import json

from app.config import Config
from app.database.models import Deal
from app.database.services.enums import DealTypeEnum
from app.database.services.repos import UserRepo, PostRepo, OrderRepo


class FondyApiWrapper:

    order_url = 'https://pay.fondy.eu/api/checkout/url/'
    check_url = 'https://pay.fondy.eu/api/status/order_id'

    def __init__(self, config: Config):
        self.merchant_id = config.bot.fondy_merchant_id
        self.secret_key = config.bot.fondy_credit_key

    @staticmethod
    async def _post_request(url: str, body: dict) -> dict:
        session = aiohttp.ClientSession(json_serialize=json.dumps)
        async with session.post(url, json=body, headers={'Content-Type': 'application/json'}) as resp:
            result = await resp.json()
        await session.close()
        return result

    async def create_order(self, deal: Deal, user_db: UserRepo, post_db: PostRepo, order_db: OrderRepo,
                           need_to_pay: int) -> tuple[dict, OrderRepo.model]:
        customer = await user_db.get_user(deal.customer_id)
        executor = await user_db.get_user(deal.executor_id)
        order: OrderRepo.model = await order_db.add(deal_id=deal.deal_id, price=need_to_pay)
        if deal.type == DealTypeEnum.PUBLIC:
            post = await post_db.get_post(deal.post_id)
            order_desc = (
                f'Сплата за угоду №{deal.deal_id} - "{post.title}", '
                f'укладеної між {customer.full_name} (замовник) та {executor.full_name} '
                f'(виконавець)'
            )
        else:
            order_desc = (
                f'Сплата приватної угоди №{deal.deal_id} укладеної '
                f'між {customer.full_name} (замовник) та {executor.full_name} '
                f'(виконавець)'
            )
        amount = str(need_to_pay * 100)

        data = {
            'request': {
                'order_id': order.order_id,
                'merchant_id': self.merchant_id,
                'order_desc': order_desc,
                'amount': amount,
                'currency': 'UAH',
                'merchant_data': f'{deal.deal_id}',
                'preauth': 'Y',
                'lang': 'uk',
            }
        }

        keys = list(data['request'].keys())
        keys.sort()
        signature_args = [self.secret_key]
        for key in keys:
            signature_args.append(data['request'][key])
        signature = self._generate_signature(*signature_args)
        data['request'].update(signature=signature)

        return await self._post_request(self.order_url, data), order

    @staticmethod
    def _generate_signature(*values) -> str:
        string = '|'.join([str(m) for m in values])
        s = hashlib.sha1(bytes(string, 'utf-8'))
        return s.hexdigest()

    async def check_order(self, order_id: str):
        signature = self._generate_signature(
            self.secret_key, self.merchant_id, order_id
        )
        data = {
            'request': {
                'order_id': order_id,
                'merchant_id': self.merchant_id,
                'signature': signature
            }
        }
        return await self._post_request(self.check_url, data)
