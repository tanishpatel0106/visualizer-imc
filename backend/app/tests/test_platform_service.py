from app.services.platform_service import PlatformService


def test_snapshots_json_safe_nan(tmp_path):
    prices = tmp_path / 'prices_round_0_day_-2.csv'
    trades = tmp_path / 'trades_round_0_day_-2.csv'
    prices.write_text(
        'day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss\n'
        '-2;0;EMERALDS;9992;14;9990;29;;;10008;14;10010;29;;;10000.0;0.0\n'
    )
    trades.write_text('timestamp;buyer;seller;symbol;currency;price;quantity\n3200;;;EMERALDS;XIRECS;9992.0;8\n')
    svc = PlatformService()
    svc.load_dataset('x', str(tmp_path))
    rows = svc.snapshots(product='EMERALDS', day=-2)
    assert rows
    assert rows[0]['bid_price_3'] is None
    assert rows[0]['ask_price_3'] is None
