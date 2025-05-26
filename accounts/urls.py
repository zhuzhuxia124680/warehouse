from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'
urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/done/', views.RegisterDoneView.as_view(), name='register-done'),
    path('verify/', views.VerifyEmailWithEmailView.as_view(), name='verify_email_with_email'),
    path('verify/resend/', views.ResendVerificationCodeView.as_view(), name='resend_verification_code'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/code/', views.LoginByCodeView.as_view(), name='login_by_code'),
    path('login/code/request/', views.RequestLoginCodeView.as_view(), name='request_login_code'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]