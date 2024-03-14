import datetime
import hashlib
import logging
from fractions import Fraction
from os.path import basename

import PIL.ExifTags
from django.core.files.images import ImageFile
from PIL import Image as PILImage
from PIL import TiffImagePlugin
from PIL.IptcImagePlugin import getiptcinfo
from wagtail.images import get_image_model

logger = logging.getLogger(__name__)


def imagefile_to_model(image_file: ImageFile):
    """
    Converts an ImageFile to our image model.
    """
    ImageModel = get_image_model()

    with image_file.open(mode="rb") as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()

        try:
            image, created = ImageModel.objects.get_or_create(
                file_hash=file_hash,
                defaults={"title": basename(image_file.name), "file": image_file},
            )
            return image
        except ImageModel.MultipleObjectsReturned:
            logger.error(
                "Multiple versions of %s (%s) found. Returning the first one found.",
                basename(image_file.name),
                file_hash,
            )
            return ImageModel.objects.filter(file_hash=file_hash).first()


def parse_iptc(image_file: ImageFile) -> dict:
    """
    Extracts IPTC data from an image (tiff, jpeg). For more inforation see:
        https://www.iptc.org/std/IIM/3.0/specification/IIMV3.PDF
    """
    try:
        image = PILImage.open(image_file)
        iptc = getiptcinfo(image)
    except FileNotFoundError as fnfe:
        logger.warning(fnfe)
        return {}
    except ValueError as ve:
        logger.warning(ve)
        return {}

    iptc_dict = {}

    if not iptc:
        logger.info("Image did not contain IPTC data.")
        return iptc_dict

    def decode(v):
        if isinstance(v, bytes):
            return bytes.decode(v)
        elif isinstance(v, list):
            return [decode(item) for item in v]
        elif isinstance(v, str):
            return v

    # fmt: off
    for k, v in iptc.items():
        if k == (2, 5,):
            iptc_dict["object_name"] = decode(v)
        elif k == (2, 7,):
            iptc_dict["edit_status"] = decode(v)
        elif k == (2, 25,):
            iptc_dict["keywords"] = decode(v)
        elif k == (2, 30,):
            iptc_dict["release_date"] = decode(v)
        elif k == (2, 35,):
            iptc_dict["release_time"] = decode(v)
        elif k == (2, 37,):
            iptc_dict["expiration_date"] = decode(v)
        elif k == (2, 38,):
            iptc_dict["expiration_time"] = decode(v)
        elif k == (2, 40,):
            iptc_dict["instructions"] = decode(v)
        elif k == (2, 40,):
            iptc_dict["instructions"] = decode(v)
        elif k == (2, 42,):
            iptc_dict["action_advised"] = decode(v)
        elif k == (2, 80,):
            iptc_dict["byline"] = decode(v)
        elif k == (2, 85,):
            iptc_dict["byline_title"] = decode(v)
        elif k == (2, 90,):
            iptc_dict["city"] = decode(v)
        elif k == (2, 92,):
            iptc_dict["sub_location"] = decode(v)
        elif k == (2, 95,):
            iptc_dict["province_state"] = decode(v)
        elif k == (2, 100,):
            iptc_dict["country"] = decode(v)
        elif k == (2, 105,):
            iptc_dict["headline"] = decode(v)
        elif k == (2, 110,):
            iptc_dict["credit"] = decode(v)
        elif k == (2, 116,):
            iptc_dict["copyright_notice"] = decode(v)
        elif k == (2, 120,):
            iptc_dict["caption"] = decode(v)
        elif k == (2, 122,):
            iptc_dict["writer_editor"] = decode(v)
    # fmt: on

    return {k: v for k, v in iptc_dict.items() if v}


def parse_exif(image_file: ImageFile):
    """
    Credits/source: https://python.plainenglish.io/reading-a-photographs-exif-data-with-python-and-pillow-a29fceafb761

    Update 2024-03-11, by Thomas Weholt: this will no also return GPS related data.

    Generate a dictionary of dictionaries.
    The outer dictionary keys are the names
    of individual items, eg Make, Model etc.
    The outer dictionary values are themselves
    dictionaries with the following keys:
        tag: the numeric code for the item names
        raw: the data as stored in the image, often
        in a non-human-readable format
        processed: the raw data if it is human-readable,
        or a processed version if not.
    """
    def clean_up_exif_dict(exif_dict: dict) -> dict:
        def cast(v):
            if isinstance(v, TiffImagePlugin.IFDRational):
                return float(v)
            elif isinstance(v, str):
                return v.rstrip("\x00")
            elif isinstance(v, tuple):
                return tuple(cast(t) for t in v)
            elif isinstance(v, bytes):
                return v.decode(errors="replace").rstrip("\x00")
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    v[kk] = cast(vv)
                return v
            return v

        return {k: cast(v.get("processed")) for k, v in exif_dict.items() if v.get("processed")}

    def get_lat_lon(exif_info):
        "Credit/source: https://gist.github.com/maxbellec/dbb60d136565e3c4b805931f5aad2c6d"

        def convert_to_degrees(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)

        try:
            gps_latitude = exif_info[34853][2]
            gps_latitude_ref = exif_info[34853][1]
            gps_longitude = exif_info[34853][4]
            gps_longitude_ref = exif_info[34853][3]
            lat = convert_to_degrees(gps_latitude)
            if gps_latitude_ref != "N":
                lat *= -1

            lon = convert_to_degrees(gps_longitude)
            if gps_longitude_ref != "E":
                lon *= -1
            return lat, lon
        except KeyError:
            return None, None

    try:
        image = PILImage.open(image_file)
        exif_data_PIL = image._getexif()
        if not exif_data_PIL:
            return {}

        tags = {**PIL.ExifTags.TAGS}
        exif_data = {}

        for k, v in tags.items():
            value = k in exif_data_PIL and exif_data_PIL[k]
            if len(str(value)) > 64:
                value = str(value)[:65] + "..."
            exif_data[v] = {"tag": k, "raw": value, "processed": value}

        lat, lon = get_lat_lon(exif_data_PIL)
        exif_data.update({"latitude": {'processed': lat}, "longitude": {'processed': lon}})
        exif_data = _process_exif_dict(exif_data)
        return clean_up_exif_dict(exif_data)
    except IOError as ioe:
        raise ioe


