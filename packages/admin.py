from django import forms
from django.contrib import admin
from django.utils import timezone

from .models import *
from .helpers import *

class PackageSubscriptionAdminForm(forms.ModelForm):

    class Meta:
        model = PackageSubscription
        exclude = ()

    def clean(self):
        cleaned_data = super(PackageSubscriptionAdminForm, self).clean()
        radcheck = cleaned_data.get('radcheck')
        package = cleaned_data.get('package')

        start, amount, balance = check_balance_and_subscription(radcheck, package)
        update_cleaned_data(cleaned_data, {'start': start, 'amount': amount, 'balance': balance})

    def save(self, commit=True):
        radcheck = self.cleaned_data['radcheck']
        amount = self.cleaned_data['amount']
        balance = self.cleaned_data['balance']
        package = self.cleaned_data['package']

        # Charge subscriber for package
        charge_subscriber(radcheck, amount, balance, package)

        package_subscription = super(PackageSubscriptionAdminForm, self).save(commit=False)
        package_subscription.stop = compute_stop(package_subscription.start,
            package_subscription.package.package_type)
        package_subscription.save()

        return package_subscription

class GroupPackageSubscriptionAdminForm(forms.ModelForm):

    class Meta:
        model = GroupPackageSubscription
        exclude = ()

    def clean(self):
        cleaned_data = super(GroupPackageSubscriptionAdminForm, self).clean()
        group = cleaned_data.get('group')
        start = check_subscription(group=group)
        cleaned_data['start'] = start

    def save(self, commit=True):
        group_package_subscription = super(GroupPackageSubscriptionAdminForm, self).save(commit=False)
        group_package_subscription.stop = compute_stop(group_package_subscription.start,
            group_package_subscription.package.package_type)
        group_package_subscription.save()

        return group_package_subscription

def subscription_package(obj):
    return obj.package.__str__()

subscription_package.short_description = 'Package'
subscription_package.admin_order_field = 'package__package_type'

def subscription_group(obj):
    return obj.group.name

subscription_group.short_description = 'Group'
subscription_group.admin_order_field = 'group__name'

def subscription_radcheck(obj):
    return obj.radcheck.username

subscription_radcheck.short_description = 'Subscriber'
subscription_radcheck.admin_order_field = 'radcheck__username'

class PackageSubscriptionAdmin(admin.ModelAdmin):
    form = PackageSubscriptionAdminForm
    list_display = (subscription_package, 'start', 'stop', subscription_radcheck)
    search_fields = ('package__package_type', 'radcheck__username')

    def get_queryset(self, request):
        qs = super(PackageSubscriptionAdmin, self).get_queryset(request)
        return qs.exclude(stop__lt=timezone.now())

class GroupPackageSubscriptionAdmin(admin.ModelAdmin):
    form = GroupPackageSubscriptionAdminForm
    list_display = (subscription_package, 'start', 'stop', subscription_group)
    search_fields = ('package__package_type', 'group__name')

    def get_queryset(self, request):
        qs = super(GroupPackageSubscriptionAdmin, self).get_queryset(request)
        return qs.exclude(stop__lt=timezone.now())

class PackageAdmin(admin.ModelAdmin):
    list_display = ('package_type', 'volume', 'speed', 'price')
    search_fields = ('package_type', 'volume', 'speed')

admin.site.register(Package, PackageAdmin)
admin.site.register(PackageSubscription, PackageSubscriptionAdmin)
admin.site.register(GroupPackageSubscription, GroupPackageSubscriptionAdmin)
