import re

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.html import linebreaks
from django.utils.text import Truncator
from wagtail.images import get_image_model_string

from .services import parse_exif, parse_iptc

IMAGE_MODEL = get_image_model_string()


@receiver(pre_save, sender=IMAGE_MODEL)
def parse_image_meta(sender, **kwargs):
    """
    Parses image meta data from a tif or jpeg and populates the corresponding
    fields of the image model.
    """
    instance = kwargs["instance"]

    # If we have an ID, don't parse again.
    if instance.id is not None:
        return

    meta_dict = parse_iptc(instance.file)

    # Add the meta data to the fields.
    if title := meta_dict.get("headline", ""):
        trimmed_title = Truncator(title.strip()).chars(255)
        instance.title = trimmed_title
        instance.alt = trimmed_title

    if credit := meta_dict.get("credit", ""):
        trimmed_credit = Truncator(credit.strip()).chars(255)
        instance.credit = trimmed_credit

    if caption := meta_dict.get("caption", ""):
        # Wrap plain-text in <p> tags for RichTextField values.
        starts_with_tag = bool(re.search("^<[p|div].*?>", caption))

        if starts_with_tag:
            instance.caption = caption.strip()
        else:
            instance.caption = linebreaks(caption.strip())

    if byline := meta_dict.get("byline", ""):
        trimmed_byline = Truncator(byline.strip()).chars(255)
        instance.byline = trimmed_byline

    if instructions := meta_dict.get("instructions", ""):
        trimmed_instructions = Truncator(instructions.strip()).chars(255)
        instance.usage_terms = trimmed_instructions.strip()

    if copyright_notice := meta_dict.get("copyright_notice", ""):
        trimmed_copyright = Truncator(copyright_notice.strip()).chars(255)
        instance.copyright_notice = trimmed_copyright

    instance.iptc_data = meta_dict

    if hasattr(instance, "exif_data"):
        exif_data = parse_exif(instance.file)

        def string_clean_up(s: str) -> str:
            return Truncator(s.strip().rstrip("\x00")).chars(255)

        if camera_make := exif_data.get("Make", None):
            instance.camera_make = string_clean_up(camera_make)

        if camera_model := exif_data.get("Model", None):
            instance.camera_model = string_clean_up(camera_model)

        if lens_make := exif_data.get("LensMake", None):
            instance.lens_make = string_clean_up(lens_make)

        if lens_model := exif_data.get("LensModel", None):
            instance.lens_model = string_clean_up(lens_model)

        if focal_length := exif_data.get("FocalLength", None):
            instance.focal_length = string_clean_up(focal_length)

        if shutter_speed := exif_data.get("ExposureTime", None):
            instance.shutter_speed = string_clean_up(shutter_speed)

        if aperture := exif_data.get("ApertureValue", None):
            aperture_float = float(aperture)
            instance.aperture = f"f/{aperture_float:.2f}"

        if iso_rating := exif_data.get("ISOSpeedRatings", None):
            instance.iso_rating = f"{iso_rating}ISO"

        if latitude := exif_data.get("latitude"):
            instance.latitude = latitude

        if longitude := exif_data.get("longitude"):
            instance.longitude = longitude

        instance.exif_data = exif_data
