import random
import datetime

COMPANIES = ["Meridian Steel", "Railyard Logistics", "Bharat Heavy Electricals Limited", "Vantage Cloud", "Zenith Partners", "Halcyon Retail", "Apex Tech", "Nexus Solutions", "Trident Dynamics", "Starlight Media"]
DOMAINS = ["meridiansteel.co.in", "railyardlogistics.in", "bhel.in", "vantagecloud.com", "zenith.io", "halcyon.in", "apextech.com", "nexus.co.in", "trident.org", "starlight.net"]
FIRST_NAMES = ["Suresh", "Ankit", "Nandita", "Farhan", "Deepak", "Priya", "Vikram", "Neha", "Rohan", "Sunita", "Amit", "Kavita"]
LAST_NAMES = ["Kulkarni", "Bose", "Reddy", "Qureshi", "Sharma", "Menon", "Gupta", "Deshmukh", "Joshi", "Verma", "Patel", "Rao"]

def generate_sample_emails(count: int = 250) -> list:
    """Generates synthetic emails covering all 12 worked examples and edge cases."""
    emails = []
    base_time = datetime.datetime(2026, 8, 1, 9, 0, 0)

    for i in range(1, count + 1):
        email_id = f"em_{i:05d}"
        thread_id = f"th_{((i - 1) % 180) + 1:04d}"
        is_reply = (i > 180) or (random.random() < 0.15)
        message_index = 1 if is_reply else 0

        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        name = f"{fn} {ln}"
        domain = random.choice(DOMAINS)
        from_email = f"{fn.lower()}.{ln.lower()}@{domain}"
        comp = random.choice(COMPANIES)

        time_offset = datetime.timedelta(minutes=i * 12 + random.randint(0, 5))
        rec_time = (base_time + time_offset).isoformat() + "+05:30"

        # Categorized email templates matching Section 6
        template_type = i % 12

        if template_type == 1:
            # Enterprise RFP (> 10L)
            val_lakhs = random.randint(15, 80)
            subject = f"RFP - Enterprise System for {comp}"
            body = f"Dear Team,\n\n{comp} invites proposals for an enterprise system. Indicative budget is Rs. {val_lakhs} lakhs. Proposals must reach us by 15th August 2026.\n\nRegards,\n{name}"
            attachments = ["RFP_Spec_2026.pdf"]

        elif template_type == 2:
            # SMB Demo request (no value)
            subject = f"Quick demo request - {comp}"
            body = f"Hi, we are a 25-person team at {comp}... can we get a demo next week? Nothing urgent.\n\nThanks,\n{name}"
            attachments = []

        elif template_type == 3:
            # PSU Tender (< 10L)
            subject = f"Tender Notice No. BHEL/PROC/2026/{random.randint(1000, 9999)}"
            body = f"Bharat Heavy Electricals Limited invites bids for supply of licences. Estimated value: Rs. 6,50,000. Last date for bid submission: 03-08-2026, 1700 hrs IST.\n\nRegards,\nProcurement Dept"
            attachments = ["Tender_Notice.pdf"]

        elif template_type == 4:
            # Marketing Sponsorship
            subject = f"Sponsorship confirmation needed - India SaaS Summit"
            body = f"We are finalising sponsors for the Summit. Gold tier is ₹4,00,000. We need confirmation by tomorrow EOD as we are going to print.\n\nBest,\n{name}"
            attachments = ["Sponsorship_Deck.pdf"]

        elif template_type == 5:
            # Invoice query
            inv_num = f"INV-2026-{random.randint(100, 999)}"
            subject = f"Invoice {inv_num} Overdue"
            body = f"Please find attached invoice {inv_num} for Rs. 1,18,000 (incl. 18% GST). Kindly process as payment is 12 days overdue.\n\nRegards,\nFinance Team"
            attachments = [f"{inv_num}.pdf"]

        elif template_type == 6:
            # Alliances
            subject = f"Partnership & Reseller Proposal - {comp}"
            body = f"We are a partner across MEA. We would like to explore reselling your platform or a technical integration. Who handles partnerships?\n\nRegards,\n{name}"
            attachments = []

        elif template_type == 7:
            # OOO Auto reply
            subject = f"Out of Office: {name}"
            body = f"I am out of office until 14th August with limited access to email. For urgent matters please contact colleague@domain.com."
            attachments = []

        elif template_type == 8:
            # Vendor Spam
            subject = "Boost your organic traffic by 3x in 90 days"
            body = "Hi, I noticed your website isn't ranking on page 1. We do content marketing, PR outreach, and webinar promotion. Interested in a quick 15 min call?"
            attachments = ["Audit.pdf"]

        elif template_type == 9:
            # Newsletter
            subject = f"B2B Growth Weekly - Issue #{random.randint(100, 300)}"
            body = "In this edition: why PLG is stalling, pricing experiments, and teardowns. Click here to [Unsubscribe]."
            attachments = []

        elif template_type == 10:
            # Thread Reply
            subject = f"Re: RFP - Enterprise System for {comp}"
            body = f"Correction to our earlier note - budget approved is Rs. 32 lakhs, deadline is 11th August.\n\n> On 01 Aug, {name} wrote:\n> Dear Team, RFP invites..."
            attachments = []

        elif template_type == 11:
            # Ambiguous (Triage)
            subject = f"Met at booth - Evaluation + Webinar co-host"
            body = f"Hi, two things: (1) we'd like to evaluate for 800 people, budget TBD, and (2) CMO wants to co-host a webinar. Can you loop in right people?\n\n{name}"
            attachments = []

        else:
            # Hinglish enterprise
            subject = f"Hinglish deal request - {comp}"
            body = f"Bhai, humko aapka product chahiye for dealer network. 150 users. Budget approx 1.2 cr allocated hai for FY. Kab connect kar sakte hain?\n\n{name}"
            attachments = []

        emails.append({
            "email_id": email_id,
            "thread_id": thread_id,
            "message_index": message_index,
            "from_name": name,
            "from_email": from_email,
            "to": "sales@company.com",
            "cc": [],
            "subject": subject,
            "body": body,
            "received_at": rec_time,
            "attachments": attachments,
            "is_reply": is_reply
        })

    return emails
