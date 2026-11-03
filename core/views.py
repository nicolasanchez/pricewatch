from django.db.models import Count
from django.shortcuts import render

from catalog.categories import annotated_games, attach_best_deals, home_categories
from catalog.models import Store


def home(request):
    stores = Store.objects.filter(is_active=True).annotate(n=Count("deals")).filter(n__gt=0).order_by("-n", "name")
    return render(request, "core/home.html", {
        "categories": home_categories(),
        "stores": stores,
        "suggestions": annotated_games().order_by("-popularity")[:3],
    })


def search(request):
    """Resultados en vivo del buscador (htmx)."""
    q = request.GET.get("q", "").strip()
    results = []
    if q:
        results = attach_best_deals(annotated_games().filter(title__icontains=q).order_by("-popularity", "title")[:6])
    return render(request, "core/_search_results.html", {"q": q, "results": results})


def legal(request):
    return render(request, "core/legal.html")


def not_found(request, exception=None):
    return render(request, "core/404.html", status=404)
