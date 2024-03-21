# Generated by Django 5.0.3 on 2024-03-17 14:20

import django.db.models.deletion
import wagtail.images.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailimagecaptions", "0006_captionedexifimage_captionedexifrendition"),
    ]

    operations = [
        migrations.AlterField(
            model_name="captionedexifimage",
            name="aperture",
            field=models.CharField(blank=True, help_text="The aperture used (e.g. f/1.8, f/4).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="camera_make",
            field=models.CharField(blank=True, help_text="The name of the camera make (e.g. Fujifilm, Sony, Canon).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="camera_model",
            field=models.CharField(blank=True, help_text="The name of the camera model (e.g. X100V, 70D).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="date_time_original",
            field=models.DateTimeField(blank=True, help_text="The date and time of creation of the image (EXIF DateTimeOriginal)", null=True),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="focal_length",
            field=models.CharField(blank=True, help_text="The focal length in millimeters (e.g. 33mm, 200mm).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="iso_rating",
            field=models.CharField(blank=True, help_text="The ISO rating (e.g. 400 ISO, 800 ISO).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="latitude",
            field=models.FloatField(blank=True, help_text="The latitude (e.g. ?).", null=True),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="lens_make",
            field=models.CharField(blank=True, help_text="The name of the lens make (e.g. Fujinon, Nikkor).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="lens_model",
            field=models.CharField(blank=True, help_text="The name of the lens model (e.g. XF 33mm f/1.4 R LM WR, Sony FE 24mm f/1.4 GM).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="longitude",
            field=models.FloatField(blank=True, help_text="The longitude (e.g. ?).", null=True),
        ),
        migrations.AlterField(
            model_name="captionedexifimage",
            name="shutter_speed",
            field=models.CharField(blank=True, help_text="The shutter speed in seconds (e.g. 1/1000 sec, 1/15 sec).", max_length=255),
        ),
        migrations.AlterField(
            model_name="captionedexifrendition",
            name="file",
            field=wagtail.images.models.WagtailImageField(
                height_field="height", storage=wagtail.images.models.get_rendition_storage, upload_to=wagtail.images.models.get_rendition_upload_to, width_field="width"
            ),
        ),
        migrations.AlterField(
            model_name="captionedexifrendition",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="captionedexifrendition",
            name="image",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="exif_renditions", to="wagtailimagecaptions.captionedexifimage"),
        ),
    ]