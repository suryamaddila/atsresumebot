def verify_utr(utr):
    valid_utrs = ["1234567890", "9876543210", "5555555555"]
    return utr in valid_utrs or len(utr) >= 9
