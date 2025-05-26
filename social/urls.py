from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('', views.FriendListView.as_view(), name='friend_list'),
    path('friend/<int:friend_id>/', views.FriendProfileView.as_view(), name='friend_profile'),
    # 所有功能都已整合到FriendListView中
]