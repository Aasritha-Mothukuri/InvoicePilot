from invoicepilot.agent import validate
def test_valid_invoice():
    x={"invoice_number":"A1","customer_name":"Acme","subtotal":100,"tax_amount":10,"total_amount":110}
    assert validate(x)==[]
def test_missing_fields():
    assert len(validate({"subtotal":10}))>=2
def test_arithmetic_error():
    x={"invoice_number":"A1","customer_name":"Acme","subtotal":100,"tax_amount":10,"total_amount":999}
    assert any("does not equal" in e for e in validate(x))
