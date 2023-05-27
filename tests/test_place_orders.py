from main import cancel_open_orders, place_orders


def test_place_orders():
    volume = 10000.0
    number = 5
    amount_dif = 50.0
    side = "BUY"
    price_min = 200.0
    price_max = 300.0
    data = {
        "volume": volume,  # Объем в долларах
        "number": number,  # На сколько ордеров нужно разбить этот объем
        "amountDif": amount_dif,  # Разброс в долларах, в пределах которого случайным образом выбирается объем в
        # верхнюю и нижнюю сторону
        "side": side,  # Сторона торговли (SELL или BUY)
        "priceMin": price_min,  # Нижний диапазон цены, в пределах которого нужно случайным образом выбрать цену
        "priceMax": price_max  # Верхний диапазон цены, в пределах которого нужно случайным образом выбрать цену
    }

    # Размещаем ордера
    res = place_orders(data=data)

    # Проверка того, что количество размешенных ордеров соответствует заданному
    assert sum(1 for i in res if "origQty" in i) == number

    # Проверка того, что ордера размещены на заданную величину объема,
    # не превышают ее и отклонение в меньшую сторону не более 1%
    volumes = [float(i["origQty"]) * float(i["price"]) for i in res if "origQty" in i]
    total_sum = sum(volumes)
    assert volume * .99 <= total_sum <= volume

    # Проверка того, что все цены ордеров отличаются и находятся в установленных пределах
    prices = set(float(i["price"]) for i in res if "price" in i)
    assert len(set(prices)) == number
    assert min(prices) >= price_min
    assert max(prices) <= price_max

    # Проверка того, что все объемы ордеров отличаются и находятся в заданных пределах отклонения
    assert len(set(volumes)) == number
    assert min(volumes) >= volume / number - amount_dif
    assert max(volumes) <= volume / number + amount_dif

    # Закрываем открытые ордера
    cancel_open_orders()
