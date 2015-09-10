from django import forms
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from ..models import GroupAccount
from ..admin import AccountsUserCreationForm, AccountsUserChangeForm, AccessPointAdminForm, SubscriberAdminForm, GroupAccountAdminForm

from packages.models import Package

class AdminFormsTest(TestCase):

    def setUp(self):
        self.help_text = "Required. 100 characters or fewer. Letters, digits and @/./+/-/_ only."
    
    def test_accounts_user_creation_form(self):
        a = AccountsUserCreationForm()
        self.assertEqual(a.fields['username'].help_text, self.help_text)

    def test_accounts_user_change_form(self):
        a = AccountsUserChangeForm()
        self.assertEqual(a.fields['username'].help_text, self.help_text)

class GroupAccountRelatedTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='b@b.com', password='12345')
        self.package = Package.objects.create(package_type='Daily', volume='3', speed='1.5')
        self.ga = GroupAccount.objects.create(name='CUG', package=self.package,
            max_no_of_users=10, package_start_time=timezone.now(), package_status=True)

    def test_access_point_admin_form_invalid(self):
        form = AccessPointAdminForm({'name': 'HQ', 'group': self.ga.pk, 'mac_address': '00:18:0A:F2:DE:20', 'status': 'PUB'})
        self.assertFalse(form.is_valid())
        # print form.is_valid()
        # with self.assertRaises(forms.ValidationError):
            # form.clean()

    def test_access_point_admin_form_valid(self):
        form = AccessPointAdminForm({'name': 'HQ', 'group': self.ga.pk, 'mac_address': '00:18:0A:F2:DE:20', 'status': 'PRV'})
        self.assertTrue(form.is_valid())
        # print form.clean()

    def test_subscriber_admin_form(self):
        form = SubscriberAdminForm({
          'phone_number': '0542751610',
          'group': self.ga.pk,
          'is_group_admin': True,
          'country': 'GHA',
          'date_verified': None,
          'user': self.user.pk,
          'email_verified': False,
          'id': None})
        subscriber = form.save()
        self.assertEqual(subscriber.phone_number, '+233542751610')
        self.assertEqual(subscriber.user.email, 'b@b.com')

    def test_group_account_admin_form_invalid(self):
        form  = GroupAccountAdminForm({'package_status': False, 'name': 'CUG', 'max_no_of_users': 50, 'package': self.package.pk})
        self.assertFalse(form.is_valid())

    def test_group_account_admin_form_valid(self):
        data = {'package_status': True, 'name': 'LUG', 'max_no_of_users': 50, 'package': self.package.pk}
        form  = GroupAccountAdminForm(data)
        self.assertTrue(form.is_valid())
        form.save()
        ga = GroupAccount.objects.get(name__exact=data['name'])
        self.assertEqual((ga.package_stop_time - ga.package_start_time).days, settings.PACKAGE_TYPES_HOURS_MAP[self.package.package_type] / 24)
