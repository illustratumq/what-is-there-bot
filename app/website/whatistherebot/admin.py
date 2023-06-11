from django.contrib import admin
from .models import User, Commission, BaseForm


@admin.action(description='Забанити вибраних юзерів')
def make_banned(modeladmin, request, queryset):
    queryset.update(status='BANNED')


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
