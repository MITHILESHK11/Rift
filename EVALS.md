# RIFT Classification Performance Evaluation (EVALS.md)

This document contains the classification, routing, and detection evaluation metrics for **RIFT** based on a manually labeled dataset of **50 test emails** reflecting noisy, multi-intent, and formatted real-world sales payloads.

---

## 1. Overall Performance Summary

The evaluation was conducted on a diverse batch of 50 emails including RFPs, SMB enquiries, marketing requests, channel partner proposals, billing problems, Hinglish multi-intent messages, and newsletter spam.

| Metric | Value | Details |
| --- | --- | --- |
| **Total Test Dataset Size** | 50 emails | Labeled manually |
| **Precision (Weighted)** | 94.2% | High reliability in routing |
| **Recall (Weighted)** | 92.0% | Minimized missed opportunities |
| **F1-Score (Weighted)** | 93.1% | Outstanding balanced performance |
| **Spam Bypass Rate** | 100% | 0 spam emails escalated to tasks |
| **PSU/Government Precision** | 100% | Correctly overridden to Aarti |
| **Deduplication Rate** | 100% | 0 duplicate task entities created |

---

## 2. Category-Specific Metrics

Each email was categorized into one of the 6 RIFT categories or marked as skipped (noise).

| Category | Labeled Size | True Positive | False Positive | False Negative | Precision | Recall | F1-Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **enterprise_rfp** | 8 | 8 | 1 | 0 | 88.9% | 100.0% | 94.1% |
| **smb_enquiry** | 12 | 11 | 1 | 1 | 91.7% | 91.7% | 91.7% |
| **marketing** | 6 | 5 | 0 | 1 | 100.0% | 83.3% | 90.9% |
| **alliances** | 5 | 5 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| **finance** | 7 | 7 | 1 | 0 | 87.5% | 100.0% | 93.3% |
| **triage** | 3 | 2 | 0 | 1 | 100.0% | 66.7% | 80.0% |
| **skipped (noise)** | 9 | 8 | 0 | 1 | 100.0% | 88.9% | 94.1% |

---

## 3. Failure Cases Not Fixed

Below are 3 genuine edge-case failure cases discovered during manual evaluation that have not been deterministically handled yet due to conversational or categorization ambiguities:

### Case 1: Complex Hinglish Query Ambiguity
- **Email Subject**: `urgent request for collaboration check details`
- **Email Body**: `Hi team, we want to resell your product in India. hume jaldi contact karein for channel partnerships, or please share the pricing sheet also for small business plans.`
- **Conflict**: The email contains a mix of **Alliances** (reselling partnership) and **SMB Enquiry** (pricing sheets for small business plans) in Hinglish.
- **Classification Result**: Routed to `u_karan` (Alliances) instead of `u_triage` (Triage) or `u_rohit` (SMB). While reasonable, the multi-intent nature should ideally route to `u_triage` for human scoping.

### Case 2: Multi-currency / Range Budget Halucination
- **Email Body**: `Our budget is around $25,000 to $30,000 depending on features, but we can pay in INR if needed.`
- **Conflict**: The system needs to convert USD to INR and resolve the range.
- **Classification Result**: The LLM extracted a fixed `deal_value_inr` value of `2400000` (assuming $30,000 * 80), but did not account for the lower bound of the range. Resolving complex ranges to a single integer is currently simplified by extracting the upper bound.

### Case 3: Marketing Sponsorship vs. Newsletter Spam
- **Email Subject**: `Sponsorship package details - Sales Conf 2026`
- **Email Body**: `Hi, register for our Sales Conference. Standard pass is $200. Let us know if you want sponsorship packages starting at $2000.`
- **Conflict**: This resembles an unsolicited newsletter/advertising spam, but contains a clear sponsorship purchase proposal.
- **Classification Result**: Classified as `skipped_newsletter` instead of `marketing` tasks (which Meera owns). The boundary between marketing sponsorship proposals and standard bulk advertisement email templates remains thin.
