import os
import pandas as pd
import numpy as np
from pandas.tseries.offsets import BDay

PERIOD = 3
LOT = 25000
GAIN_CAP = 0.1
INCLUDE_RISK_FREE = False
HOLDING_PERIOD_CAP = 5  # business days


# HISTORICAL MARKET DATA
def load_data(period=PERIOD):
    file_path = os.getenv("ITA_DATA_PATH")
    hist = pd.read_csv(f'{file_path}\data.csv', parse_dates=True, index_col='Date')
    risk_free_hist = pd.read_csv(f"{file_path}\\risk_free.csv", parse_dates=True, index_col='Date')

    risk_free_hist['interest_rate'] = risk_free_hist['interest_rate'] / 100
    hist = hist.iloc[::-1]
    hist['log_ret_AMZN'] = np.log(hist['amzn_Close']) - np.log(hist['amzn_Close'].shift(1))
    hist['log_ret_WMT'] = np.log(hist['wmt_Close']) - np.log(hist['wmt_Close'].shift(1))
    hist['corr_coef'] = hist['amzn_Close'].rolling(period).corr(hist['wmt_Close'])
    hist = hist.merge(risk_free_hist, how='left', on='Date')
    return hist


# GET POSITION DIRECTION

# This is another logic to decide if we should go long or short
# It's only based on the number of negative returns in a period of time (no tie-breaker)
def get_position_direction(slice_hist):
    amzn_neg_count = np.sum((slice_hist['log_ret_AMZN'].values < 0))
    wmt_neg_count = np.sum((slice_hist['log_ret_WMT'].values < 0))
    amzn_direction = 'BUY' if (amzn_neg_count >= wmt_neg_count) else 'SELL'
    wmt_direction = 'SELL' if (amzn_direction == 'BUY') else 'BUY'
    return {'AMZN': amzn_direction, 'WMT': wmt_direction}


# This logic decides if we should go long or short
# It's based on the volume of stocks that had negative returns (it's tie-breaker)
def get_position_direction2(slice_hist):
    amzn_total_volume = slice_hist['amzn_Volume'].sum()
    amz_negative_volume = np.where(slice_hist['log_ret_AMZN'] < 0, slice_hist['amzn_Volume'], 0).sum()
    amz_negative_pct = amz_negative_volume / amzn_total_volume

    wmt_total_volume = slice_hist['wmt_Volume'].sum()
    wmt_negative_volume = np.where(slice_hist['log_ret_WMT'] < 0, slice_hist['wmt_Volume'], 0).sum()
    wmt_negative_pct = wmt_negative_volume / wmt_total_volume

    amzn_direction = 'BUY' if (amz_negative_pct >= wmt_negative_pct) else 'SELL'
    wmt_direction = 'SELL' if (amzn_direction == 'BUY') else 'BUY'

    return {'AMZN': amzn_direction, 'WMT': wmt_direction}


# CREATE ENTRY TRADES
def create_entry_trades(hist, biz_date, period, lot_lcl):
    from_date = biz_date - BDay(period - 1)
    to_date = biz_date
    slice_hist = hist.loc[from_date: to_date, :]

    trade_date = hist[hist.index > biz_date].index[0]  # get next date
    pos_direction = get_position_direction2(slice_hist)
    amzn_open_price = hist.loc[trade_date]['amzn_Open']
    amzn_size = lot_lcl / amzn_open_price
    wmt_open_price = hist.loc[trade_date]['wmt_Open']
    wmt_size = lot_lcl / wmt_open_price

    amzn_entry_trade = {
        "Date": trade_date,
        "Symbol": 'AMZN',
        "Trip": 'ENTRY',
        "Action": pos_direction['AMZN'],
        "Price": amzn_open_price,
        "Size": round(amzn_size, 4),  # rounding based on IB's minimum fractional size
        "Status": 'FILLED'
    }
    wmt_entry_trade = {
        "Date": trade_date,
        "Symbol": 'WMT',
        "Trip": 'ENTRY',
        "Action": pos_direction['WMT'],
        "Price": wmt_open_price,
        "Size": round(wmt_size, 4),
        "Status": 'FILLED'
    }
    return pd.DataFrame([amzn_entry_trade, wmt_entry_trade])


# CREATE EXIT TRADES

# The exit trades are LMT orders created right after entry trades with "Date" as the expiration date
def create_exit_trade(hist, entry_trades, symbol, gain_cap, include_risk_free, holding_period_cap):
    entry_data = entry_trades[entry_trades['Symbol'] == symbol].reset_index()
    entry_date = entry_data.at[0, 'Date']
    exit_date = entry_date + BDay(holding_period_cap)

    entry_action = entry_data.at[0, 'Action']
    exit_action = 'SELL' if entry_action == 'BUY' else 'BUY'

    entry_price = entry_data.at[0, 'Price']
    exit_price = None
    risk_free = hist.loc[entry_date]['interest_rate']
    if exit_action == 'SELL':
        exit_price = entry_price * (1 + gain_cap + risk_free) if include_risk_free else entry_price * (
                1 + gain_cap)
    else:
        exit_price = entry_price * (1 - gain_cap - risk_free) if include_risk_free else entry_price * (
                1 - gain_cap)

    exit_size = entry_data.at[0, 'Size']

    return {
        "Date": exit_date,
        "Symbol": symbol,
        "Trip": 'EXIT',
        "Action": exit_action,
        "Price": round(exit_price, 2),
        "Size": exit_size,
        "Status": 'PENDING'
    }


