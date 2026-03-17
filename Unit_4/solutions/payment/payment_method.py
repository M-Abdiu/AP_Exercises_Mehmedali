from abc import ABC, abstractmethod


class PaymentMethod(ABC):
    def __init__(self, amount: float) -> None:
        self.amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    @amount.setter
    def amount(self, value: float) -> None:
        amount = float(value)
        if amount <= 0:
            raise ValueError("amount must be greater than 0")
        self._amount = amount

    @abstractmethod
    def process_payment(self) -> str:
        raise NotImplementedError
