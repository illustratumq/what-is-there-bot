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
        verbose_name = 'юзер'
        verbose_name_plural = 'юзери'

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


class BaseForm(ModelForm):
    class Meta:
        fields = '__all__'

        widgets = {
            'description': Textarea(attrs={'cols': 100, 'rows': 5}),
            'ban_comment': Textarea(attrs={'cols': 100, 'rows': 5})
        }
