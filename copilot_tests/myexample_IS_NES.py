TAX = 20

def calculate_price(price, tax):
    subtotal = price
    total = subtotal + tax
    return total


def print_receipt(amount):
    print("Total amount:", amount)


if __name__ == "__main__":
    result = calculate_price(100, TAX)
    print_receipt(result)
    