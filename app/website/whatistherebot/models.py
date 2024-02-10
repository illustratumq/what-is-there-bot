import json

from aiogram.utils.markdown import hide_link
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ModelForm, Textarea
from telebot import TeleBot

from app.config import Config


class TimeBaseModel(models.Model):

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата останнього оновлення')


class Merchant(TimeBaseModel):

    class Meta:
        db_table = 'merchants'
        verbose_name = 'мерчанти'
        verbose_name_plural = 'мерчанти'

    merchant_id = models.BigAutoField(primary_key=True, verbose_name='ID мерчанта')
    secret_key = models.CharField(verbose_name='Ключ транзакцій', editable=False)
    p2p_key = models.CharField(verbose_name='Ключ P2P транзакцій', editable=False)
    percent = models.FloatField(verbose_name='Відсоток на комісію')
    name =  models.CharField(verbose_name='Назва мерчанту')


class Commission(TimeBaseModel):

    class Meta:
        db_table = 'commissions'
        verbose_name = 'комісійний пакет'
        verbose_name_plural = 'комісійні пакети'

    commission_id = models.BigAutoField(primary_key=True, verbose_name='ID Пакету', db_column='commission_id')
    name = models.CharField(max_length=255, verbose_name='Назва пакунку')
    description = models.CharField(max_length=500, verbose_name='Інформація для амдіна', null=True, blank=True)
    minimal = models.IntegerField(verbose_name='Мінімальна ціна угоди, грн')
    maximal = models.IntegerField(verbose_name='Максимальна ціна угоди, грн')
    trigger_price_1 = models.IntegerField(verbose_name='Максимальна ціна першого мерчанта, грн')
    trigger_price_2 = models.IntegerField(verbose_name='Максимальна ціна другого мерчанта, грн')
    merchant_1 = models.ForeignKey(Merchant, verbose_name='Мерчант №1',
                                   on_delete=models.SET_NULL, null=True,
                                   db_column='merchant_1', related_name='merchant_1')
    merchant_2 = models.ForeignKey(Merchant, verbose_name='Мерчант №2', on_delete=models.SET_NULL,
                                   null=True, db_column='merchant_2', related_name='merchant_2')
    merchant_3 = models.ForeignKey(Merchant, verbose_name='Мерчант №3', on_delete=models.SET_NULL,
                                   null=True, db_column='merchant_3', related_name='merchant_3')

    def __str__(self):
        return f'{self.name}'


class User(TimeBaseModel):

    class Meta:
        db_table = 'users'
        verbose_name = 'користувач'
        verbose_name_plural = 'користувачі'

    UserStatusEnum = (
        ('ACTIVE', 'Активний'),
        ('BANNED', 'Забанений')
    )

    UserTypeEnum = (
        ('ADMIN', 'Адмін'),
        ('USER', 'Користувач'),
        ('MODERATOR', 'Модератор'),
    )

    user_id = models.BigIntegerField(primary_key=True, verbose_name='Телеграм ID')
    full_name = models.CharField(max_length=255, null=False, verbose_name='Ім\'я')
    bankcard = models.CharField(max_length=16, null=True, blank=True, verbose_name='Банківська карта')
    status = models.CharField(choices=UserStatusEnum, null=False, default='UNAUTHORIZED', verbose_name='Статус')
    type = models.CharField(choices=UserTypeEnum, null=False, default='USER', verbose_name='Права')
    balance = models.BigIntegerField(default=0, verbose_name='Баланс')
    description = models.CharField(max_length=500, verbose_name='Про себе', null=True, blank=True)
    ban_comment = models.CharField(max_length=500, verbose_name='Причина бану', null=True, blank=True)
    time = models.CharField(max_length=10, null=False, default='*', verbose_name='Години сповіщень')

    def __str__(self):
        return f'{self.full_name} ({self.user_id})'


