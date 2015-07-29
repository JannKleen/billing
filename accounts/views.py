from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import logout as auth_logout
from django.conf import settings

from .forms import CreateAccountForm, LoginForm
from .helpers import *

def index(request):
    if request.method == 'POST':
        form = CreateAccountForm(request.POST)
        if form.is_valid():
            # Create user in Django
            user = User.objects.create_user(
                form.cleaned_data['username'], form.cleaned_data['username'], form.cleaned_data['password']
            )
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            # user.phone_number = form.cleaned_data['phone_number']
            user.save()
            # Save username and password in RADIUS radcheck.
            form.save()

            # We need to call login here so that our dashboard can have user's details.
            auth = auth_and_login(request, user.username, form.cleaned_data['password'])
            if auth:
                return redirect('accounts:dashboard')
    else:
        form = CreateAccountForm()
  
    context = {'form': form}

    return render(request, 'accounts/index.html', context)

def login(request):
    if request.method == 'POST':
        parts = request.POST['login_url'].split('?')
        login_url = parts[0]
        auth_string = parts[1].split('&')[0]
        logout_url = login_url[:-5] + 'logout/?' + auth_string

        form = LoginForm(request.POST)

        if form.is_valid():
            email = request.POST['username']
            password = request.POST['password']

            auth = auth_and_login(request, email, password)

            if auth:
                if not settings.SERV_PKG:
                    # Go and buy service package at dashboard.
                    # return redirect(settings.LOGIN_REDIRECT_URL)
                    pass
                    # After buying package, do Meraki auth (automatically?? - can we have user who 
                    # just buys package without intentions of browsing?) 
                    # and redirect to dashboard displaying message in session.
                else:
                    # User has service package, let's attempt Meraki authentication
                    # After successful Meraki auth, user is redirected to dashboard with
                    # message that he is connected and can end his browsing session
                    # by clicking logout_url. logout_url is stored in Session and retrieved
                    # to construct logout link.
                    meraki_auth(request, email, password, logout_url)
                
                return redirect(settings.LOGIN_REDIRECT_URL)

        context = {'form': form}
    else:
        context = {'form': LoginForm()}
        if request.GET:
            context.update({
              'login_url': request.GET['login_url'],
              'continue_url': request.GET['continue_url']
            })

    return render(request, 'accounts/login.html', context)

def dashboard(request):
    # Let's remember to use User methods here and in the template, instead of attributes.
    """
    if new_user:
        welcome_msg = ""
        context = {'message': welcome_msg}
    else:
        context = {}"""

    context = {}
    if 'auth_message' in request.session:
        context.update({'auth_message': request.session['auth_message']})
        if 'logout_url' in request.session:
            context.update({'logout_url': request.session['logout_url']})

    return render(request, 'accounts/dashboard.html', context)
