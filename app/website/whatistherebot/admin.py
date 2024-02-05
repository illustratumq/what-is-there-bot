from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import User, Commission, Post, Deal, Room, BaseForm


@admin.action(description='Забанити вибраних юзерів')
def make_banned(modeladmin, request, queryset):
    queryset.update(status='BANNED')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('full_name', 'user_id', 'balance', 'type', 'status', 'updated_at')
    list_filter = ('status', 'type')
    search_fields = ('user_id__startswith', 'full_name__startswith')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-updated_at']
    actions = [make_banned]

    fieldsets = (
        ('Персональна інформація', {
            'fields': ('user_id', 'full_name', 'description')
        }),
        ('Статус користувача', {
            'fields': ('type', 'status')
        }),
        ('Грошові дані', {
            'fields': ('balance',),
        }),
        ('Інше', {
            'fields': ('time', 'ban_comment'),
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

    def has_add_permission(self, request):
        return False

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):

    form = BaseForm
    list_filter = ('status', )
    list_display = ('title', 'price', 'status', 'view_user_link', 'updated_at')
    search_fields = ('title__startswith', 'post_id__startswith')
    readonly_fields = ('created_at', 'updated_at', 'message_id', 'admin_message_id',
                       'reserv_message_id', 'post_url', 'media_url')
    ordering = ['-updated_at']

    def view_user_link(self, obj):
        url = (
                reverse('admin:whatistherebot_user_changelist') + f'{obj.user_id.user_id}/change'
        )
        return format_html('<a href="{}">{}</a>', url, obj.user_id.full_name)

    view_user_link.short_description = 'Власник'

    fieldsets = (
        ('Статус та користувач', {
            'fields': ('user_id', 'status')
        }),
        ('Дані поста', {
            'fields': ('title', 'about', 'price'),
        }),
        ('Посилання поста', {
            'fields': ('post_url', 'media_url')
        }),
        ('Telegram ID повідомлень в каналах', {
            'fields': ('message_id', 'admin_message_id', 'reserv_message_id')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

    def has_add_permission(self, request):
        return False

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):

    form = BaseForm
    list_filter = ('status',)
    list_display = ('__str__',  'status', 'view_post_link', 'view_customer_link', 'view_executor_link', 'updated_at')
    search_fields = ('customer_id__startswith', 'executor_id__startswith', 'deal_id__startswith')
    ordering = ['-updated_at']
    readonly_fields = ('log', 'created_at', 'updated_at')
    autocomplete_fields = ('post_id', 'executor_id', 'customer_id', 'chat_id')

    def view_post_link(self, obj):
        url = (
                reverse('admin:whatistherebot_post_changelist') + f'{obj.post_id.post_id}/change'
        )
        return format_html('<a href="{}">{}</a>', url, obj.post_id)

    def view_customer_link(self, obj):
        url = (
                reverse('admin:whatistherebot_user_changelist') + f'{obj.customer_id.user_id}/change'
        )
        return format_html('<a href="{}">{}</a>', url, obj.customer_id.full_name)

    def view_executor_link(self, obj):
        if obj.executor_id:
            url = (
                    reverse('admin:whatistherebot_user_changelist') + f'{obj.executor_id.user_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.executor_id.full_name)
        else:
            return 'Немає'

    view_customer_link.short_description = 'Замовник'
    view_executor_link.short_description = 'Виконавець'
    view_post_link.short_description = 'Пост'

    fieldsets = (
        ('Дані про угоду', {
            'fields': ('log', 'price', 'payed', 'status'),
        }),
        ('Учасники', {
            'fields': ('post_id', 'customer_id', 'executor_id', 'chat_id'),
        }),
        ('Оцінка', {
            'fields': ('rating', 'comment')
        }),
        ('Активність у чаті', {
            'fields': ('activity_confirm', 'next_activity_date')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

    def has_add_permission(self, request):
        return False


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('name', 'commission_id', 'updated_at')
    search_fields = ('name__startswith',)
    readonly_fields = ('created_at', 'updated_at', 'merchant_1', 'merchant_2', 'merchant_3')
    ordering = ['-updated_at']

    fieldsets = (
        ('Про пакунок', {
            'fields': ('name', 'description')
        }),
        ('Цінові параметри', {
            'fields': ('trigger_price_1', 'trigger_price_2', 'minimal', 'maximal')
        }),
        ('Мерчанти', {
            'fields': ('merchant_1', 'merchant_2', 'merchant_3')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('name', 'chat_id', 'status', 'updated_at')
    search_fields = ('name__startswith', 'chat_id__startswith')
    readonly_fields = ('created_at', 'updated_at', 'chat_id')
    ordering = ['-updated_at']

    def has_add_permission(self, request):
        return False

    fieldsets = (
        ('Телеграм дані', {
            'fields': ('chat_id', 'name', 'invite_link', 'status')
        }),
        ('Модерація в чаті', {
            'fields': ('admin_required', 'admin_id', 'reason'),
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )