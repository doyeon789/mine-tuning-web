from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


class AccountLoginView(LoginView):
    authentication_form = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect("mine_chat:index")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("mine_chat:index")
    else:
        form = UserCreationForm()

    return render(request, "accounts/signup.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect("accounts:signup")
