import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from . import services
from .models import Order


@csrf_exempt
def orders(request):
    if request.method == "POST":
        try:
            order = services.create_order(json.loads(request.body))
        except ValidationError as e:
            return JsonResponse({"errors": e.message_dict}, status=400)
        return JsonResponse(services.order_summary(order), status=201)
    return JsonResponse({"orders": [services.order_summary(o) for o in Order.objects.order_by("id")]})


@csrf_exempt
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "PATCH":
        try:
            services.update_note(order, json.loads(request.body).get("note", ""))
        except ValidationError as e:
            return JsonResponse({"errors": e.message_dict}, status=400)
    return JsonResponse(services.order_summary(order))


def report(request):
    return JsonResponse(services.revenue_report())
