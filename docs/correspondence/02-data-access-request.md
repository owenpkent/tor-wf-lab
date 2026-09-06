# Draft 2: open-world background data access request

**Route:** the "Request Access" control on https://osf.io/9m8ea/ (the node has
access requests enabled). No email address, form, or lead time for the data use
agreement is stated in the OSF wiki or in the thesis, so the platform mechanism
is the only documented path. If it produces no response, fall back to sending
this same text to <seven-character full name>@sfu.ca.

---

Dear Professor Wang and colleagues,

I would like to request access to the open-world background traces from "Reality
Check for Tor Website Fingerprinting in the Open World". I understand these are
real, unlabeled Tor traffic and are restricted for one year after release, and
that access is subject to a data use agreement and academic research approval.

Purpose. I am trying to establish whether robustness to network mismatch and
robustness to temporal drift are genuinely distinct properties of a WF
classifier. Your results suggest they are, and in an unusually sharp way: RF is
near-useless under cross-network training but the strongest model under
six-month drift, while DF is the reverse. I want to test whether that trade-off
holds across all five classifiers you evaluate, and to report it with multiple
seeds and variance rather than single runs.

Why the restricted set is needed. The public monitored traces span CA, AU and UK
clients across month 0, 2 and 6, so both axes can be constructed closed-world,
and I intend to run that regardless. But your cross-network and concept-drift
figures are open-world numbers scored against the real background, so a
closed-world result cannot be compared to them directly. Without the background
set I can ask your question, but I cannot check my answer against yours.

Undertakings. I would not redistribute the traces, would not attempt to
deanonymize or otherwise identify any user or destination in the background
traffic, would store the data on a single non-shared machine, would delete it on
request or at the end of the work, and would cite the dataset and paper in
anything published. I am happy to sign whatever agreement you use and to work
within any additional conditions you would like to impose.

I recognize that access is limited to approved academic research and that my
situation may not meet that bar. If it does not, I would rather know now than
wait, and a straight no is a perfectly useful answer.

Best regards,
Owen Kent
[affiliation, or "independent researcher, unaffiliated"]

---

## Notes before sending

- **Be honest on the affiliation line.** The stated bar is "academic research
  approval". Overstating an affiliation to clear it would poison the result and
  is not worth a dataset. If the answer is no, the closed-world substitute is
  already the plan.
- The second-to-last paragraph invites a fast rejection on purpose. Unknown lead
  time is the main scheduling risk for Track A, and a quick no is worth more
  than a slow maybe.
- Send the same day as draft 1, not after it.
