
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from account import views
from plant import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index , name="index"),
    path('account/',include('account.urls')),
    path('product/',include('product.urls')),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns+=static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
