from allauth.account.forms import LoginForm, SignupForm
from allauth.account.views import LoginView, SignupView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import Profile


class AccessMixin:
    """Inicio de sesión y registro comparten pantalla, como en el boceto."""

    template_name = "account/access.html"
    mode = "login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.mode == "login":
            ctx["login_form"] = ctx.get("form")
            ctx["signup_form"] = SignupForm()
        else:
            ctx["signup_form"] = ctx.get("form")
            ctx["login_form"] = LoginForm(request=self.request)
        ctx["mode"] = self.mode
        return ctx


class AccessLoginView(AccessMixin, LoginView):
    mode = "login"


class AccessSignupView(AccessMixin, SignupView):
    mode = "signup"


@login_required
def profile(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=prof)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cambios guardados. Los precios ya se muestran en tu moneda.")
        return redirect("profile")
    return render(request, "account/profile.html", {"form": form})
