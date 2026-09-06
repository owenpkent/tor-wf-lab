# Draft 1: analysis code availability

**To:** <seven-character full name>@sfu.ca
**Subject:** Analysis code for "Reality Check for Tor WF in the Open World"

---

Dear Professor Wang,

I have been working through "Reality Check for Tor Website Fingerprinting in the
Open World" and the accompanying OSF project at osf.io/9m8ea. The trace data
downloads cleanly and the pre/post-Conflux structure is clear.

I could not find the analysis code. The introduction says the dataset and the
analysis code are both released, but the OSF file listing contains only the
.npz trace files, and I could not locate a repository elsewhere. Is the code
published somewhere I have missed, or is a release still pending?

What I am specifically after is the classifier implementations and training
harness for k-FP, DF, Tik-Tok, RF and Holmes at the configurations in your
hyperparameter table. My aim is to compare the five at your published settings
rather than retuning them, so working from your code rather than from five
separate reimplementations matters quite a bit for whether the comparison means
anything.

An unpolished tarball or a private repository link would be more than enough. I
am not looking for anything packaged.

If Mohammadhamed Shadbeh is the right person to ask, I would be grateful if you
could forward this.

One unrelated question, if you do not mind. Your conclusion suggests designing
Conflux scheduling algorithms that mitigate the latency bias. Is anyone in your
group or among your collaborators already working on that? I am scoping a small
project in that direction and would rather not duplicate work that is already
under way.

Thank you for releasing the data. The pre/post-Conflux split with the latency
variants is unusually useful.

Best regards,
Owen Kent
[affiliation or "independent researcher"]

---

## Notes before sending

- The only field to fill is the affiliation line.
- Deliberately does not mention the DUA. Keep the two requests separate so a
  slow answer on one does not stall the other.
- The Conflux scheduling paragraph was added 2026-09-06 for Track B. It is the
  cheapest way to resolve the one serious no-go risk in `docs/track-b-memo.md`,
  which is that the authors are the obvious people to be doing this already.
  Delete it if you would rather keep the email to a single ask.
- If there is no reply in about a week, the fallback is reimplementation from
  the original papers, logged as a delta. k-FP, DF, Tik-Tok and RF have usable
  public reference implementations. Holmes is the recent one and the risk.
