from django.shortcuts import render, redirect
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views.generic import ListView

from billing.decorators import *
from .forms import CreateUserForm, LoginForm, BulkUserUploadForm, EditUserForm, RechargeAccountForm
from .models import Subscriber
from .helpers import *

from packages.forms import PackageSubscriptionForm
from packages.models import Package

def captive(request):
    context = {'form': LoginForm()}

    if 'error_message' in request.GET:
        context.update({
            'error_message': request.GET['error_message']
        })

    if 'login_url' in request.GET:
        context.update({
          'login_url': request.GET['login_url'],
          'success_url': settings.SUCCESS_URL,
        })
    else:
        raise Http404("Login URL is incorrect. Please disconnect and reconnect to the WiFi network to get an accurate URL.")

    return render(request, 'captive.html', context)

def success(request):
    logout_url = request.session.get('logout_url', None)
    if logout_url is not None:
        context = {'logout_url': logout_url}
    if 'logout_url' in request.GET:
        context = {'logout_url': request.GET['logout_url']}
        request.session['logout_url'] = request.GET['logout_url']
    else:
        context = {}

    return render(request, 'accounts/success.html', context)

def index(request):
    # print request.COOKIES
    # We need to implement a logout page here. Users should be able to come here
    # and get a logout link to terminate their browsing session. It would be really
    # helpful if we set 'logout_url' as a cookie after user is authenticated in captive()
    # and delete this cookie when the user clicks the link to log out.
    if request.method == 'POST':
        form = CreateUserForm(request.POST, user=AnonymousUser())
        if form.is_valid():
            user = form.save()

            # Send verification mail here - we might
            # need to wrap this in a try - except block
            send_verification_mail(user)

            # We need to call login here so that our
            # dashboard can have user's details.
            auth = auth_and_login(request, user.username,
                form.cleaned_data['password'])
            if auth:
                return redirect('accounts:dashboard')
    else:
        logout_url = request.session.get('logout_url', None)
        if logout_url is not None:
            return redirect('success')
        else:
            form = CreateUserForm(user=request.user)
  
    context = {'form': form}

    return render(request, 'accounts/index.html', context)

@login_required
def dashboard(request):
    # Let's remember to use User methods here and in the template, instead of attributes.
    """
    if new_user:
        welcome_msg = ""
        context = {'message': welcome_msg}
    else:
        context = {}"""

    context = {}

    if request.user.subscriber.email_verified:
        context.update({'verified': True})

    return render(request, 'accounts/dashboard.html', context)

def verify_email(request, uidb64=None, token=None):
    assert uidb64 is not None and token is not None
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    a, b = token.split('-')

    if user is not None and len(b) == 20:
        subscriber = user.subscriber
        subscriber.email_verified = True
        subscriber.date_verified = timezone.now()
        subscriber.save()

        return redirect('accounts:dashboard')
    else:
        raise Http404("Verification link incorrect.")

@login_required
def resend_mail(request):
    send_verification_mail(request.user)
    return redirect('accounts:dashboard')

@must_be_group_admin
@login_required
def add_user(request):
    context = {}

    if request.method == 'POST':
        form = CreateUserForm(request.POST, user=request.user)
        if form.is_valid():
            user = form.save()
            success = send_group_welcome_mail([user])
            messages.success(request, 'User added successfully.')
            return redirect('accounts:add_user')
    else:
        form = CreateUserForm(user=request.user)

    context.update({'form': form})
    return render(request, 'accounts/add_user.html', context)

@login_required
def edit_user(request, pk=None):
    context = {}

    user = User.objects.get(pk=pk)

    if user.subscriber.phone_number:
        phone_number = '0' + user.subscriber.phone_number[4:]
    else:
        phone_number = ""

    dct = {
        'username': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': phone_number
        }

    request.session.set_test_cookie()

    if request.method == 'POST':
        form = EditUserForm(request.POST, user=request.user)
        if form.is_valid():
            form.save(user)
            messages.success(request, 'User changed successfully.')
            referrer = request.session.get('referrer')
            del request.session['referrer']

            return redirect(referrer)
    else:
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
            if not request.session.get('referrer'):
                request.session['referrer'] = request.META.get('HTTP_REFERER')

        form = EditUserForm(user=request.user, initial=dct)

    context.update({'form': form})
    return render(request, 'accounts/edit_user.html', context)

@must_be_group_admin
@login_required
def upload_user_list(request):
    context = {}

    if request.method == 'POST':
      form = BulkUserUploadForm(request.POST, request.FILES, user=request.user)
      if form.is_valid():
          user_list = form.save()
          success = send_group_welcome_mail(user_list)
          messages.success(request, 'Users added successfully.')
          return redirect('accounts:upload_user_list')
    else:
        form = BulkUserUploadForm(user=request.user)

    context.update({
      'form': form, 
      'file_length': settings.MAX_FILE_LENGTH
    })
    return render(request, 'accounts/upload_user_list.html', context)

@must_be_individual_user
@login_required
def buy_package(request):
    context = {}
    packages = [(p.id, p) for p in Package.objects.all()]
    if request.method == "POST":
        form = PackageSubscriptionForm(request.POST, user=request.user, packages=packages)
        if form.is_valid():
            form.save()
            messages.success(request, 'Package purchased successfully.')
            return redirect('accounts:buy_package')
    else:
        form = PackageSubscriptionForm(user=request.user, packages=packages)

    context.update(
        {
          'form': form,
          'speed_map': settings.SPEED_NAME_MAP,
          # 'volume_map': settings.VOLUME_NAME_MAP
          }
        )

    return render(request, 'packages/buy_package.html', context)

@must_be_individual_user
@login_required
def recharge_account(request):
    context = {}

    if request.method == 'POST':
        form = RechargeAccountForm(request.POST, user=request.user)
        if form.is_valid():
            voucher = form.save()
            url = settings.VOUCHER_INVALIDATE_URL
            response = send_api_request(url, {'id': voucher['serial_number']})

            if response['code'] == 200:
                messages.success(request, "Account recharged successfully.")
                return redirect('accounts:recharge_account')
    else:
        form = RechargeAccountForm(user=request.user)

    context.update({'form': form})
    return render(request, 'accounts/recharge_account.html', context)

@must_be_group_admin
@login_required
def view_users(request, page=None):
    context = {}
    user_list = User.objects.filter(subscriber__group=request.user.subscriber.group).exclude(pk=request.user.pk)

    paginate_by = request.GET.get('paginate_by', None)

    if paginate_by is None:
        paginate_by = 10

    paginator = Paginator(user_list, int(paginate_by))

    if page is None:
        page = request.GET.get('page')

    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    context.update({'users': users})

    if paginate_by is not None:
        context.update({'paginate_by': paginate_by})

    return render(request, 'accounts/user_list.html', context)

@must_be_group_admin
@login_required
def toggle_status(request, pk):
    user = User.objects.get(pk=pk)
    
    if not request.session.get('referrer'):
        request.session['referrer'] = request.META.get('HTTP_REFERER')

    referrer = request.session.get('referrer')
    del request.session['referrer']

    if user.is_active:
        user.is_active = False
    else:
        group = request.user.subscriber.group
        if group.max_user_count_reached() or group.available_user_slots_count() is None:
            if not settings.EXCEED_MAX_USER_COUNT:
                messages.error(request,
                    "You are not allowed to create more users than your group threshold. Your group threshold is set to %s." % group.max_no_of_users)
                return redirect(referrer)
        else:
            user.is_active = True

    user.save()

    return redirect(referrer)