class Post(TimeBaseModel):

    class Meta:
        db_table = 'posts'
        verbose_name = 'пост'
        verbose_name_plural = 'пости'

    PostStatusEnum = (
        ('ACTIVE', 'Активний'),
        ('BUSY', 'Зайнятий в угоді'),
        ('DONE', 'Завершений'),
        ('DISABLED', 'Відхилений адміністратором'),
        ('MODERATE', 'Очікує схвалення адміністратором'),
        ('WAIT', 'Очікує публікації в черзі')
    )

    post_id = models.BigAutoField(primary_key=True, verbose_name='Пост Id')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Власник', null=False, db_column='user_id')
    title = models.CharField(max_length=150, null=False, verbose_name='Заголовок')
    about = models.CharField(max_length=800, null=False, verbose_name='Опис')
    price = models.IntegerField(default=0, verbose_name='Ціна поста, грн')
    status = models.CharField(choices=PostStatusEnum, null=False, default='MODERATE', verbose_name='Статус')
    message_id = models.BigIntegerField(null=True, blank=True, verbose_name='Повідомлення в основному каналі')
    admin_message_id = models.BigIntegerField(null=True, blank=True, verbose_name='Повідомлення в адмін каналі')
    reserv_message_id = models.BigIntegerField(null=True, blank=True, verbose_name='Повідомлення в резервному каналі')
    post_url = models.CharField(max_length=150, null=True, blank=True, verbose_name='Посилання на пост')
    media_url = models.CharField(max_length=150, null=True, blank=True, verbose_name='Посилання на медіа')

    def delete(self, *args, **kwargs):
        if self.status != 'BUSY':
            config = Config.from_env()
            bot = TeleBot(config.bot.token)
            if self.message_id:
                bot.delete_message(
                    chat_id=config.misc.post_channel_chat_id, message_id=self.message_id
                )
            if self.reserv_message_id:
                bot.delete_message(
                    chat_id=config.misc.reserv_channel_id, message_id=self.reserv_message_id
                )
            if self.admin_message_id:
                bot.delete_message(
                    chat_id=config.misc.admin_channel_id, message_id=self.admin_message_id
                )
            bot.send_message(
                self.user_id.user_id, f'Ваш пост {self.title}{hide_link(self.media_url)} було видалено адміністратором',
                parse_mode='HTML'
            )
            return super(Post, self).delete()
        else:
            raise ValidationError('Цей пост неможливо видалити, оскільки він є зайнятим в угоді')

    # def save(self, *args, **kwargs):
    #     if self.status != 'BUSY':
    #         model = Post.objects.filter(post_id=self.post_id)[0]
    #         if any([self.title != model.title, self.about != model.about, self.price != model.price]):
    #             config = Config.from_env()
    #             bot = TeleBot(config.bot.token)

    def __str__(self):
        return f'Пост №{self.post_id}'


class Room(TimeBaseModel):

    class Meta:
        db_table = 'rooms'
        verbose_name = 'чат'
        verbose_name_plural = 'чати'

    RoomStatusEnum = (
        ('AVAILABLE', 'Вільний'),
        ('BUSY', 'Зайнятий')
    )

    AdminRequiredEnum = (
        (True, 'Потрібна'),
        (False, 'Не потрібна')
    )

    chat_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    invite_link = models.CharField(max_length=150, unique=True, verbose_name='Запрошувальне посилання')
    status = models.CharField(choices=RoomStatusEnum, default='AVAILABLE', null=False, verbose_name='Статус чату')
    admin_required = models.BooleanField(default=False, choices=AdminRequiredEnum, verbose_name='Допомога в чаті')
    admin_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Адмін чату',
                                 db_column='admin_id')
    reason = models.CharField(max_length=150, null=True, blank=True, verbose_name='Причина')

