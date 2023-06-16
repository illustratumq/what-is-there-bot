from django.db import models

# Create your models here.
from django.forms import ModelForm, Textarea


class TimeBaseModel(models.Model):

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')


class Commission(TimeBaseModel):

    class Meta:
        db_table = 'commissions'
        verbose_name = 'комісійний пакет'
        verbose_name_plural = 'комісійні пакети'

    pack_id = models.BigAutoField(primary_key=True, verbose_name='ID Пакету')
    commission = models.IntegerField(verbose_name='Комісія у відсотках')
    trigger = models.IntegerField(verbose_name='Тригерна ціна, грн')
    under = models.IntegerField(verbose_name='Фікована комісія, грн')
    minimal = models.IntegerField(verbose_name='Мінімальна ціна угоди, грн')
    maximal = models.IntegerField(verbose_name='Максимальна ціна угоди, грн')
    name = models.CharField(max_length=255, verbose_name='Назва пакунку')
    description = models.CharField(max_length=500, verbose_name='Інформація для амдіна')

    def __str__(self):
        return f'{self.name} (ID {self.pack_id})'


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
        ('USER', 'Клієнт'),
        ('MODERATOR', 'Модератор'),
    )

    user_id = models.BigIntegerField(primary_key=True, verbose_name='Телеграм ID')
    full_name = models.CharField(max_length=255, null=False, verbose_name='Ім\'я')
    commission_id = models.ForeignKey(Commission, verbose_name='Комісійний пакунок', null=True, blank=True,
                                      on_delete=models.SET_NULL, db_column='commission_id')
    bankcard = models.CharField(max_length=16, null=True, blank=True, verbose_name='Банківська карта')
    status = models.CharField(choices=UserStatusEnum, null=False, default='UNAUTHORIZED', verbose_name='Статус')
    type = models.CharField(choices=UserTypeEnum, null=False, default='USER', verbose_name='Права')
    balance = models.BigIntegerField(default=0, verbose_name='Баланс')
    description = models.CharField(max_length=500, verbose_name='Про себе', null=True, blank=True)
    ban_comment = models.CharField(max_length=500, verbose_name='Причина бану', null=True, blank=True)
    time = models.CharField(max_length=10, null=False, default='*', verbose_name='Дозволені години')

    def __str__(self):
        return f'{self.full_name} ({self.user_id})'


DealStatusEnum = (
    ('ACTIVE', 'Активний'),
    ('BUSY', 'Виконується'),
    ('DONE', 'Виконаний'),
    ('DISABLED', 'Видалений'),
    ('MODERATE', 'Модерується'),
    ('WAIT', 'Очікує публікації')
)

class Post(TimeBaseModel):

    class Meta:
        db_table = 'posts'
        verbose_name = 'пост'
        verbose_name_plural = 'пости'

    post_id = models.BigAutoField(primary_key=True, verbose_name='Пост Id')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Власник', null=False, db_column='user_id')
    title = models.CharField(max_length=150, null=False, verbose_name='Заголовок')
    about = models.CharField(max_length=800, null=False, verbose_name='Опис')
    price = models.IntegerField(default=0, verbose_name='Ціна поста, грн')
    status = models.CharField(choices=DealStatusEnum, null=False, default='MODERATE', verbose_name='Статус')

    def __str__(self):
        return f'Пост №{self.post_id} ({self.user_id.full_name} {self.user_id.user_id})'

class Deal(TimeBaseModel):

    class Meta:
        db_table = 'deals'
        verbose_name = 'угода'
        verbose_name_plural = 'угоди'

    DealRatingEnum = (
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

    deal_id = models.BigAutoField(primary_key=True, verbose_name='Id угоди')
    post_id = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name='Пост', null=False, db_column='post_id')
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
    # chat_id = sa.Column(sa.BIGINT, sa.ForeignKey('rooms.chat_id', ondelete='SET NULL'), nullable=True)
    # willing_ids = sa.Column(ARRAY(sa.BIGINT), default=[], nullable=False, )

    def __str__(self):
        return f'Угода №{self.deal_id}'


class BaseForm(ModelForm):
    class Meta:
        fields = '__all__'

        widgets = {
            'description': Textarea(attrs={'cols': 100, 'rows': 3}),
            'ban_comment': Textarea(attrs={'cols': 100, 'rows': 3}),
            'about': Textarea(attrs={'cols': 100, 'rows': 3})
        }
