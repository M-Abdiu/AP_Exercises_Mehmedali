from bank_transfer_payment import BankTransferPayment
from credit_card_payment import CreditCardPayment
from paypal_payment import PayPalPayment

if __name__ == "__main__":
    payments = [
        CreditCardPayment(50, "1234-5678-9012-3456"),
        PayPalPayment(25, "user@email.com"),
        BankTransferPayment(100, "CH9300762011623852957"),
    ]

    for payment in payments:
        print(payment.process_payment())
