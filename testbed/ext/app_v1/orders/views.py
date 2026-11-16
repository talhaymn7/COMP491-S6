import json

from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from . import services


def _resource(name):
    if name not in services.RESOURCES:
        raise Http404(name)
    return services.RESOURCES[name]


@csrf_exempt
def collection(request, resource):
    model, create, summary = _resource(resource)
    if request.method == "POST":
        try:
            obj = create(json.loads(request.body))
        except ValidationError as e:
            return JsonResponse({"errors": e.message_dict}, status=400)
        return JsonResponse(summary(obj), status=201)
    return JsonResponse({"items": [summary(o) for o in model.objects.order_by("id")]})


@csrf_exempt
def detail(request, resource, pk):
    model, _, summary = _resource(resource)
    obj = get_object_or_404(model, pk=pk)
    if request.method == "PATCH":
        try:
            services.update_note(resource, obj, json.loads(request.body).get("note", ""))
        except ValidationError as e:
            return JsonResponse({"errors": e.message_dict}, status=400)
    return JsonResponse(summary(obj))


def report(request):
    return JsonResponse(services.report())
