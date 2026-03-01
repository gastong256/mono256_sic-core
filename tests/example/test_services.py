import pytest
from django.core.exceptions import ValidationError

from apps.example.models import Item
from apps.example.services import create_item


@pytest.mark.django_db
class TestCreateItem:
    def test_creates_item_with_name(self) -> None:
        item = create_item(name="Widget")
        assert item.pk is not None
        assert item.name == "Widget"
        assert item.description == ""
        assert Item.objects.filter(pk=item.pk).exists()

    def test_creates_item_with_description(self) -> None:
        item = create_item(name="Widget", description="A useful widget.")
        assert item.description == "A useful widget."

    def test_persists_to_database(self) -> None:
        item = create_item(name="Persisted")
        fetched = Item.objects.get(pk=item.pk)
        assert fetched.name == "Persisted"

    def test_raises_on_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            create_item(name="")

    def test_name_max_length(self) -> None:
        with pytest.raises(ValidationError):
            create_item(name="x" * 256)
