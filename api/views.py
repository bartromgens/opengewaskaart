import logging

from rest_framework.authentication import SessionAuthentication
from django.conf import settings
from django.core.cache import cache
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
from api.gebruik import gebruik_by_gewascode
from api.models import Gewasperceel, GewasGebruik
from api.serializers import (
    CategorieSummarySerializer,
    GebruikSummarySerializer,
    GewassenSummarySerializer,
    GewasGebruikSerializer,
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

    def get_serializer_context(self) -> dict:
        ctx = super().get_serializer_context()
        ctx["gebruik_map"] = gebruik_by_gewascode()
        return ctx

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

    # Full-table aggregate is slow; cache the rows (gebruik is merged in below).
    cache_key = f"gewassen_summary:{jaar_param}:{limit_param}"
    cached_rows = cache.get(cache_key)
    if cached_rows is None:
        cached_rows = list(rows)
        cache.set(cache_key, cached_rows, settings.SUMMARY_CACHE_SECONDS)
    rows = cached_rows

    codes_in_gebruik_table = set(
        GewasGebruik.objects.values_list("gewascode", flat=True)
    )
    serializer = GewassenSummarySerializer(
        rows,
        many=True,
        context={
            "gebruik_map": gebruik_by_gewascode(),
            "gewas_gebruik_codes": codes_in_gebruik_table,
        },
    )
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
@permission_classes([AllowAny])
def gewas_gebruik_list(request: Request) -> Response:
    rows = GewasGebruik.objects.values("gewascode", "gebruik").order_by("gewascode")
    serializer = GewasGebruikSerializer(rows, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def gebruik_summary(request: Request) -> Response:
    from collections import defaultdict

    jaar_param = request.query_params.get("jaar")
    queryset = Gewasperceel.objects.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    if jaar_param is not None:
        try:
            jaar = int(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)
        queryset = queryset.filter(jaar=jaar)

    gebruik_map = gebruik_by_gewascode()

    parcels: dict[str, int] = defaultdict(int)
    areas: dict[str, float] = defaultdict(float)
    # Aggregate per gewascode in the database (a few hundred rows) instead of
    # iterating every parcel in Python; cache since it scans the whole table.
    cache_key = f"gebruik_summary:{jaar_param}"
    per_code = cache.get(cache_key)
    if per_code is None:
        per_code = list(
            queryset.values("gewascode").annotate(
                parcel_count=Count("id"), area_m2=Sum("area_m2")
            )
        )
        cache.set(cache_key, per_code, settings.SUMMARY_CACHE_SECONDS)
    for row in per_code:
        code = int(row["gewascode"])
        g = gebruik_map.get(code, GewasGebruik.GEBRUIK_ONBEKEND)
        parcels[g] += row["parcel_count"]
        am = row["area_m2"]
        if am is not None:
            areas[g] += float(am)

    order = (
        GewasGebruik.GEBRUIK_VEEVOER,
        GewasGebruik.GEBRUIK_VOEDSEL,
        GewasGebruik.GEBRUIK_GEMENGD,
        GewasGebruik.GEBRUIK_NIET_VOEDSEL,
        GewasGebruik.GEBRUIK_ONBEKEND,
    )
    seen = set(order)
    out = []
    for g in order:
        pc = parcels.get(g, 0)
        am2 = areas.get(g, 0.0)
        out.append(
            {
                "gebruik": g,
                "parcel_count": pc,
                "area_m2": am2 if am2 > 0 else None,
            }
        )
    for g in sorted(set(parcels) | set(areas)):
        if g in seen:
            continue
        pc = parcels.get(g, 0)
        am2 = areas.get(g, 0.0)
        out.append(
            {
                "gebruik": g,
                "parcel_count": pc,
                "area_m2": am2 if am2 > 0 else None,
            }
        )

    serializer = GebruikSummarySerializer(out, many=True)
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
