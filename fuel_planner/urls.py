from django.urls import path
from .views import route_fuel_api_view, map_interface_view

urlpatterns = [
    path('', map_interface_view, name='map_interface'),
    path('api/route/', route_fuel_api_view, name='route_fuel_api'),
]
