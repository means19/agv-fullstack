from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from .models import Agv
from .serializers import AGVSerializer
from django.db import transaction
import schedule
import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import csv
import io
from rest_framework.parsers import MultiPartParser, FormParser
from .apply_main_algorithms.apply_main_algorithms import process_agv_report # <-- Import hàm adapter


def send_order_assignment_notification(order_id, agv_id, message, additional_data=None):
    """
    Send order assignment notification through WebSocket.

    Args:
        order_id: The ID of the assigned order
        agv_id: The ID of the AGV that received the order
        message: The notification message to display
        additional_data: Additional data to include in the notification (optional)
    """
    try:
        # Get AGV details for enhanced notification
        agv_data = {}
        try:
            from .models import Agv

            agv = Agv.objects.get(agv_id=agv_id)
            agv_data = {
                "current_node": agv.current_node,
                "common_nodes_count": len(agv.common_nodes) if agv.common_nodes else 0,
                "adjacent_common_nodes_count": len(agv.adjacent_common_nodes)
                if agv.adjacent_common_nodes
                else 0,
                "remaining_path_length": len(agv.remaining_path)
                if agv.remaining_path
                else 0,
            }
        except Exception as e:
            print(f"Error getting AGV details for notification: {str(e)}")

        notification_data = {
            "type": "order_assignment_notification",
            "data": {
                "order_id": order_id,
                "agv_id": agv_id,
                "message": message,
                "timestamp": datetime.datetime.now().isoformat(),
                "agv_details": agv_data,
            },
        }

        # Add any additional data if provided
        if additional_data:
            notification_data["data"].update(additional_data)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "agv_group", {"type": "agv_message", "message": notification_data}
        )
    except Exception as e:
        print(f"Error sending order assignment notification: {str(e)}")


class ListAGVsView(ListAPIView):
    queryset = Agv.objects.all()
    serializer_class = AGVSerializer


