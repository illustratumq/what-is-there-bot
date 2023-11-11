from django.shortcuts import render
from django.views import View

class CustomAdminView(View):
    template_name = "test.html"  # Вказуємо шлях до шаблону

    def get(self, request):
        # Тут ви можете зробити обчислення або отримати дані для відображення на сторінці
        context = {
            'data': 'Це ваші дані для відображення на сторінці',
        }
        return render(request, self.template_name, context)
