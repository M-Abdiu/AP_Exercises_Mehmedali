from datetime import datetime


def convert_to_iso(date_str: str) -> str:
    """Convert a date string from DD/MM/YYYY format to ISO format YYYY-MM-DD."""
    dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
    return dt.strftime("%Y-%m-%d")


def main():
    print("Date converter: DD/MM/YYYY  →  YYYY-MM-DD (ISO 8601)")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("Enter date (DD/MM/YYYY): ")
        if user_input.lower() == "quit":
            break
        try:
            iso_date = convert_to_iso(user_input)
            print(f"ISO date: {iso_date}\n")
        except ValueError:
            print("Invalid date. Please use the format DD/MM/YYYY (e.g. 01/02/2026).\n")


if __name__ == "__main__":
    main()
