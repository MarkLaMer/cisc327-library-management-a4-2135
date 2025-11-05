from services.library_service import refund_late_fee_payment
from unittest.mock import Mock
from services.payment_service import PaymentGateway

def test_refund_late_fee_success(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Simulate a successful refund operation
    mock_gateway.refund_payment.return_value = (True, "Refund successful")
    result = refund_late_fee_payment("txn_ABC123", amount=5.00, payment_gateway=mock_gateway)
    # Function should return success True and the success message
    assert result == (True, "Refund successful")
    # Verify that refund_payment was called once with correct arguments
    mock_gateway.refund_payment.assert_called_once_with("txn_ABC123", 5.00)

def test_refund_late_fee_invalid_transaction_id(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Use an invalid transaction_id (does not start with "txn_")
    result = refund_late_fee_payment("123ABC", amount=5.00, payment_gateway=mock_gateway)
    # Expect an error message and False success
    assert result == (False, "Invalid transaction ID.")
    mock_gateway.refund_payment.assert_not_called()  # Gateway should not be called

def test_refund_late_fee_invalid_amount_zero(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Amount = 0 is not allowed
    result = refund_late_fee_payment("txn_12345", amount=0, payment_gateway=mock_gateway)
    assert result == (False, "Refund amount must be greater than 0.")
    mock_gateway.refund_payment.assert_not_called()

def test_refund_late_fee_invalid_amount_negative(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    result = refund_late_fee_payment("txn_99999", amount=-10.0, payment_gateway=mock_gateway)
    assert result == (False, "Refund amount must be greater than 0.")
    mock_gateway.refund_payment.assert_not_called()

def test_refund_late_fee_amount_exceeds_max(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Amount greater than $15 should be rejected
    result = refund_late_fee_payment("txn_XYZ789", amount=20.00, payment_gateway=mock_gateway)
    assert result == (False, "Refund amount exceeds maximum late fee.")
    mock_gateway.refund_payment.assert_not_called()

def test_refund_late_fee_gateway_failure(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Simulate the gateway returning a failure response
    mock_gateway.refund_payment.return_value = (False, "Transaction not found")
    result = refund_late_fee_payment("txn_FAIL1", amount=5.00, payment_gateway=mock_gateway)
    # Function should return False and prepend "Refund failed: " to the gateway message
    assert result == (False, "Refund failed: Transaction not found")
    mock_gateway.refund_payment.assert_called_once_with("txn_FAIL1", 5.00)

def test_refund_late_fee_gateway_exception(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    # Simulate an exception being raised by the payment gateway
    mock_gateway.refund_payment.side_effect = Exception("Gateway error")
    result = refund_late_fee_payment("txn_EXC1", amount=3.00, payment_gateway=mock_gateway)
    # The function should catch the exception and return a formatted error message
    assert result == (False, "Refund processing error: Gateway error")
    mock_gateway.refund_payment.assert_called_once_with("txn_EXC1", 3.00)
