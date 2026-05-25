from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # Added for language switching
    path('sales_chat_api/', views.sales_chat_api, name='sales_chat_api'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('auth/', include('accounts.urls')),
    path('analytics/', include('analytics.urls')),
    path('management/', include('management.urls')),
    path('blog/', include('blog.urls')),
    path('', views.home, name='home'),
    path('landing/', views.home, name='landing'),
    path('features/', views.features, name='features'),
    path('roadmap/', views.roadmap, name='roadmap'),
    path('docs/', views.docs, name='docs'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
