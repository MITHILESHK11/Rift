from fastapi import APIRouter

router = APIRouter(tags=["Team Roster (Section 5.6)"])

TEAM_ROSTER = [
    { "user_id": "u_aarti", "name": "Aarti Menon", "department": "Sales - Enterprise",
      "scope": "RFPs, RFIs, tenders, and inbound deals above ₹10,00,000" },
    { "user_id": "u_rohit", "name": "Rohit Sharma", "department": "Sales - SMB",
      "scope": "Product enquiries, demo requests, deals at or below ₹10,00,000" },
    { "user_id": "u_meera", "name": "Meera Iyer", "department": "Marketing",
      "scope": "Webinars, event and conference sponsorships, content collaborations, PR and media" },
    { "user_id": "u_karan", "name": "Karan Doshi", "department": "Alliances",
      "scope": "Reseller, channel partner, and technology integration proposals" },
    { "user_id": "u_divya", "name": "Divya Rao", "department": "Finance",
      "scope": "Invoices, purchase orders, payment reminders, GST and vendor billing" },
    { "user_id": "u_triage", "name": "Triage Queue", "department": "Operations",
      "scope": "Ambiguous items requiring human review" }
]

@router.get("/users")
def get_team_roster():
    """Returns team roster per Section 3.2."""
    return {"team": TEAM_ROSTER}
