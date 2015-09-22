from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django import forms

from .models import *
from .helpers import send_verification_mail, md5_password

help_text = "Required. 100 characters or fewer. Letters, digits and @/./+/-/_ only."

class SubscriberAdminForm(forms.ModelForm):

    class Meta:
        model = Subscriber
        exclude = ()

    def clean(self):
        cleaned_data = super(SubscriberAdminForm, self).clean()

        if cleaned_data['group'] is None or cleaned_data['is_group_admin'] is False:
            raise forms.ValidationError("You must set the group and group admin status of this user.")

        return cleaned_data

    def save(self, commit=True):
        subscriber = super(SubscriberAdminForm, self).save(commit=False)
        country_code = Subscriber.COUNTRY_CODES_MAP[subscriber.country]

        if not subscriber.phone_number.startswith(country_code):
            subscriber.phone_number = country_code + subscriber.phone_number[1:]

        subscriber.save()

        send_verification_mail(subscriber.user)

        return subscriber

class SubscriberInline(admin.StackedInline):
    model = Subscriber
    form = SubscriberAdminForm
    can_delete = False
    verbose_name_plural = 'subscribers'

class AccountsUserCreationForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super(AccountsUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Email Address"
        self.fields['username'].help_text = help_text

    def save(self, commit=True):
        user = super(AccountsUserCreationForm, self).save(commit=False)
        user.email = user.username
        user.save()

        md5 = md5_password(self.cleaned_data['password1'])
        Radcheck.objects.create(username=self.cleaned_data['username'],
                                attribute='MD5-Password',
                                op=':=',
                                value=md5)

        return user

class AccountsUserChangeForm(UserChangeForm):

    def __init__(self, *args, **kwargs):
        super(AccountsUserChangeForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Email Address"
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
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
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
admin.site.register(GroupAccount)
admin.site.register(AccessPoint, AccessPointAdmin)
