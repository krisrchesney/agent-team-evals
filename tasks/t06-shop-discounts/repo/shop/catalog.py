"""Look items up by SKU."""


class UnknownSku(KeyError):
    pass


class Catalog:
    def __init__(self, items):
        self._items = {item.sku: item for item in items}

    def get(self, sku):
        try:
            return self._items[sku]
        except KeyError:
            raise UnknownSku(sku) from None

    def __contains__(self, sku):
        return sku in self._items

    def __len__(self):
        return len(self._items)
