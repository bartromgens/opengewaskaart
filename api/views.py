import logging

from rest_framework.authentication import SessionAuthentication
from django.db.models import Count, Sum
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
from api.log_files import list_log_files, parse_line_count, read_log_file, resolve_log_file
from api.models import Gewasperceel
from api.serializers import (
    CategorieSummarySerializer,
    GewassenSummarySerializer,
    GewasperceelSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health_check(request: Request) -> Response:
    logger.debug("Health check requested.")
    return Response({"status": "ok"})


class GewasperceelDetailView(RetrieveAPIView):
    queryset = Gewasperceel.objects.all()
    serializer_class = GewasperceelSerializer

    def retrieve(self, request, *args, **kwargs):
        logger.info("Parcel detail requested: pk=%s", kwargs.get("pk"))
        return super().retrieve(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([AllowAny])
def gewassen_summary(request: Request) -> Response:
    jaar_param = request.query_params.get("jaar")
    limit_param = request.query_params.get("limit")
    queryset = Gewasperceel.objects.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    if jaar_param is not None:
        try:
            jaar = int(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)
        queryset = queryset.filter(jaar=jaar)

    rows = (
        queryset.values("gewascode", "gewas", "category")
        .annotate(parcel_count=Count("id"), area_m2=Sum("area_m2"))
        .order_by("-parcel_count")
    )
    if limit_param is not None:
        try:
            limit = int(limit_param)
        except ValueError:
            return Response({"error": "Invalid limit parameter."}, status=400)
        if limit < 1:
            return Response({"error": "Invalid limit parameter."}, status=400)
        rows = rows[:limit]

    serializer = GewassenSummarySerializer(rows, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def categorieen_summary(request: Request) -> Response:
    jaar_param = request.query_params.get("jaar")
    queryset = Gewasperceel.objects.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    if jaar_param is not None:
        try:
            jaar = int(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)
        queryset = queryset.filter(jaar=jaar)

    rows = (
        queryset.values("category")
        .annotate(parcel_count=Count("id"), area_m2=Sum("area_m2"))
        .order_by("-parcel_count")
    )
    serializer = CategorieSummarySerializer(rows, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def admin_status(request: Request) -> Response:
    user = request.user
    is_staff = bool(user.is_authenticated and user.is_staff)
    return Response(
        {
            "is_staff": is_staff,
            "username": user.get_username() if is_staff else None,
        }
    )


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def admin_logs(request: Request) -> Response:
    return Response({"files": list_log_files()})


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def admin_log_content(request: Request, name: str) -> Response:
    path = resolve_log_file(name)
    if path is None:
        return Response({"error": "Log file not found."}, status=404)
    return Response(
        read_log_file(path, parse_line_count(request.query_params.get("lines")))
    )
