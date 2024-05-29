from django.db import models
from wagtail.models import Page
from wagtail.images import get_image_model
from wagtail.admin.panels import FieldPanel

Image = get_image_model()


class TestPage(Page):
    cover = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    content_panels = Page.content_panels + [
        FieldPanel("cover"),
    ]
