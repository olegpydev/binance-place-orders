import logging
import os
from pprint import pprint
from random import random

from binance.error import ClientError
from binance.lib.utils import config_logging
from binance.spot import Spot as Client
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")
BINANCE_TEST_API_KEY = os.environ.get("BINANCE_TEST_API_KEY")
BINANCE_TEST_SECRET_KEY = os.environ.get("BINANCE_TEST_SECRET_KEY")

BINANCE_TESTNET = True

config_logging(logging, logging.INFO)

PAIR = "BNBBUSD"


def get_client():
    if BINANCE_TESTNET:
        client = Client(BINANCE_TEST_API_KEY, BINANCE_TEST_SECRET_KEY, base_url="https://testnet.binance.vision")
    else:
        client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    return client


def get_filter(symbol: str, filter_name: str) -> dict:
    client = get_client()
    try:
        data_from_api = client.exchange_info()
        symbol_info = next(filter(lambda x: x["symbol"] == symbol, data_from_api["symbols"]))
        return next(filter(lambda x: x["filterType"] == filter_name, symbol_info["filters"]))
    except ClientError as error:
        error_msg = "Found error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
        logging.error(error_msg)
        return {"error": error.error_message,
                "error_code": error.error_code}


def place_order(pair: str, side: str, quantity: float, price: float) -> dict:
    """
    Создает ордер в Binance

    :param pair: Торговая пара
    :param side: "BUY" / "SELL"
    :param quantity: Количество
    :param price: Цена
    :return: созданный ордер или ошибка
    """
    params = {
        "symbol": pair,
        "side": side,
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": price,
    }
    client = get_client()
    try:
        response = client.new_order(**params)
        logging.info(response)
        return response
    except ClientError as error:
        error_msg = "Found error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
        logging.error(error_msg)
        return {"error": error.error_message,
                "error_code": error.error_code}


def place_orders(data: dict) -> list[dict]:
    """
    Принимает на вход словарь:

    {"volume": float, "number": int, "amountDif": float, "side": str, "priceMin": float, "priceMax": float}

    Создает number ордеров с общим объемом volume, каждый из которых имеет цену в диапазоне
    от priceMin до priceMax, и разброс объема каждого ордера amountDif.

    Возвращает список созданных ордеров.
    """
    volume = data["volume"]
    number = data["number"]
    amount_dif = data["amountDif"]
    side = data["side"]
    price_min = data["priceMin"]
    price_max = data["priceMax"]
    pair = PAIR

    result = []

    price_filter = get_filter(pair, "PRICE_FILTER")
    if "tickSize" in price_filter:
        tick_size = price_filter["tickSize"].rstrip("0").count("0")
    else:
        return [price_filter]  # Binance error

    lot_size = get_filter(pair, "LOT_SIZE")
    if "stepSize" in lot_size:
        step_size = lot_size["stepSize"].rstrip("0").count("0")
    else:
        return [price_filter]  # Binance error

    def get_random_price():
        return round(price_min + random() * (price_max - price_min), tick_size)

    part = volume / number
    surplus = 0
    total = 0
    for _ in range(number - 1):
        shift = float("inf")
        while abs(shift) > amount_dif:
            shift = random() * amount_dif * 2 - amount_dif + surplus
        surplus -= shift

        price = get_random_price()
        quantity = round((part + shift) / price, step_size)
        order = place_order(side=side, pair=pair, quantity=quantity, price=price)
        if "error" in order:
            result.append(order)
            return result  # Binance error
        total += quantity * price
        result.append(order)

    quantity = float("inf")
    price = 1
    while total + quantity * price > volume or abs(quantity * price - part) > amount_dif:
        price = get_random_price()
        quantity = round((volume - total) / price, step_size)
    order = place_order(side=side, pair=pair, quantity=quantity, price=price)
    result.append(order)
    return result


def cancel_open_orders() -> list[dict]:
    """
    Функция закрывает все открытые ордера, возвращает список закрытых ордеров
    """
    client = get_client()
    try:
        results = []
        symbols = (client.exchange_info())["symbols"]
        for symbol in symbols:
            s = symbol["symbol"]
            orders = client.get_open_orders(symbol=s)
            for order in orders:
                res = client.cancel_order(symbol=s, orderId=order["orderId"])
                results.append(res)
        return results
    except ClientError as error:
        error_msg = "Found error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
        logging.error(error_msg)
        return [{"error": error.error_message,
                "error_code": error.error_code}]


def main():
    res = place_orders({
        "volume": 10000.0,  # Объем в долларах
        "number": 5,  # На сколько ордеров нужно разбить этот объем
        "amountDif": 50.0,  # Разброс в долларах, в пределах которого случайным образом выбирается объем в
        # верхнюю и нижнюю сторону
        "side": "BUY",  # Сторона торговли (SELL или BUY)
        "priceMin": 200.0,  # Нижний диапазон цены, в пределах которого нужно случайным образом выбрать цену
        "priceMax": 300.0  # Верхний диапазон цены, в пределах которого нужно случайным образом выбрать цену
    })

    pprint(res)
    print(sum(float(i["origQty"]) * float(i["price"]) for i in res if "origQty" in i))

    pprint(cancel_open_orders())


if __name__ == "__main__":
    main()
