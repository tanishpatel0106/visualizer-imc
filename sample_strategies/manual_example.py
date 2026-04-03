class Trader:
    def run(self, state):
        orders = []
        mid = state.get("mid", 0)
        if state.get("best_bid") and state.get("best_ask"):
            if state.get("position", 0) <= 0:
                orders.append({"product": state["product"], "side": "BUY", "price": state["best_ask"], "quantity": 1})
            else:
                orders.append({"product": state["product"], "side": "SELL", "price": state["best_bid"], "quantity": 1})
        return orders, 0, {"mid": mid}
