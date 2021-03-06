# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20150910_1824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriber',
            name='phone_number',
            field=models.CharField(max_length=15, null=True, validators=[django.core.validators.RegexValidator(regex=b'^\\+?1?\\d{9,15}$', message=b"Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]),
        ),
    ]
