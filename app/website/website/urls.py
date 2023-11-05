from django.contrib import admin
from django.urls import path

from app.website.website.view import CustomAdminView

admin.site.site_header = 'Enter Admin'
admin.site.index_title = 'Головне меню'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('statistic/', CustomAdminView.as_view())
]
