# Compliance Stress Test: Ufit Motion — First-School Go-Live

**Date:** 2026-05-26
**Vertical:** Education / Ed-tech (K-8 student education records)
**Jurisdictions:** US Federal + California (primary — LAUSD-style identifiers + California governing law in the Terms of Service). Multi-state expansion is a future-state risk (see Minor findings).
**Reviewed by:** compliance-stress-test skill

## Frameworks reviewed

- **FERPA** — Family Educational Rights and Privacy Act, 20 U.S.C. § 1232g; 34 CFR Part 99 (federal, US Dept of Education)
- **COPPA + 2025 amended Rule** — 16 CFR Part 312; FTC final rule published 2025-04-22, full compliance deadline **2026-04-22 (now passed)** — [FTC](https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-changes-childrens-privacy-rule-limiting-companies-ability-monetize-kids-data) · [Federal Register](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule)
- **SOPIPA** — Student Online Personal Information Protection Act, Cal. Bus. & Prof. Code §§ 22584–22585 (California)
- **AB 1584 / Cal. Education Code § 49073.1** — mandatory ed-tech vendor contract law (California) — [Ed Code §49073.1](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=EDC&sectionNum=49073.1.)
- **CA-NDPA v1.5 (01.28.25) / CSDPA** — the standard contract vehicle California districts use — [CITE/CSPA](https://www.cite.org/stuprivacy)

---

## Existing-state baseline (what the law already requires)

**FERPA** — Ufit may process student education records only as a designated "school official" with a "legitimate educational interest," under the school's "direct control," and may not re-disclose without consent. The school's contract must establish this designation.

**COPPA (2025 Rule)** — For K-12 services, the **school may consent in lieu of parents** *only if* student data is used **solely for educational purposes, never commercial**. The 2025 amendments add: (a) a mandatory written **data-retention policy** — no indefinite retention; (b) consent before third-party disclosure or targeted ads; (c) expanded definition of "personal information" now includes **government-issued identifiers** and biometric data.

**SOPIPA** — Operators of K-12 services must: no targeted advertising to students; no profiling outside school purposes; no selling/renting student data; **implement reasonable security**; and **delete student data upon school/district request within a commercially reasonable time**.

**AB 1584 / Ed Code § 49073.1 — the load-bearing one.** A California LEA's contract with an ed-tech vendor **must** contain, or the contract **is void**:
1. Pupil records remain the **property and under the control of the LEA**
2. Data used **only for the agreed educational purpose** — no advertising, no profile-building, no selling
3. Vendor's **security measures** described (encryption, access controls)
4. Description of how the LEA **and vendor jointly ensure FERPA compliance**
5. **Prohibition on targeted advertising** using PII in pupil records
6. Vendor must **delete all student data, including backups, upon contract termination, and provide proof**
7. Student-**generated** content (e.g., assessment scores coaches enter) gets the same protection as traditional records

**CA-NDPA v1.5** — the actual document a CA district will hand Ufit to sign. Includes an **AI clause**: if the service uses AI, student-data ownership stays with the district and the provider is **prohibited from using student data for AI training or content generation without prior written district consent**.

---

## 🔴 Critical

### C1 — No executed AB 1584 / CA-NDPA contract = cannot lawfully receive student data
**The collision:** The go-live plan treats the signed Data Processing Agreement as gap #1 on a punch list ("we'll get to it"). Under Ed Code § 49073.1, the §49073.1-compliant contract is a **legal prerequisite to processing a single student record** — and a non-compliant contract **is void**. This is structurally identical to the Casa Mate 3-tier miss: a legal mandate being treated as an optional best practice.

**The rule:** Cal. Education Code § 49073.1; the CA-NDPA v1.5 is the endorsed compliant vehicle.

**The fix:** **Do not load any student data until the district's CA-NDPA (or equivalent §49073.1 contract) is signed and uploaded to the CSPA registry.** Practically: pre-fill the CA-NDPA exhibits for Ufit (Exhibit E — data elements collected; the security exhibit; the deletion exhibit) so the district's counsel can review and countersign fast. The district initiates and uploads it, but Ufit should arrive with its exhibits ready. This is sales-blocking work, not code — but it gates the entire launch.

### C2 — No verifiable per-district deletion (including backups) with proof
**The collision:** AB 1584 requires deletion of **all student data including backups** on contract termination **with proof**; SOPIPA requires deletion on school request within a commercially reasonable time. Current state: soft-delete columns + `production_wipe.py` exist, but there is (a) no **per-district** deletion routine, (b) student data persists in **Supabase point-in-time-recovery backups** (7-day free / 30-day Pro) after a delete, and (c) no **deletion certificate / proof** mechanism.

**The rule:** Ed Code § 49073.1(a)(... deletion-with-proof clause); SOPIPA Cal. Bus. & Prof. Code § 22584.

**The fix:** Build a per-district deletion routine (`scripts/delete_district_data.py` scoped by organization_id), document that PITR backups age out the deleted data within the backup window (7 or 30 days — this satisfies "including backups" via expiry, which is industry standard), and emit a **deletion certificate** (date, district, record counts deleted, backup-expiry date) the ops team can send the district as proof. ~half a day of work. Must exist before signing C1's contract, because the contract obligates it.

---

## 🟡 Substantive

### S1 — CA-NDPA v1.5 AI clause needs an attestation
The current standard CA contract prohibits using student data for AI training/content generation without written district consent. Ufit Motion's scoring engine is deterministic (1-5 rubric → 20-100 normalization), not AI — good. **Fix:** be ready to attest "no AI training on student data" in the contract. If you ever add an AI feature (auto-written progress summaries, etc.), it requires prior written district consent first.

### S2 — COPPA 2025 retention limit must be enforced, not just stated
The Privacy Policy states "retained for the duration of the contract + 3 years." COPPA's 2025 Rule now requires a written retention policy AND prohibits indefinite retention — but a *stated* policy with no *enforcing purge routine* is a gap. **Fix:** either implement a scheduled purge that enforces the 3-year window, or align the policy text to what's actually enforced. Don't let policy and practice diverge.

### S3 — Subprocessors must be disclosed in the contract
HubSpot (adults only), Sentry (PII off), Render, Supabase, and Google/Resend are all subprocessors touching covered data or infrastructure. AB 1584 requires describing security and, in the CA-NDPA, listing subprocessors. **Fix:** (a) execute HubSpot's DPA in their account settings (gap #3 from prior review); (b) list all five subprocessors in the CA-NDPA subprocessor exhibit; (c) confirm each has a DPA (Supabase, Render, Google Workspace, Sentry all publish SOC 2 + DPAs).

### S4 — local_student_identifier is now COPPA "personal information"
The 2025 COPPA Rule expanded PII to include government/district-issued identifiers — your `local_student_identifier` (e.g., LAUSD-2026-0001) is squarely in scope. This **raises** the consent bar, but it's **covered** by the school-consent exception **as long as C1's contract is in place**. **Fix:** covered by C1; no separate action.

---

## 🟢 Minor

### M1 — Multi-state expansion ≠ California compliance
The "100 schools" goal implies expansion beyond CA. Each state has its own student-privacy regime (~100+ state laws tracked by the Parent Coalition for Student Privacy). The CA-NDPA has a national sibling (the SDPC **NDPA**) adopted by ~20+ states. **Fix:** when you cross a state line, sign that state's NDPA variant; never assume CA compliance transfers.

### M2 — Public Privacy Policy / Terms are not the operative contract
`/privacy` and `/terms` are good for legitimacy and iOS App Store submission, but they do **not** satisfy AB 1584 — that requires a signed contract *with the LEA*. **Fix:** keep the public pages; understand the CA-NDPA is the document that actually governs.

---

## ✅ What the plan got right

Genuinely strong — better technical privacy posture than most ed-tech vendors ship with: no advertising, no data selling, no student data sent to HubSpot (adult-only third-party surface), org-scoped queries enforcing the FERPA boundary at the SQL layer, PBKDF2 hashing, audit logging, `send_default_pii=False` on Sentry, and a school-as-consent-giver model that aligns cleanly with both COPPA's school-consent exception and FERPA's school-official exception. The "reasonable security" bar under SOPIPA/AB 1584 is met.

---

## Compliance verdict: 6/10

**What this score reflects:** The *technical* build is ~9/10 — privacy-by-design, defensible security, no commercial misuse. The score is dragged to 6 by a **structural compliance gap**: you cannot lawfully onboard a California district's student data until a §49073.1-compliant contract (the CA-NDPA) is executed, and one capability that contract will obligate (verifiable deletion including backups, with proof) isn't built yet. Both are concrete and fixable — this is not a "rethink the product" situation.

**Plan is ready to go live if:** (C1) the district signs the CA-NDPA before any student data is loaded, and (C2) the per-district deletion-with-certificate routine exists. Those two close the legal gate.

**Plan is unsafe to go live if:** you import the first school's roster before the CA-NDPA is signed. That's processing education records without the legally-mandated contract — the exact failure this review exists to prevent. The district's own counsel will likely catch it and stall the deal; worst case it's a § 49073.1 violation and a void contract.

---

## Recommended sequence to clear the gate

1. **Build C2** (deletion routine + certificate) — ~half a day. I can do this.
2. **Prep the CA-NDPA exhibits** for Ufit (data elements, security description, subprocessor list, deletion method) — so the district gets a turnkey packet.
3. **Execute HubSpot DPA** (S3) — 5 min in HubSpot settings.
4. **District signs CA-NDPA → uploads to CSPA registry** (C1) — district-driven; Ufit provides exhibits.
5. **Only then** import the first school's student roster.

Sources:
- [FTC — COPPA final rule (2025)](https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-changes-childrens-privacy-rule-limiting-companies-ability-monetize-kids-data)
- [Federal Register — COPPA Rule amendment](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule)
- [CA Education Code § 49073.1](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=EDC&sectionNum=49073.1.)
- [California Student Privacy Alliance / CITE](https://www.cite.org/stuprivacy)
- [CA-NDPA v1.5 (01.28.25)](https://assets.noviams.com/novi-file-uploads/cite/pdfs-and-documents/StudentDataPrivacy/CA-NDPA_v1_5__Final_.pdf)
- [FPF Guide to SOPIPA](https://fpf.org/wp-content/uploads/2016/11/SOPIPA-Guide_Nov-4-2016.pdf)
