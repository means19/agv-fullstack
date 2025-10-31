from django.urls import path
from .views import (
    CreateAGVView,
    CreateAGVsViaCSVView,
    ListAGVsView,
    DeleteAGVView,
    BulkDeleteAGVsView,
    DispatchOrdersToAGVsView,
    ResetAGVsView,
    GodotReportLocationView
)

urlpatterns = [
    path("get/", ListAGVsView.as_view(), name="list_agvs"),
    path("create/", CreateAGVView.as_view(), name="create_agv"),
    path("create-via-csv/", CreateAGVsViaCSVView.as_view(), name="create_agvs_via_csv"),
    path("delete/<int:agv_id>/", DeleteAGVView.as_view(), name="delete_agv"),
    path("bulk-delete/", BulkDeleteAGVsView.as_view(), name="bulk_delete_agvs"),
    path("reset/", ResetAGVsView.as_view(), name="reset_agvs"),
    path('simulation/report_location/', GodotReportLocationView.as_view(), name='godot_report_location'),
    path(
        "dispatch-orders-to-agvs/",
        DispatchOrdersToAGVsView.as_view(),
        name="dispatch_orders_to_agvs",
    ),
]
