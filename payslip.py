
from io import BytesIO
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_payslip_pdf(payroll):
    """
    Generate an employee payslip PDF.

    payroll must contain:
    employee_name, payroll_month, basic_salary,
    hra, allowances, deductions, gross_salary,
    net_salary, payment_status.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    heading_style = ParagraphStyle(
        "PayslipHeading",
        parent=styles["Heading1"],
        fontSize=18,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#253858"),
        spaceAfter=12,
    )

    normal_style = styles["Normal"]

    def money(value):
        return f"INR {Decimal(str(value)):,.2f}"

    def safe(value):
        return escape(str(value))

    content = [
        Paragraph("EMPLOYEE PAYSLIP", heading_style),
        Spacer(1, 12),
        Paragraph(
            f"<b>Employee:</b> {safe(payroll['employee_name'])}",
            normal_style,
        ),
        Spacer(1, 6),
        Paragraph(
            f"<b>Payroll Month:</b> {safe(payroll['payroll_month'])}",
            normal_style,
        ),
        Spacer(1, 6),
        Paragraph(
            f"<b>Payment Status:</b> {safe(payroll['payment_status'])}",
            normal_style,
        ),
        Spacer(1, 24),
    ]

    salary_table = Table(
        [
            ["Salary Component", "Amount"],
            ["Basic Salary", money(payroll["basic_salary"])],
            ["HRA", money(payroll["hra"])],
            ["Allowances", money(payroll["allowances"])],
            ["Gross Salary", money(payroll["gross_salary"])],
            ["Deductions", money(payroll["deductions"])],
            ["Net Salary", money(payroll["net_salary"])],
        ],
        colWidths=[310, 180],
    )

    salary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253858")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E9F5EE")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )

    content.append(salary_table)
    content.append(Spacer(1, 25))
    content.append(
        Paragraph(
            "This is a computer-generated payslip.",
            normal_style,
        )
    )

    document.build(content)

    buffer.seek(0)
    return buffer
