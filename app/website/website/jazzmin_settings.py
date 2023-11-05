
JAZZMIN_SETTINGS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    'show_sidebar': True,
    "sidebar": "sidebar-dark-primary",
    "theme": "default",
    "dark_mode_theme": "cyborg",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "topmenu_links": [
        {
            "name": "Головна",
            "url": "admin:index",
            "new_window": False,
        },
        {'model': 'auth.User'},
        {
            "name": 'Статистика',
            'url': "/statistic/",
            'new_window': False
        }
    ]
}