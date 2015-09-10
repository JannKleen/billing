from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django import forms

from .models import *
from .helpers import send_verification_mail

from datetime import timedelta

help_text = "Required. 100 characters or fewer. Letters, digits and @/./+/-/_ only."

class GroupAccountAdminForm(forms.ModelForm):

    class Meta:
        model = GroupAccount
        exclude = ()

    def clean(self):
        cleaned_data = super(GroupAccountAdminForm, self).clean()

        if not cleaned_data['package_status']:
            group_account = GroupAccount.objects.get(name__exact=cleaned_data['name'])
            if group_account.package_start_time:
                raise forms.ValidationError("You cannot switch off a package.")

        return cleaned_data

    def save(self, commit=True):
        group_account = super(GroupAccountAdminForm, self).save(commit=False)

        if group_account.package_status:
            now = timezone.now()
            if not group_account.package_start_time:
                group_account.package_start_time = now

            if not group_account.package_stop_time:
                package_period = timedelta(hours=settings.PACKAGE_TYPES_HOURS_MAP[group_account.package.package_type])
                group_account.package_stop_time = group_account.package_start_time + package_period

        group_account.save()

        return group_account

class GroupAccountAdmin(admin.ModelAdmin):
    form = GroupAccountAdminForm

class SubscriberAdminForm(forms.ModelForm):

    class Meta:
        model = Subscriber
        exclude = ()

    def save(self, commit=True):
        subscriber = super(SubscriberAdminForm, self).save(commit=False)
        country_code = Subscriber.COUNTRY_CODES_MAP[subscriber.country]

        if not subscriber.phone_number.startswith(country_code):
            subscriber.phone_number = country_code + subscriber.phone_number[1:]

            subscriber.user.email = subscriber.user.username
            subscriber.user.save()

            send_verification_mail(subscriber.user)

        subscriber.save()

        return subscriber

class SubscriberInline(admin.StackedInline):
    model = Subscriber
    form = SubscriberAdminForm
    can_delete = False
    verbose_name_plural = 'subscribers'

class AccountsUserCreationForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super(AccountsUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = help_text

class AccountsUserChangeForm(UserChangeForm):

    def __init__(self, *args, **kwargs):
        super(AccountsUserChangeForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = help_text

class AccountsUserAdmin(UserAdmin):
    form = AccountsUserChangeForm
    add_form = AccountsUserCreationForm
    inlines = (SubscriberInline, )

    """
    Original
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    ) """
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

class AccessPointAdminForm(forms.ModelForm):

    class Meta:
        model = AccessPoint
        fields = ('name', 'group', 'mac_address', 'status')

    def clean(self):
        cleaned_data = super(AccessPointAdminForm, self).clean()
        if cleaned_data['group'] is not None and cleaned_data['status'] == 'PUB':
            raise forms.ValidationError("Group Access Points cannot be public.")

        return cleaned_data

class AccessPointAdmin(admin.ModelAdmin):
    form = AccessPointAdminForm

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, AccountsUserAdmin)
admin.site.register(GroupAccount, GroupAccountAdmin)
admin.site.register(AccessPoint, AccessPointAdmin)
