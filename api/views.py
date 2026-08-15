from rest_framework.decorators import api_view
from rest_framework.generics import RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Gewasperceel
from api.serializers import GewasperceelSerializer


@api_view(["GET"])
def health_check(request: Request) -> Response:
    return Response({"status": "ok"})


class GewasperceelDetailView(RetrieveAPIView):
    queryset = Gewasperceel.objects.all()
    serializer_class = GewasperceelSerializer
