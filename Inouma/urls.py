"""
URL configuration for Inouma project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from Inouma import views
from django.views.generic import RedirectView
from django.urls import reverse_lazy

urlpatterns = [
    path('home', views.machine_directory, name='machine_directory'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('reservations/', views.my_reservations, name='my_reservations'),
    path('admin/', admin.site.urls),
    # Mount account-related routes under /auth/
    path('auth/', include('accounts.urls')),
<<<<<<< Updated upstream
    # Home / landing page
    # Make root redirect to the auth sign-in page (HTML login)
    path('', RedirectView.as_view(url=reverse_lazy('login')), name='landing'),
=======
    path('', include('machines.urls')),
    path('staff/locations/', include('locations.urls')),
    path('', include('machines.urls')),
>>>>>>> Stashed changes
]


# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATICFILES_DIRS[0])
