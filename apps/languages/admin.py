from django.contrib import admin

from .models import Lengua


@admin.register(Lengua)
class LenguaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo")
    search_fields = ("nombre", "codigo")
