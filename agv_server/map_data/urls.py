from django.urls import path
from .views import (
    ImportConnectionsAPIView,
    ImportDirectionsAPIView,
    MapDataAPIView,
    DeleteMapDataAPIView,
    MapStatisticsAPIView,
)

urlpatterns = [
    path(
        "import-connections/",
        ImportConnectionsAPIView.as_view(),
        name="import-connections",
    ),
    path(
        "import-directions/",
        ImportDirectionsAPIView.as_view(),
        name="import-directions",
    ),
    path("get/", MapDataAPIView.as_view(), name="get-map-data"),
    path("delete/", DeleteMapDataAPIView.as_view(), name="delete-all-map-data"),
    path("statistics/", MapStatisticsAPIView.as_view(), name="map-statistics"),
]
