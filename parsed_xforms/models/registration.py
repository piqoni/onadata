from django.db import models
from parsed_instance import ParsedInstance
from surveyor_manager.models import Surveyor
from common_tags import SURVEYOR_NAME, INSTANCE_DOC_NAME, REGISTRATION

class Registration(models.Model):
    parsed_instance = models.ForeignKey(ParsedInstance)
    surveyor = models.ForeignKey(Surveyor)

    class Meta:
        app_label = "parsed_xforms"

    @classmethod
    def get_registered_surveyor(cls, parsed_instance):
        # We need both a phone and a start time to know who this
        # survey should be attributed to.
        if parsed_instance.phone is None or \
                parsed_instance.start_time is None:
            return None
        # Find all registrations for this phone that happened before
        # this instance.
        qs = cls.objects.filter(
            parsed_instance__phone=parsed_instance.phone,
            parsed_instance__start_time__lte=parsed_instance.start_time
            )
        # Order them by start time.
        qs = qs.order_by("-parsed_instance__start_time")
        if qs.count()==0:
            return None
        most_recent_registration = qs[0]
        return most_recent_registration.parsed_instance.surveyor

    def _create_surveyor(self):
        doc = self.parsed_instance.to_dict()
        name = doc.get(u"name", u"")
        if not name:
            raise Exception(
                "Registration must have a non-empty name.",
                self.parsed_instance.instance.xml, doc
                )
        # Hack city with the username and password here.
        kwargs = {"username" : "surveyor%d" % Surveyor.objects.count(),
                  "password" : "noneisabadd3f4u1tpassword",
                  "name" : name,}
        return Surveyor.objects.create(**kwargs)

    def save(self, *args, **kwargs):
        self.surveyor = self._create_surveyor()
        super(Registration, self).save(*args, **kwargs)


def _set_surveyor(sender, **kwargs):
    parsed_instance = kwargs["instance"]
    doc = parsed_instance.to_dict()
    if doc[INSTANCE_DOC_NAME]==REGISTRATION:
        # There should be a prettier way to do this. But, we want to
        # make sure if this parsed instance has already been logged
        # that we don't try to do it again.
        qs = Registration.objects.filter(parsed_instance=parsed_instance)
        if qs.count()>0: return

        registration = \
            Registration.objects.create(parsed_instance=parsed_instance)
        parsed_instance.surveyor = registration.surveyor
        # We need to save this update to the database.
        parsed_instance.save()
    else:
        parsed_instance.surveyor = \
            Registration.get_registered_surveyor(parsed_instance)

from django.db.models.signals import post_save
post_save.connect(_set_surveyor, sender=ParsedInstance)
