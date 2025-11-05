import pytest
from unittest.mock import Mock
# Import the functions and PaymentGateway class from the library service module
import services.library_service as svc
from services.library_service import pay_late_fees, PaymentGateway

def test_pay_late_fees_successful_payment(mocker):
    # Stub external dependencies: calculate late fee returns a positive fee, book lookup returns a title
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 5.00, "days_overdue": 10})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Test Book"})
    # Create a mock PaymentGateway and configure process_payment to simulate a successful payment
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_12345", "Success")
    # Call the function under test
    success, message, transaction_id = pay_late_fees("123456", book_id=1, payment_gateway=mock_gateway)
    # Validate outcomes
    assert success is True
    assert transaction_id == "txn_12345"
    assert "Payment successful" in message  # e.g., "Payment successful! Success"
    # Verify that process_payment was called exactly once with correct arguments
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456", amount=5.00, description="Late fees for 'Test Book'"
    )

def test_pay_late_fees_payment_declined(mocker):
    # Stub dependencies to return a positive late fee and book title
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 2.50, "days_overdue": 5})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Another Book"})
    # Mock the payment gateway to simulate a declined payment (success=False)
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (False, None, "Card declined")
    success, message, transaction_id = pay_late_fees("999999", book_id=42, payment_gateway=mock_gateway)
    # The function should indicate failure and no transaction ID
    assert success is False
    assert transaction_id is None
    assert "Payment failed: Card declined" in message  # includes the gateway's failure message
    # Verify the gateway was still called once with correct parameters
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="999999", amount=2.50, description="Late fees for 'Another Book'"
    )

def test_pay_late_fees_invalid_patron_id(mocker):
    # Even if we stub the dependencies, they should not be used due to early validation failure
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 1.00, "days_overdue": 1})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Book"})
    # Mock gateway (should not be called at all in this scenario)
    mock_gateway = Mock(spec=PaymentGateway)
    # Use an invalid patron_id (not 6 digits) and a valid book_id
    success, message, transaction_id = pay_late_fees("12345", book_id=1, payment_gateway=mock_gateway)
    # Verify it returns an error and does not proceed to payment
    assert success is False
    assert transaction_id is None
    assert message == "Invalid patron ID. Must be exactly 6 digits."
    # Since patron ID was invalid, the payment gateway should never be called
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_no_late_fees(mocker):
    # Stub fee calculation to return zero fee
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 0.0, "days_overdue": 0})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Book"})
    mock_gateway = Mock(spec=PaymentGateway)
    success, message, transaction_id = pay_late_fees("111111", book_id=10, payment_gateway=mock_gateway)
    # If fee_amount is 0, no payment should be processed
    assert success is False
    assert transaction_id is None
    assert message == "No late fees to pay for this book."
    mock_gateway.process_payment.assert_not_called()  # Should not call gateway for zero fee

def test_pay_late_fees_network_error(mocker):
    # Stub a positive fee to ensure the payment gateway will be invoked
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 7.00, "days_overdue": 3})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Network Book"})
    # Configure the mock gateway to raise an exception when process_payment is called
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network timeout")
    success, message, transaction_id = pay_late_fees("222222", book_id=5, payment_gateway=mock_gateway)
    # The function should handle the exception and return a failure result with an error message
    assert success is False
    assert transaction_id is None
    assert message == "Payment processing error: Network timeout"
    # Verify that process_payment was indeed called once (it raised an exception on call)
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="222222", amount=7.00, description="Late fees for 'Network Book'"
    )