class CreateAGVView(APIView):
    def post(self, request):
        if isinstance(request.data, list):
            # Handle multiple objects
            serializer = AGVSerializer(data=request.data, many=True)
        else:
            # Handle single object
            serializer = AGVSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteAGVView(APIView):
    def delete(self, request, agv_id):
        try:
            agv = Agv.objects.get(agv_id=agv_id)
            agv.delete()
            return Response(
                {"message": f"AGV {agv_id} deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except Agv.DoesNotExist:
            return Response(
                {"error": f"AGV {agv_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )


class BulkDeleteAGVsView(APIView):
    def delete(self, request):
        try:
            agv_ids = request.data.get("agv_ids", [])
            if not agv_ids:
                return Response(
                    {"error": "No AGV IDs provided for deletion."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            deleted_count, _ = Agv.objects.filter(agv_id__in=agv_ids).delete()
            return Response(
                {"message": f"{deleted_count} AGVs deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred during bulk deletion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DispatchOrdersToAGVsView(APIView):
    """
    API endpoint to schedule orders to be assigned to available AGVs at their specified times.
    This replaces the functionality previously in the schedule_generate app.
    """

    def __init__(self):
        super().__init__()
        from .main_algorithms.algorithm1.algorithm1 import TaskDispatcher

        self.task_dispatcher = TaskDispatcher()

    def post(self, request):
        """
        Schedule orders to be assigned to idle AGVs at their specified start_time and order_date.

        Returns:
            Response: Information about scheduled orders.
        """
        try:  # Get the algorithm parameter (defaults to dijkstra)
            algorithm = request.data.get("algorithm", "dijkstra")

            # Get all unassigned orders with their scheduling information
            unassigned_orders = self.task_dispatcher.get_unassigned_orders()

            if not unassigned_orders.exists():
                return self._create_no_orders_response()

            # Clear any existing scheduled jobs to avoid duplicates
            schedule.clear()

            # Process orders for scheduling or immediate assignment
            scheduled_orders, immediate_orders = (
                self.task_dispatcher.process_orders_for_scheduling(algorithm)
            )

            # Start scheduler if needed
            # Recalculate common nodes for all active AGVs after immediate assignments
            self.task_dispatcher.start_scheduler_if_needed(scheduled_orders)
            if immediate_orders:
                try:
                    from .main_algorithms.algorithm1.common_nodes import (
                        recalculate_all_common_nodes,
                    )

                    recalculate_all_common_nodes(log_summary=True)
                    print(
                        f"Recalculated common nodes for all AGVs after {len(immediate_orders)} immediate assignments"
                    )
                except Exception as e:
                    print(
                        f"Error recalculating common nodes after immediate assignments: {str(e)}"
                    )

            return self._create_success_response(scheduled_orders, immediate_orders)

        except Exception as e:
            return self._create_error_response(e)

    def _create_no_orders_response(self):
        """Create response for when no unassigned orders are available."""
        return Response(
            {
                "success": False,
                "message": "No unassigned orders available to schedule.",
            },
            status=status.HTTP_200_OK,
        )

    def _create_success_response(self, scheduled_orders, immediate_orders):
        """Create success response with order scheduling results."""
        total_processed = len(scheduled_orders) + len(immediate_orders)

        return Response(
            {
                "success": True,
                "message": f"Successfully scheduled {len(scheduled_orders)} orders and immediately assigned {len(immediate_orders)} orders",
                "scheduled_orders": scheduled_orders,
                "immediate_orders": immediate_orders,
                "total_processed": total_processed,
            },
            status=status.HTTP_200_OK,
        )

    def _create_error_response(self, exception):
        """Create error response with exception details."""
        import traceback

        traceback_str = traceback.format_exc()

        return Response(
            {
                "success": False,
                "message": f"Error scheduling orders: {str(exception)}",
                "details": traceback_str,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ResetAGVsView(APIView):
    """
    API endpoint to reset all fields of all AGV records to their default values,
    except for agv_id and preferred_parking_node.
    """

    @transaction.atomic
    def post(self, request):
        try:
            # Get all AGVs
            agvs = Agv.objects.all()

            if not agvs.exists():
                return Response(
                    {"success": False, "message": "No AGVs found to reset."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            reset_count = 0

            # Reset each AGV
            for agv in agvs:
                # Reset all state fields
                agv.current_node = None
                agv.next_node = None
                agv.reserved_node = None
                agv.motion_state = Agv.IDLE
                agv.spare_flag = False
                agv.backup_nodes = {}
                agv.initial_path = []
                agv.remaining_path = []
                agv.common_nodes = []
                agv.adjacent_common_nodes = []
                agv.active_order = None
                agv.previous_node = None
                agv.direction_change = Agv.GO_STRAIGHT

                # Save the changes
                agv.save(
                    update_fields=[
                        "current_node",
                        "next_node",
                        "reserved_node",
                        "motion_state",
                        "spare_flag",
                        "backup_nodes",
                        "initial_path",
                        "remaining_path",
                        "common_nodes",
                        "adjacent_common_nodes",
                        "active_order",
                        "previous_node",
                        "direction_change",
                    ]
                )

                reset_count += 1

            return Response(
                {
                    "success": True,
                    "message": f"Successfully reset {reset_count} AGVs to their default state.",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            import traceback

            traceback_str = traceback.format_exc()
            return Response(
                {
                    "success": False,
                    "message": f"Error resetting AGVs: {str(e)}",
                    "details": traceback_str,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateAGVsViaCSVView(APIView):
    """
    API endpoint to create multiple AGVs from a CSV file.
    Expected CSV format: agv_id,preferred_parking_node
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            # Check if CSV file is provided
            if "csv_file" not in request.FILES:
                return Response(
                    {
                        "error": "No CSV file provided. Please upload a file with the key 'csv_file'."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            csv_file = request.FILES["csv_file"]

            # Validate file extension
            if not csv_file.name.lower().endswith(".csv"):
                return Response(
                    {"error": "File must be a CSV file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Read and parse CSV file
            try:
                file_content = csv_file.read().decode("utf-8")
                csv_reader = csv.DictReader(io.StringIO(file_content))

                # Validate CSV headers
                expected_headers = {"agv_id", "preferred_parking_node"}
                actual_headers = (
                    set(csv_reader.fieldnames) if csv_reader.fieldnames else set()
                )

                if not expected_headers.issubset(actual_headers):
                    missing_headers = expected_headers - actual_headers
                    return Response(
                        {
                            "error": f"CSV file is missing required headers: {', '.join(missing_headers)}. "
                            f"Expected headers: agv_id, preferred_parking_node"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Parse CSV rows and prepare data for AGV creation
                agv_data_list = []
                row_number = 1  # Start from 1 since header is row 0

                for row in csv_reader:
                    row_number += 1

                    # Skip empty rows
                    if not any(row.values()):
                        continue

                    # Validate and clean data
                    try:
                        agv_id = int(row["agv_id"])
                        preferred_parking_node = (
                            int(row["preferred_parking_node"])
                            if row["preferred_parking_node"].strip()
                            else None
                        )
                    except ValueError as e:
                        return Response(
                            {
                                "error": f"Invalid data in row {row_number}: {str(e)}. "
                                f"agv_id and preferred_parking_node must be integers."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Check for duplicate AGV IDs in the CSV
                    if any(agv_data["agv_id"] == agv_id for agv_data in agv_data_list):
                        return Response(
                            {
                                "error": f"Duplicate agv_id {agv_id} found in row {row_number}. "
                                f"Each AGV ID must be unique."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    agv_data_list.append(
                        {
                            "agv_id": agv_id,
                            "preferred_parking_node": preferred_parking_node,
                        }
                    )

                if not agv_data_list:
                    return Response(
                        {"error": "No valid data rows found in the CSV file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except Exception as e:
                return Response(
                    {"error": f"Error reading CSV file: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check for existing AGV IDs in database
            existing_agv_ids = list(
                Agv.objects.filter(
                    agv_id__in=[agv_data["agv_id"] for agv_data in agv_data_list]
                ).values_list("agv_id", flat=True)
            )

            if existing_agv_ids:
                return Response(
                    {
                        "error": f"AGVs with the following IDs already exist: {', '.join(map(str, existing_agv_ids))}. "
                        f"Please use unique AGV IDs."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create AGVs using the existing serializer
            with transaction.atomic():
                serializer = AGVSerializer(data=agv_data_list, many=True)

                if serializer.is_valid():
                    created_agvs = serializer.save()

                    return Response(
                        {
                            "success": True,
                            "message": f"Successfully created {len(created_agvs)} AGVs from CSV file.",
                            "created_agvs": AGVSerializer(created_agvs, many=True).data,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {
                            "error": "Validation failed for AGV data.",
                            "details": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        except Exception as e:
            import traceback

            traceback_str = traceback.format_exc()
            return Response(
                {
                    "error": f"An unexpected error occurred: {str(e)}",
                    "details": traceback_str,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
class GodotReportLocationView(APIView):
    """
    API endpoint cho Godot simulation (Digital Twin) báo cáo vị trí
    và nhận chỉ thị tiếp theo.
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        agv_id = data.get("agv_id")
        current_node = data.get("current_node")

        if not agv_id or current_node is None:
            return Response(
                {"error": "agv_id và current_node là bắt buộc"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Gọi hàm "adapter" lõi (giống hệt MQTT)
        all_affected_agvs = process_agv_report(
            agv_id=int(agv_id),
            current_node=int(current_node)
        )

        # 2. Tìm AGV GỐC (Godot) để trả về phản hồi
        this_agv = None
        for agv in all_affected_agvs:
            if agv.agv_id == int(agv_id):
                this_agv = agv
                break

        # 3. Xây dựng và trả về phản hồi JSON cho Godot
        if this_agv:
            # Xây dựng phản hồi dựa trên 'encode_message' của bạn
            response_dict = {
                "motion_state": this_agv.motion_state,
                "reserved_node": this_agv.reserved_node,
                "direction_change": this_agv.direction_change,
                # Thêm các trường khác nếu Godot cần
            }
            return Response(response_dict, status=status.HTTP_200_OK)
        else:
            # Trường hợp AGV không tìm thấy (đã được log bởi process_agv_report)
            return Response(
                {"error": f"Không tìm thấy AGV {agv_id} hoặc không có phản hồi"},
                status=status.HTTP_404_NOT_FOUND
            )




# ==================== Map Layout API Views ====================

class MapLayoutAPIView(APIView):
    """
    Get map layout data for frontend visualization.
    
    Returns nodes (CA, DEPOT, STATION) and edges (LSA) with positions
    and metadata for rendering the map graph.
    
    GET /api/map/layout/
    
    Response format:
    {
        "nodes": [
            {
                "id": "CA-01",
                "name": "CA-01",
                "type": "CA",
                "x": 100,
                "y": 100,
                "status": "ONLINE"
            },
            ...
        ],
        "edges": [
            {
                "id": "LSA_CA01_CA02",
                "name": "LSA_CA01_CA02",
                "from": "CA-01",
                "to": "CA-02",
                "distance_m": 200.0,
                "base_time_sec": 100.0,
                "status": "ONLINE"
            },
            ...
        ],
        "stats": {
            "num_nodes": 11,
            "num_edges": 24,
            "num_ca": 6,
            "num_depot": 2,
            "num_station": 3
        }
    }
    """
    
    def get(self, request, format=None):
        from .models import ResourceAgent
        
        try:
            # Get all nodes (CA, DEPOT, STATION)
            nodes = ResourceAgent.objects.filter(
                resource_type__in=['CA', 'DEPOT', 'STATION']
            ).values('name', 'resource_type', 'pos_x', 'pos_y', 'status')
            
            # Get all edges (LSA)
            edges = ResourceAgent.objects.filter(
                resource_type='LSA',
                from_ca__isnull=False,
                to_ca__isnull=False
            ).select_related('from_ca', 'to_ca').values(
                'name',
                'from_ca__name',
                'to_ca__name',
                'distance_m',
                'base_time_sec',
                'status'
            )
            
            # Format nodes for frontend
            nodes_data = [
                {
                    'id': node['name'],
                    'name': node['name'],
                    'type': node['resource_type'],
                    'x': node['pos_x'],
                    'y': node['pos_y'],
                    'status': node['status']
                }
                for node in nodes
            ]
            
            # Format edges for frontend
            edges_data = [
                {
                    'id': edge['name'],
                    'name': edge['name'],
                    'from': edge['from_ca__name'],
                    'to': edge['to_ca__name'],
                    'distance_m': float(edge['distance_m']),
                    'base_time_sec': float(edge['base_time_sec']),
                    'status': edge['status']
                }
                for edge in edges
            ]
            
            # Calculate statistics
            stats = {
                'num_nodes': len(nodes_data),
                'num_edges': len(edges_data),
                'num_ca': sum(1 for n in nodes_data if n['type'] == 'CA'),
                'num_depot': sum(1 for n in nodes_data if n['type'] == 'DEPOT'),
                'num_station': sum(1 for n in nodes_data if n['type'] == 'STATION'),
            }
            
            return Response({
                'nodes': nodes_data,
                'edges': edges_data,
                'stats': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            return Response(
                {
                    'error': f'Error retrieving map layout: {str(e)}',
                    'details': traceback_str
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetIdealPathAPIView(APIView):
    """
    Calculate ideal path between two nodes using MapService.
    
    GET /api/map/path/?start=CA-01&end=STATION-A&speed=1.5
    
    Query parameters:
    - start: Starting node name (required)
    - end: Destination node name (required)
    - speed: AGV speed in m/s (optional, default 1.0)
    
    Response format:
    {
        "start": "CA-01",
        "end": "STATION-A",
        "path": [
            {
                "node_name": "CA-01",
                "resource_type": "CA",
                "pos_x": 100,
                "pos_y": 100,
                "distance_m": 200.0,
                "cumulative_distance_m": 200.0,
                "travel_time_sec": 133.33,
                "cumulative_time_sec": 133.33
            },
            ...
        ],
        "total_distance_m": 600.0,
        "total_time_sec": 400.0
    }
    """
    
    def get(self, request, format=None):
        from map_data.services.map_service import MapService
        
        try:
            start_node = request.query_params.get('start')
            end_node = request.query_params.get('end')
            speed = float(request.query_params.get('speed', 1.0))
            
            if not start_node or not end_node:
                return Response(
                    {'error': 'Missing required parameters: start and end'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if speed <= 0:
                return Response(
                    {'error': 'Speed must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use MapService from map_data module
            map_service = MapService()
            path_result = map_service.get_shortest_path(start_node, end_node)
            
            if not path_result['success']:
                return Response(
                    {'error': path_result.get('message', 'Failed to find path')},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(path_result['data'], status=status.HTTP_200_OK)
        
        except ValueError as e:
            return Response(
                {'error': f'Invalid input: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            return Response(
                {
                    'error': f'Error calculating path: {str(e)}',
                    'details': traceback_str
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