def create_exit_trades(hist, entry_trades, gain_cap, include_risk_free, holding_period_cap):
    amzn_exit_trade = create_exit_trade(hist, entry_trades, 'AMZN', gain_cap, include_risk_free, holding_period_cap)
    wmt_exit_trade = create_exit_trade(hist, entry_trades, 'WMT', gain_cap, include_risk_free, holding_period_cap)
    return pd.DataFrame([amzn_exit_trade, wmt_exit_trade])


# The forced trades are MKT orders created when the exit trades are not filled within the holding period cap.
# It uses the Close Price of the next day following the exit trade's date
def create_forced_trade(biz_date, symbol, action, size, market_data):
    column_prefix = symbol.lower()
    close_price_column_name = f"{column_prefix}_Close"
    return {
        "Date": biz_date,
        "Symbol": symbol,
        "Trip": 'EXIT',
        "Action": action,
        "Price": market_data[close_price_column_name],
        "Size": size,
        "Status": 'FORCED'
    }


def should_force_close_position(position, biz_date):
    if position['Date'] < biz_date:
        return True


def should_close_position(hist, position, biz_date):
    column_prefix = position['Symbol'].lower()
    high_price_column_name = f"{column_prefix}_High"
    low_price_column_name = f"{column_prefix}_Low"
    if position['Action'] == 'SELL' and hist.loc[biz_date][high_price_column_name] >= position['Price']:
        return True
    if position['Action'] == 'BUY' and hist.loc[biz_date][low_price_column_name] <= position['Price']:
        return True
    return False


# RUN BACK TEST
def run_backtest(hist, period=PERIOD, lot=LOT, gain_cap=GAIN_CAP, include_risk_free=INCLUDE_RISK_FREE,
                 holding_period_cap=HOLDING_PERIOD_CAP):
    blotter = pd.DataFrame(
        columns=['Date', 'Symbol', 'Trip', 'Action', 'Price', 'Size', 'Status'])
    for index, today_market_data in hist.iterrows():
        business_date = index
        pending_exit_trades = blotter[(blotter['Trip'] == 'EXIT') & (blotter['Status'] == 'PENDING')]
        current_position_status = 'CLOSED' if pending_exit_trades.empty else 'OPEN'

        if current_position_status == 'CLOSED' and today_market_data['corr_coef'] < 0:
            entry_trades = create_entry_trades(hist, business_date, period, lot)
            blotter = pd.concat([blotter, entry_trades], ignore_index=True)

            exit_trades = create_exit_trades(hist, entry_trades, gain_cap, include_risk_free, holding_period_cap)
            blotter = pd.concat([blotter, exit_trades], ignore_index=True)
        elif current_position_status == 'OPEN':
            for i, pending_trade in pending_exit_trades.iterrows():
                if should_force_close_position(pending_trade, business_date):
                    blotter.at[i, 'Status'] = 'CANCELED'
                    forced_trade = create_forced_trade(business_date,
                                                       pending_trade['Symbol'],
                                                       pending_trade['Action'],
                                                       pending_trade['Size'],
                                                       today_market_data)
                    blotter = pd.concat([blotter, pd.DataFrame([forced_trade])], ignore_index=True)
                elif should_close_position(hist, pending_trade, business_date):
                    blotter.at[i, 'Status'] = 'FILLED'
    return blotter


# RESULT & STATS
def calculate_gain_loss(symbol, blotter, messages):
    results = blotter[(blotter['Status'] != 'CANCELED') & (blotter['Symbol'] == symbol)].copy()
    results['Total_Price'] = results['Price'] * results['Size']
    sells = results[results['Action'] == 'SELL'].copy()
    buys = results[results['Action'] == 'BUY'].copy()

    total_sales = sells['Total_Price'].sum()
    total_purchases = buys['Total_Price'].sum()
    gain_loss = total_sales - total_purchases

    messages.append(f"\n******  {symbol}  ******")
    messages.append(f'Total Sales: ${round(total_sales, 2):,}')
    messages.append(f'Total Purchases: ${round(total_purchases, 2):,}')
    messages.append(f'Gain or Loss: ${round(gain_loss, 2):,}')
    return gain_loss


def get_stats(hist, blotter):
    order_messages = []
    order_messages.append(f"******  Orders  ******")
    order_messages.append(f"Entry Orders: {blotter[(blotter['Trip'] == 'ENTRY') & (blotter['Status'] == 'FILLED')].shape[0]}")
    order_messages.append(
        f"Filled Exit Orders: {blotter[(blotter['Trip'] == 'EXIT') & (blotter['Status'] == 'FILLED')].shape[0]}")
    order_messages.append(
        f"Canceled Exit Orders: {blotter[(blotter['Trip'] == 'EXIT') & (blotter['Status'] == 'CANCELED')].shape[0]}")
    order_messages.append(
        f"Forced Exit Orders: {blotter[(blotter['Trip'] == 'EXIT') & (blotter['Status'] == 'FORCED')].shape[0]}")

    amzn_messages = []
    amz_gain_loss = calculate_gain_loss('AMZN', blotter, amzn_messages)
    wmt_messages = []
    wmt_gain_loss = calculate_gain_loss('WMT', blotter, wmt_messages)
    total_gain_loss = amz_gain_loss + wmt_gain_loss
    time_period = hist.last_valid_index() - hist.first_valid_index()
    years = round(time_period.days / 365.2425, 2)
    total_gain_loss_per_year = total_gain_loss / years

    gain_loss_messages = []
    gain_loss_messages.append(f"******  Total Gain/Loss  ******")
    gain_loss_messages.append(f"\nYears: {years}")
    gain_loss_messages.append(f'Total Gain or Loss: ${round(total_gain_loss, 2):,}')
    gain_loss_messages.append(f"Total Gain or Loss Per Year: ${round(total_gain_loss_per_year, 2):,}")
    print()
    return [order_messages, amzn_messages, wmt_messages, gain_loss_messages]
