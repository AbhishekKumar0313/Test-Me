from django.contrib import admin
from .models import UserDetails, CollectedData
# Register your models here.
admin.site.register(UserDetails)
admin.site.register(CollectedData)