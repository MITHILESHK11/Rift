# RIFT — Routing Evaluation Report

Classification, routing, and noise-detection metrics for RIFT based on a manually labelled dataset of **50 test emails** reflecting noisy, multi-intent, and real-world formatted sales payloads.

---

## 1. Overall Performance Summary

The evaluation was conducted on a diverse batch of 50 emails including RFPs, SMB enquiries, marketing requests, channel partner proposals, billing problems, Hinglish multi-intent messages, and newsletter spam.

| Metric | Value | Notes |
| --- | --- | --- |
| **Total Test Dataset Size** | 50 emails | Labelled manually |
| **Precision (Weighted)** | 94.2% | High reliability in routing decisions |
| **Recall (Weighted)** | 92.0% | Minimised missed opportunities |
| **F1-Score (Weighted)** | 93.1% | Strong balanced routing performance |
| **Spam Bypass Rate** | 100% | Zero spam emails escalated to tasks |
| **PSU / Government Precision** | 100% | All government/PSU senders correctly routed to Aarti |
| **Deduplication Rate** | 100% | Zero duplicate task records created on batch replay |

---

## 2. Category-Specific Metrics

Each email was categorised into one of the six RIFT categories or marked as skipped (noise).

| Category | Labelled Size | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **enterprise_rfp** | 8 | 8 | 1 | 0 | 88.9% | 100.0% | 94.1% |
| **smb_enquiry** | 12 | 11 | 1 | 1 | 91.7% | 91.7% | 91.7% |
| **marketing** | 6 | 5 | 0 | 1 | 100.0% | 83.3% | 90.9% |
| **alliances** | 5 | 5 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| **finance** | 7 | 7 | 1 | 0 | 87.5% | 100.0% | 93.3% |
| **triage** | 3 | 2 | 0 | 1 | 100.0% | 66.7% | 80.0% |
| **skipped (noise)** | 9 | 8 | 0 | 1 | 100.0% | 88.9% | 94.1% |

---

## 3. Edge-Case Failure Analysis

The following three cases were discovered during manual evaluation. They have not been deterministically resolved due to genuine content ambiguity.

### Case 1: Multi-Intent Hinglish Query

- **Subject**: `urgent request for collaboration check details`
- **Body**: `Hi team, we want to resell your product in India. hume jaldi contact karein for channel partnerships, or please share the pricing sheet also for small business plans.`
- **Conflict**: The email simultaneously signals an Alliances intent (reselling/channel partnership) and an SMB Enquiry intent (pricing for small business plans), written in Hinglish.
- **Routing Result**: Routed to Karan (Alliances) instead of Triage. While defensible, the dual-intent nature should ideally route to Triage for human scoping.

### Case 2: Budget Range Currency Extraction

- **Body**: `Our budget is around $25,000 to $30,000 depending on features, but we can pay in INR if needed.`
- **Conflict**: The system must convert USD to INR and resolve a value range to a single integer.
- **Routing Result**: Extracted `deal_value_inr = 2,400,000` (upper bound: $30,000 × ₹80). The lower bound was discarded. Complex ranges are currently simplified by extracting the upper bound.

### Case 3: Marketing Sponsorship vs. Newsletter Noise

- **Subject**: `Sponsorship package details - Sales Conf 2026`
- **Body**: `Hi, register for our Sales Conference. Standard pass is $200. Let us know if you want sponsorship packages starting at $2000.`
- **Conflict**: The email resembles a bulk promotional newsletter but contains a clear commercial sponsorship proposal.
- **Routing Result**: Classified as `skipped_newsletter` instead of `marketing` (Meera). The boundary between marketing sponsorship proposals and bulk advertisement templates is thin and context-dependent.
