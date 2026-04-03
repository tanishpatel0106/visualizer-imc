# Strategy Interface

## Built-in
Built-ins implement internal signal/threshold contract with typed parameter schemas surfaced via `/strategies`.

## Uploaded Prosperity-style
Upload a Python file with:

```python
class Trader:
    def run(self, state):
        return orders, conversions, trader_data
```

`orders` is a list of dictionaries containing: `product`, `side`, `price`, `quantity`.