class Deal(TimeBaseModel):

    class Meta:
        db_table = 'deals'
        verbose_name = 'угода'
        verbose_name_plural = 'угоди'

    DealRatingEnum = (
        (None, 'Немає'),
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
        (5, '5')
    )

    RoomActivityEnum = (
        (True, 'Підтверджена'),
        (False, 'Не підтверджена')
    )

    DealStatusEnum = (
        ('ACTIVE', 'Активна'),
        ('BUSY', 'Виконується в чаті'),
        ('DONE', 'Завершена'),
        ('DISABLED', 'Відхилена адміністратором'),
        ('MODERATE', 'Очікує схвалення поста'),
        ('WAIT', 'Очікує публікації поста')
    )

    deal_id = models.BigAutoField(primary_key=True, verbose_name='Id угоди')
    post_id = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name='Пост', null=False, db_column='post_id')
    chat_id = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Чат угоди',
                                db_column='chat_id')
    customer_id = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Замовник',
                                    null=False, db_column='customer_id', related_name='customer_id')
    executor_id = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Виконавець',
                                    null=True, db_column='executor_id', related_name='executor_id', blank=True)
    price = models.IntegerField(default=0, verbose_name='Ціна угоди, грн')
    payed = models.IntegerField(default=0, verbose_name='Оплачено, грн')
    status = models.CharField(choices=DealStatusEnum, verbose_name='Статус', default='MODERATE')
    rating = models.IntegerField(choices=DealRatingEnum, verbose_name='Рейтингова оцінка', null=True, blank=True)
    comment = models.CharField(max_length=500, verbose_name='Відгук', null=True, blank=True)
    next_activity_date = models.DateTimeField(verbose_name='Дата перевірки активності', null=True, blank=True,
                                              help_text='*Визначається автоматично')
    activity_confirm = models.BooleanField(choices=RoomActivityEnum, verbose_name='Підтвердження активності',
                                           default=True)
    log = models.CharField(verbose_name='Історія угоди', null=True, editable=False)

    def __str__(self):
        return f'Угода №{self.deal_id}'

class CustomJsonField(models.JSONField):
    def from_db_value(self, value, expression, connection):
        if isinstance(value, dict):
            return value
        return super().from_db_value(value, expression, connection)

class Order(TimeBaseModel):

    class Meta:
        db_table = 'orders'
        verbose_name = 'платежі'
        verbose_name_plural = 'платежі'

    OrderTypeEnum = (
        ('ORDER', 'ОПЛАТА'),
        ('CAPTURE', 'CAPTURE'),
        ('REVERSE', 'ПОВЕРНЕНЯ'),
        ('PAYOUT', 'ВИПЛАТА'),
    )

    OrderStatus = (
        (True, 'Завершений'),
        (False, 'Незавершений')
    )

    id = models.BigAutoField(primary_key=True, verbose_name='Номер платежу')
    type = models.CharField(choices=OrderTypeEnum, verbose_name='Тип', default='ORDER')
    deal_id = models.ForeignKey(Deal, on_delete=models.SET_NULL, verbose_name='Угода',
                                null=True, db_column='deal_id')
    url = models.CharField(null=False, verbose_name='URL платежу', editable=False)
    request_body = CustomJsonField(verbose_name='Тіло запиту', editable=False)
    request_answer = CustomJsonField(verbose_name='Тіло відповіді', editable=False)
    log = models.CharField(verbose_name='Історія платежу', null=True, editable=False)
    payed = models.BooleanField(verbose_name='Статус платежу', choices=OrderStatus)
    merchant_id = models.ForeignKey(Merchant, on_delete=models.SET_NULL, verbose_name='Мерчант',
                      null=True, db_column='merchant_id', editable=False)


    @property
    def order_id(self):
        return str(int(self.created_at.timestamp()) + self.deal_id * self.id * int(self.created_at.microsecond / 10e3))
    # merchant_id = sa.Column(sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)

class BaseForm(ModelForm):
    class Meta:
        fields = '__all__'

        widgets = {
            'description': Textarea(attrs={'cols': 41, 'rows': 3}),
            'ban_comment': Textarea(attrs={'cols': 41, 'rows': 3}),
            'comment': Textarea(attrs={'cols': 60, 'rows': 7}),
            'about': Textarea(attrs={'cols': 60, 'rows': 7}),
            'title': Textarea(attrs={'cols': 60, 'rows': 1}),
        }
