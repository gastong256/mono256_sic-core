from .models import Item


def create_item(*, name: str, description: str = "") -> Item:
    item = Item(name=name, description=description)
    item.full_clean()
    item.save()
    return item
