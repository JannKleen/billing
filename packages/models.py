from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import GroupAccount

class Package(models.Model):
    package_type = models.CharField(max_length=7, choices=settings.PACKAGE_TYPES)
    volume = models.CharField(max_length=9, choices=settings.VOLUME_CHOICES)
    speed = models.CharField(max_length=3, choices=settings.SPEED_CHOICES, default='1.5')

    def __str__(self):
        if self.volume != "Unlimited":
            return "%s %sGB" % (self.package_type, self.volume)
        else:
            return "%s %s" % (self.package_type, self.volume)

""" class PackageSubscription(models.Model):
    pass """

class GroupPackageSubscription(models.Model):
    group = models.ForeignKey(GroupAccount)
    package = models.ForeignKey(Package)
    start = models.DateTimeField()
    stop = models.DateTimeField(blank=True, help_text="The time this subscription expires. You are not allowed to set this.")

    class Meta:
        verbose_name = "Group Package Subscription"
        ordering = ['-stop']

    def __str__(self):
        return "%s %s %s" % (self.group.name, self.package.package_type, self.stop.strftime('%B %d %Y, %I:%M%p'))

    def is_valid(self, now=timezone.now()):
        return self.stop > now