def _derationalize(rational):
    return rational.numerator / rational.denominator


def _create_lookups():

    lookups = {}
    lookups["metering_modes"] = (
        "Undefined",
        "Average",
        "Center-weighted average",
        "Spot",
        "Multi-spot",
        "Multi-segment",
        "Partial",
    )

    lookups["exposure_programs"] = (
        "Undefined",
        "Manual",
        "Program AE",
        "Aperture-priority AE",
        "Shutter speed priority AE",
        "Creative (Slow speed)",
        "Action (High speed)",
        "Portrait ",
        "Landscape",
        "Bulb",
    )

    lookups["resolution_units"] = ("", "Undefined", "Inches", "Centimetres")
    lookups["orientations"] = (
        "",
        "Horizontal",
        "Mirror horizontal",
        "Rotate 180",
        "Mirror vertical",
        "Mirror horizontal and rotate 270 CW",
        "Rotate 90 CW",
        "Mirror horizontal and rotate 90 CW",
        "Rotate 270 CW",
    )
    return lookups


def _process_exif_dict(exif_dict: dict, date_format: str = "%Y:%m:%d %H:%M:%S"):
    """
    Internal method parsing the exif data info more human readable form.
    """
    lookups = _create_lookups()

    exif_dict["DateTime"]["processed"] = datetime.datetime.strptime(exif_dict["DateTime"]["raw"], date_format)
    exif_dict["DateTimeOriginal"]["processed"] = datetime.datetime.strptime(
        exif_dict["DateTimeOriginal"]["raw"], date_format
    )
    exif_dict["DateTimeDigitized"]["processed"] = datetime.datetime.strptime(
        exif_dict["DateTimeDigitized"]["raw"], date_format
    )
    exif_dict["FNumber"]["processed"] = _derationalize(exif_dict["FNumber"]["raw"])
    exif_dict["FNumber"]["processed"] = "f{}".format(exif_dict["FNumber"]["processed"])
    exif_dict["MaxApertureValue"]["processed"] = _derationalize(exif_dict["MaxApertureValue"]["raw"])
    exif_dict["MaxApertureValue"]["processed"] = "f{:2.1f}".format(exif_dict["MaxApertureValue"]["processed"])
    exif_dict["FocalLength"]["processed"] = _derationalize(exif_dict["FocalLength"]["raw"])
    exif_dict["FocalLength"]["processed"] = "{}mm".format(exif_dict["FocalLength"]["processed"])
    exif_dict["FocalLengthIn35mmFilm"]["processed"] = "{}mm".format(exif_dict["FocalLengthIn35mmFilm"]["raw"])
    exif_dict["Orientation"]["processed"] = lookups["orientations"][exif_dict["Orientation"]["raw"]]
    exif_dict["ResolutionUnit"]["processed"] = lookups["resolution_units"][exif_dict["ResolutionUnit"]["raw"]]
    exif_dict["ExposureProgram"]["processed"] = lookups["exposure_programs"][exif_dict["ExposureProgram"]["raw"]]
    exif_dict["MeteringMode"]["processed"] = lookups["metering_modes"][exif_dict["MeteringMode"]["raw"]]
    exif_dict["XResolution"]["processed"] = int(_derationalize(exif_dict["XResolution"]["raw"]))
    exif_dict["YResolution"]["processed"] = int(_derationalize(exif_dict["YResolution"]["raw"]))
    exif_dict["ExposureTime"]["processed"] = _derationalize(exif_dict["ExposureTime"]["raw"])
    exif_dict["ExposureTime"]["processed"] = str(
        Fraction(exif_dict["ExposureTime"]["processed"]).limit_denominator(8000)
    )
    exif_dict["ExposureBiasValue"]["processed"] = _derationalize(exif_dict["ExposureBiasValue"]["raw"])
    exif_dict["ExposureBiasValue"]["processed"] = "{} EV".format(exif_dict["ExposureBiasValue"]["processed"])

    return exif_dict
