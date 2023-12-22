import base64
import hashlib
import logging

import aiohttp
from aiogram.utils.json import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.models import Order
from app.database.services.repos import Deal, OrderRepo, CommissionRepo, UserRepo, MerchantRepo

log = logging.getLogger(__name__)

class FondyApiWrapper:

    order_url = 'https://pay.fondy.eu/api/checkout/url/'
    check_url = 'https://pay.fondy.eu/api/status/order_id'
    capture_url = 'https://pay.fondy.eu/api/capture/order_id'

    def __init__(self, session: sessionmaker):
        self.session = session

    @staticmethod
    def _generate_signature(*values) -> str:
        string = '|'.join([str(m) for m in values])
        print(string)
        s = hashlib.sha1(bytes(string, 'utf-8'))
        return s.hexdigest()

    def pull_signature(self, data: dict, secret_key) -> None:
        keys = list(data['request'].keys())
        keys.sort()
        print(keys)
        signature_args = [secret_key]
        for key in keys:
            signature_args.append(data['request'][key])
        signature = self._generate_signature(*signature_args)
        data['request'].update(signature=signature)
        return data

    @staticmethod
    async def _post(url: str, body: dict) -> dict:
        session = aiohttp.ClientSession(json_serialize=json.dumps)
        async with session.post(url, json=body, headers={'Content-Type': 'application/json'}) as resp:
            result = await resp.json()
        await session.close()
        return result

    async def create_order(self, deal: Deal, need_to_pay: int, reservation_data: str = None):
        session: AsyncSession = self.session()
        order_db = OrderRepo(session)
        commission_db = CommissionRepo(session)
        user_db = UserRepo(session)
        merchant_db = MerchantRepo(session)
        customer = await user_db.get_user(deal.customer_id)
        commission = await commission_db.get_commission(customer.commission_id)
        orders = await order_db.get_orders_deal(deal.deal_id)

        orders_merchants = list(set([order.merchant_id for order in orders]))
        if len(orders_merchants) == 1 and orders_merchants[0] == commission.choose_merchant(deal.price):
            merchant_id = orders_merchants[0]
        else:
            merchant_id = commission.choose_merchant(need_to_pay)
        merchant = await merchant_db.get_merchant(merchant_id)
        order = await order_db.add(deal_id=deal.deal_id, merchant_id=merchant_id)
        # await order_db.create_log(order.id, 'Платіж створено')

        order_desc = (
            f'Сплата за угоду №T{deal.deal_id}'
        )
        need_to_pay *= 100

        data = {
            'request': {
                'order_id': order.order_id,
                'merchant_id': merchant_id,
                'order_desc': order_desc,
                'amount': need_to_pay,
                'currency': 'UAH',
                'merchant_data': f'{deal.deal_id}',
                'preauth': 'Y',
                'lang': 'uk',
            }
        }
        if reservation_data:
            inn = base64.b64encode(('{\n  "receiver_inn": "' + str(reservation_data) + '"\n}').encode('utf-8'))
            data['request'].update(receiver_data=str(inn))
        print(data)
        await order_db.update_order(order.id, request_body=dict(data['request']))
        self.pull_signature(data, merchant.secret_key)
        response = await self._post(self.order_url, data)
        check_response = await self.check_order(order, merchant)
        await order_db.update_order(order.id, request_answer=dict(check_response))
        await session.commit()
        await session.close()
        return response, order

    async def check_order(self, order: OrderRepo.model, merchant: MerchantRepo.model) -> dict:
        data = {
            'request': {
                'order_id': order.request_body['order_id'],
                'merchant_id': order.request_body['merchant_id'],
            }
        }
        self.pull_signature(data, merchant.secret_key)
        return await self._post(self.check_url, data)

    async def reverse_order(self, order: OrderRepo.model, merchant: MerchantRepo.model, comment: str) -> dict:
        session: AsyncSession = self.session()
        order_db = OrderRepo(session)
        data = {
           'request': {
              'order_id': order.order_id,
              'currency': 'UAH',
              'amount': order.request_body['amount'],
              'merchant_id': order.request_body['merchant_id'],
              'comment': comment
           }
        }
        self.pull_signature(data, merchant.secret_key)
        response = await self._post(self.check_url, data)
        await order_db.update_order(order.id, request_reverse=dict(response))
        await session.commit()
        await session.close()
        return response

    async def payout_order(self, order: OrderRepo.model, merchant: MerchantRepo.model, card_number: str):
        session: AsyncSession = self.session()
        order_db = OrderRepo(session)
        # data = {
        #     'request': {
        #         'order_id': order.order_id,
        #         'order_desc': 'Оплата за угоду',
        #         'currency': 'UAH',
        #         'amount': '92784',
        #         'receiver_card_number': card_number,
        #         'merchant_id': merchant.merchant_id
        #       }
        # }
        data = {
            'request': {'order_id': '1703098778',
                        'order_desc': 'Оплата за угоду',
                        'currency': 'UAH',
                        'amount': '92784',
                        'receiver_card_number': '4731185670621553',
                        'merchant_id': 1537378,
                        'signature': 'aa020713b9c872effddcc1a792a1e85dc66807c9'
                        }
        }
        self.pull_signature(data, 'jfZ2fG73cU5RtTpcMQUtmvauhREd8Jg4')
        log.info(data)
        response = await self._post('https://pay.fondy.eu/api/p2pcredit/', data)
        log.info(response)
        # await order_db.update_order(order.id, request_reverse=dict(response))

    async def make_capture(self, order: Order, merchant: MerchantRepo.model) -> dict:
        """
        :return: json

        API documentation:  https://docs.fondy.eu/ru/docs/page/12
        """
        data = {
            'request': {
                'order_id': order.request_body['order_id'],
                'merchant_id': order.request_body['merchant_id'],
                'amount': order.request_body['amount'],
                'currency': order.request_body['currency']
            }
        }
        self.pull_signature(data, merchant.secret_key)
        return await self._post(self.capture_url, data)
