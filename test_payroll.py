import pytest
from decimal import Decimal

from payroll import calculate_salary, validate_amount


def test_basic_salary():
    result = calculate_salary(30000)

    assert result["gross_salary"] == Decimal("30000.00")
    assert result["net_salary"] == Decimal("30000.00")


def test_salary_with_allowances():
    result = calculate_salary(30000, 8000, 2000, 3000)

    assert result["gross_salary"] == Decimal("40000.00")
    assert result["net_salary"] == Decimal("37000.00")


def test_zero_salary():
    result = calculate_salary(0, 0, 0, 0)

    assert result["net_salary"] == Decimal("0.00")


def test_decimal_precision():
    result = calculate_salary(
        "30000.50",
        "8000.25",
        "2000.10",
        "3000.35"
    )

    assert result["gross_salary"] == Decimal("40000.85")
    assert result["net_salary"] == Decimal("37000.50")


def test_negative_salary_rejected():
    with pytest.raises(ValueError):
        calculate_salary(-1000)


def test_negative_allowance_rejected():
    with pytest.raises(ValueError):
        calculate_salary(30000, allowances=-500)


def test_excessive_deductions_rejected():
    with pytest.raises(ValueError):
        calculate_salary(10000, deductions=15000)


def test_invalid_salary_rejected():
    with pytest.raises(ValueError):
        calculate_salary("invalid")


def test_more_than_two_decimal_places_rejected():
    with pytest.raises(ValueError):
        calculate_salary("30000.123")


def test_infinite_amount_rejected():
    with pytest.raises(ValueError):
        calculate_salary("Infinity")


def test_boolean_amount_rejected():
    with pytest.raises(ValueError):
        calculate_salary(True)


def test_maximum_amount_limit():
    with pytest.raises(ValueError):
        validate_amount("10000000000", "Basic salary")
