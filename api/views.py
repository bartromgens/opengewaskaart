import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from api.gebruik import (
    gebruik_by_gewascode,
    gewas_gebruik_classified_codes,
)
from api.log_files import list_log_files, parse_line_count, read_log_file, resolve_log_file
from api.management.bbox import parse_gewas_codes_param
from api.models import Gewasperceel, GewasGebruik
from api.serializers import (
    CategorieSummarySerializer,
    GebruikSummarySerializer,
    GewassenSummarySerializer,
    GewasGebruikSerializer,
    GewasperceelSerializer,
)
from api.summaries import (
    GEWASSEN_SUMMARY_LIMIT_MAX,
    fetch_categorieen_summary_rows,
    fetch_gebruik_summary_rows,
    fetch_gewassen_summary_rows,
    national_http_cache_headers,
    parse_jaar_param,
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
    bbox_param = request.query_params.get("bbox")
    gewas_param = request.query_params.get("gewas")

    if jaar_param is not None:
        try:
            parse_jaar_param(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)

    gewas_codes, gewas_ok = parse_gewas_codes_param(gewas_param)
    if not gewas_ok:
        return Response({"error": "Invalid gewas parameter."}, status=400)

    limit: int | None = None
    if limit_param is not None:
        try:
            limit = int(limit_param)
        except ValueError:
            return Response({"error": "Invalid limit parameter."}, status=400)
        if limit < 1 or limit > GEWASSEN_SUMMARY_LIMIT_MAX:
            return Response({"error": "Invalid limit parameter."}, status=400)

    try:
        rows, is_national = fetch_gewassen_summary_rows(
            jaar_param=jaar_param,
            limit=limit,
            bbox_param=bbox_param,
            gewas_codes=gewas_codes,
        )
    except ValueError as exc:
        if str(exc) == "invalid_bbox":
            return Response({"error": "Invalid bbox parameter."}, status=400)
        raise

    serializer = GewassenSummarySerializer(
        rows,
        many=True,
        context={
            "gebruik_map": gebruik_by_gewascode(),
            "gewas_gebruik_codes": gewas_gebruik_classified_codes(),
        },
    )
    headers = national_http_cache_headers() if is_national else None
    return Response(serializer.data, headers=headers)


@api_view(["GET"])
@permission_classes([AllowAny])
def categorieen_summary(request: Request) -> Response:
    jaar_param = request.query_params.get("jaar")
    if jaar_param is not None:
        try:
            parse_jaar_param(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)

    rows = fetch_categorieen_summary_rows(jaar_param)
    serializer = CategorieSummarySerializer(rows, many=True)
    return Response(serializer.data, headers=national_http_cache_headers())


@api_view(["GET"])
@permission_classes([AllowAny])
def gewas_gebruik_list(request: Request) -> Response:
    rows = GewasGebruik.objects.values("gewascode", "gebruik").order_by("gewascode")
    serializer = GewasGebruikSerializer(rows, many=True)
    return Response(serializer.data, headers=national_http_cache_headers())


@api_view(["GET"])
@permission_classes([AllowAny])
def gebruik_summary(request: Request) -> Response:
    jaar_param = request.query_params.get("jaar")
    if jaar_param is not None:
        try:
            parse_jaar_param(jaar_param)
        except ValueError:
            return Response({"error": "Invalid jaar parameter."}, status=400)

    out = fetch_gebruik_summary_rows(jaar_param)
    serializer = GebruikSummarySerializer(out, many=True)
    return Response(serializer.data, headers=national_http_cache_headers())


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
