import math

def price(product, inv):
    base_prices = {
        "WHEAT": 25.0, "MELON": 250.0, "STRAWBERRY": 12.0, "TOMATO": 50.0, "CARROT": 20.0,
        "MILK": 45.0, "WOOL": 60.0, "EGG": 25.0, "WOOD": 20.0
    }
    return base_prices.get(product, 10.0) * (0.98 ** (inv / 100.0))

print("Melon price at inv=0:", price("MELON", 0))
print("Melon price at inv=600:", price("MELON", 600))
print("Melon price at inv=1000:", price("MELON", 1000))
print("Strawberry price at inv=0:", price("STRAWBERRY", 0))
print("Strawberry price at inv=6000:", price("STRAWBERRY", 6000))
print("Milk price at inv=0:", price("MILK", 0))
print("Milk price at inv=3000:", price("MILK", 3000))
