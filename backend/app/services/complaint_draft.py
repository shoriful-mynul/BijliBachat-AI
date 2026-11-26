"""A local complaint draft. Nothing is sent to a distribution company."""

from app.schemas.bill import BillAuditReport, ComplaintDraft, ConfirmedBillRequest

_FORBIDDEN = ("unlawful", "illegal", "fraud", "fraudulent", "must refund", "court")


def build_complaint_draft(bill: ConfirmedBillRequest, report: BillAuditReport) -> ComplaintDraft:
    mismatches = [row for row in report.comparisons if row.outcome == "possible_mismatch"]
    if mismatches:
        finding = "\n".join(
            f"- {row.label}: confirmed {row.reported_amount} PKR, calculated {row.calculated_amount} PKR. "
            "Possible mismatch."
            for row in mismatches
        )
    else:
        finding = (
            "- A component-level comparison did not produce a possible mismatch. "
            "A complete payable comparison may still be unavailable."
        )
    text = (
        "To the billing office,\n\n"
        "I am writing about my electricity bill for the period ending "
        f"{bill.billing_date.isoformat()}.\n\n"
        f"Distribution company: {bill.provider_code}\n"
        f"Consumer category: {bill.consumer_category}\n"
        f"Tariff type: {bill.tariff_type}\n"
        f"Eligibility: {bill.eligibility or '[please add eligibility if it applies]'}\n"
        f"Billed units: {bill.consumption_kwh} kWh\n"
        f"Reference: [please add the account or bill reference]\n"
        "Name: [please add your name]\n"
        "Contact: [please add a phone number or email]\n\n"
        "I reviewed the printed amounts and compared the components that the tariff schedule can calculate. "
        "Please review the following:\n"
        f"{finding}\n\n"
        f"{report.explanation}\n\n"
        "I am asking for a review of these figures. "
        "This note has not been submitted.\n"
    )
    lowered = text.lower()
    if any(phrase in lowered for phrase in _FORBIDDEN):
        raise RuntimeError("The complaint template used language that is not allowed.")
    return ComplaintDraft(submitted=False, editable=True, text=text)
