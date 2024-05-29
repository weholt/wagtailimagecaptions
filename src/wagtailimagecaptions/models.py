import json
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone
from wagtail.coreutils import string_to_ascii
from wagtail.fields import RichTextField
from wagtail.images.models import AbstractImage, AbstractRendition, Image
from wagtail.search import index


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return
        return json.JSONEncoder.default(self, o)


class CaptionedImage(AbstractImage):
    uuid = models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)
    alt = models.CharField(
        max_length=255,
        blank=True,
        help_text="Set the image alt text used for accessibility.",
    )
    caption = RichTextField(features=["bold", "italic"], null=True, blank=True, help_text="Set the image caption.")
    credit = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name of the provider (e.g. AP, Getty, Reuters).",
    )
    byline = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name(s) of the creator(s) of the image.",
    )
    usage_terms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Rights information and usage limitations associated with the image, including any special restrictions or instructions.",
    )
    copyright_notice = models.CharField(
        max_length=255,
        blank=True,
        help_text="Any necessary copyright notice(s).",
    )
    iptc_data = models.JSONField(null=True, blank=True)

    admin_form_fields = Image.admin_form_fields + (
        "credit",
        "byline",
        "alt",
        "caption",
        "usage_terms",
        "copyright_notice",
    )

    search_fields = AbstractImage.search_fields + [
        index.SearchField("uuid"),
        index.SearchField("caption"),
    ]

    def default_alt_text(self):
        """Return our stored alt value, otherwise Wagtail defaults to the title."""
        if self.alt:
            return self.alt
        return super().default_alt_text

    def get_upload_to(self, filename):
        """Overrides the `get_upload_to` method to include set date paths."""
        folder_name = "original_images"

        if hasattr(settings, "WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH") and settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH:
            now = timezone.now()
            date_path = now.strftime(settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH)
            folder_name = os.path.join(folder_name, date_path)

        # ...now continue with Wagtail source.
        filename = self.file.field.storage.get_valid_name(filename)

        # convert the filename to simple ascii characters and then
        # replace non-ascii characters in filename with _ , to sidestep issues with filesystem encoding
        filename = "".join((i if ord(i) < 128 else "_") for i in string_to_ascii(filename))

        # Truncate filename so it fits in the 100 character limit
        # https://code.djangoproject.com/ticket/9893
        full_path = os.path.join(folder_name, filename)
        if len(full_path) >= 95:
            chars_to_trim = len(full_path) - 94
            prefix, extension = os.path.splitext(filename)
            filename = prefix[:-chars_to_trim] + extension
            full_path = os.path.join(folder_name, filename)

        return full_path


class CaptionedRendition(AbstractRendition):
    image = models.ForeignKey(CaptionedImage, on_delete=models.CASCADE, related_name="renditions")

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)

    def get_upload_to(self, filename):
        """Overrides the `get_upload_to` method to include set date paths."""
        if hasattr(settings, "WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH") and settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH:
            now = timezone.now()
            date_path = now.strftime(settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH)
            filename = self.file.field.storage.get_valid_name(filename)

            # Setting 'images' here to remain consistent with the Wagtail method.
            return os.path.join("images", date_path, filename)

        return super().get_upload_to(filename)


class CaptionedExifImage(CaptionedImage):
    """
    A specialized model based on CaptionedImage which adds support for a few select EXIF
    related fields, like camera make & model, lens make & model etc.
    """

    exif_data = models.JSONField(null=True, blank=True, encoder=DateTimeEncoder)
    date_time_original = models.DateTimeField(null=True, blank=True, help_text="The date and time of creation of the image (EXIF DateTimeOriginal)")

    camera_make = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name of the camera make (e.g. Fujifilm, Sony, Canon).",
    )

    camera_model = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name of the camera model (e.g. X100V, 70D).",
    )

    lens_make = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name of the lens make (e.g. Fujinon, Nikkor).",
    )

    lens_model = models.CharField(
        max_length=255,
        blank=True,
        help_text="The name of the lens model (e.g. XF 33mm f/1.4 R LM WR, Sony FE 24mm f/1.4 GM).",
    )

    focal_length = models.CharField(
        max_length=255,
        blank=True,
        help_text="The focal length in millimeters (e.g. 33mm, 200mm).",
    )

    shutter_speed = models.CharField(
        max_length=255,
        blank=True,
        help_text="The shutter speed in seconds (e.g. 1/1000 sec, 1/15 sec).",
    )

    aperture = models.CharField(
        max_length=255,
        blank=True,
        help_text="The aperture used (e.g. f/1.8, f/4).",
    )

    iso_rating = models.CharField(
        max_length=255,
        blank=True,
        help_text="The ISO rating (e.g. 400 ISO, 800 ISO).",
    )

    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="The latitude (e.g. ?).",
    )

    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="The longitude (e.g. ?).",
    )


class CaptionedExifRendition(AbstractRendition):
    "Specialized redition for the CaptionExifImage model"

    image = models.ForeignKey(CaptionedExifImage, on_delete=models.CASCADE, related_name="exif_renditions")

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)

    def get_upload_to(self, filename):
        """Overrides the `get_upload_to` method to include set date paths."""
        if hasattr(settings, "WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH") and settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH:
            now = timezone.now()
            date_path = now.strftime(settings.WAGTIALIMAGECAPTIONS_UPLOAD_TO_DATE_PATH)
            filename = self.file.field.storage.get_valid_name(filename)

            # Setting 'images' here to remain consistent with the Wagtail method.
            return os.path.join("images", date_path, filename)

        return super().get_upload_to(filename)
