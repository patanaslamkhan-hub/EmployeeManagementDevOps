
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


# ============================================================
# EMPLOYEE PAYROLL - SALARY CALCULATION
# ============================================================

MONEY_PRECISION = Decimal("0.01")
MAX_AMOUNT = Decimal("9999999999.99")


def validate_amount(value, field_name):
    """
    Validate a salary amount and convert it to Decimal.
    Ensures that amounts are non-negative and have
    no more than two decimal places.
    """

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a valid amount.")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            f"{field_name} must be a valid amount."
        ) from None

    if not amount.is_finite():
        raise ValueError(
            f"{field_name} must be a finite amount."
        )

    if amount < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )

    if amount > MAX_AMOUNT:
        raise ValueError(
            f"{field_name} exceeds the allowed limit."
        )

    if amount != amount.quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP
    ):
        raise ValueError(
            f"{field_name} cannot have more than 2 decimal places."
        )

    return amount.quantize(MONEY_PRECISION)


def calculate_salary(
    basic_salary,
    hra=0,
    allowances=0,
    deductions=0
):
    """
    Calculate employee gross and net salary.

    Gross Salary = Basic Salary + HRA + Allowances

    Net Salary = Gross Salary - Deductions
    """

    basic = validate_amount(
        basic_salary, "Basic salary"
    )

    house_rent = validate_amount(
        hra, "HRA"
    )

    other_allowances = validate_amount(
        allowances, "Allowances"
    )

    total_deductions = validate_amount(
        deductions, "Deductions"
    )

    gross_salary = (
        basic + house_rent + other_allowances
    )

    if gross_salary > MAX_AMOUNT:
        raise ValueError(
            "Gross salary exceeds the allowed limit."
        )

    if total_deductions > gross_salary:
        raise ValueError(
            "Deductions cannot exceed gross salary."
        )

    net_salary = (
        gross_salary - total_deductions
    )

    return {
        "basic_salary": basic,
        "hra": house_rent,
        "allowances": other_allowances,
        "deductions": total_deductions,
        "gross_salary": gross_salary,
        "net_salary": net_salary
    }
