from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Public URLs
    path('', views.PostListView.as_view(), name='post_list'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    
    # Management URLs
    path('manage/', views.manage_post_list, name='manage_post_list'),
    path('manage/analytics/', views.manage_blog_analytics, name='manage_blog_analytics'),
    path('track-reading/', views.track_reading, name='track_reading'),
    path('manage/create/', views.ManagePostCreateView.as_view(), name='manage_post_create'),
    path('manage/<int:pk>/edit/', views.ManagePostUpdateView.as_view(), name='manage_post_edit'),
    path('manage/<int:pk>/delete/', views.ManagePostDeleteView.as_view(), name='manage_post_delete'),
    
    # API endpoints
    path('api/upload_image/', views.upload_image, name='upload_image'),
]
