from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("home/", views.home_page, name="home"),
    path("starttestpage/", views.starttestpage, name="starttestpage"),
    path("logout/", views.logout, name="logout"),
    path("showquestions/", views.showquestions, name="showquestions"),
    path("question/<int:question_number>/", views.questions, name="questions"),
    path('convert_audio/', views.convert_audio, name='convert_audio'),
    path('get_next_question/', views.get_next_question, name='get_next_question'),
    path('scorepage/', views.scorepage, name='scorepage'),
    path('analysis/', views.analysis, name='analyse'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)