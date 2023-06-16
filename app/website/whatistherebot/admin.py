from django.contrib import admin
from .models import User, Commission, Post, Deal, BaseForm


@admin.action(description='Забанити вибраних юзерів')
def make_banned(modeladmin, request, queryset):
    queryset.update(status='BANNED')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('full_name', 'user_id', 'balance', 'type', 'status', 'updated_at')
    list_filter = ('status', 'type')
    search_fields = ('user_id__startswith', 'full_name__startswith')
    ordering = ['-updated_at']
    actions = [make_banned]
    autocomplete_fields = ('commission_id',)

    fieldsets = (
        ('Персональна інформація', {
            'fields': ('user_id', 'full_name', 'description')
        }),
        ('Сервісна інформація про клієнта', {
            'fields': ('bankcard', 'balance', 'commission_id', 'type', 'status'),
        }),
        ('Інше', {
            'fields': ('time', 'ban_comment'),
        }),
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('__str__', 'price', 'status', 'user_id', 'updated_at')
    search_fields = ('user__startswith', 'post_id__startswith')
    ordering = ['-updated_at']

    fieldsets = (
        ('Статус та користувач', {
            'fields': ('user_id', 'status')
        }),
        ('Дані поста', {
            'fields': ('title', 'about', 'price'),
        })
    )

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('__str__', 'price', 'status', 'updated_at')
    search_fields = ('customer_id__startswith', 'executor_id__startswith', 'deal_id__startswith')
    ordering = ['-updated_at']

    fieldsets = (
        ('Прив\'язаність', {
            'fields': ('post_id', 'customer_id', 'executor_id')
        }),
        ('Статус та ціна', {
            'fields': ('price', 'payed', 'status'),
        }),
        ('Оцінка', {
            'fields': ('rating', 'comment')
        }),
        ('Активність у чаті', {
            'fields': ('next_activity_date', 'activity_confirm')
        })
    )


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):

    list_display = ('name', 'pack_id', 'commission', 'updated_at')
    search_fields = ('name__startswith', 'pack_id__startswith')
    ordering = ['-updated_at']

    fieldsets = (
        ('Про пакунок', {
            'fields': ('name', 'description')
        }),
        ('Цінові параметри', {
            'fields': ('trigger', 'under', 'commission', 'minimal', 'maximal'),
        })
    )
