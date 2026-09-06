# Draft 3: one email, superseding drafts 1 and 2

**To:** <seven-character full name>@sfu.ca
**Subject:** Open-world traces and analysis code for "Reality Check for Tor WF"

Supersedes `01-code-availability.md` and `02-data-access-request.md`. Send this
one instead of those two. Why it merged, and what changed, is in the notes at
the bottom.

---

Dear Professor Wang,

I have been working through "Reality Check for Tor Website Fingerprinting in the
Open World" and the OSF release. I have three short requests, and one piece of
information you may want.

I ran your five classifiers on the open monitored traces to test whether
robustness to network mismatch and robustness to temporal drift are genuinely
distinct properties. Closed-world only, at your Table C.1 hyperparameters,
untuned, three seeds. The rank ordering on both axes comes out identical to
yours, and the drift column lands very close to your published values: mean
absolute difference 0.008 at month 2 and 0.037 at month 6. The cross-network
column does not, differing by 0.318 on average, which is what I would expect if
the open-world penalty there is dominated by false positives against the
background traffic that closed-world scoring simply deletes.

**The open-world background set.** That last point is why I would like access.
I understand it is real Tor traffic, restricted for a year, and subject to a
data use agreement and academic approval. Without it I can ask your question but
cannot check my answer against yours: no closed-world number I have is the same
measurement as anything in your tables. I would not redistribute the traces,
would not attempt to deanonymize any user or destination, would keep them on a
single non-shared machine, would delete them on request, and would cite the
dataset and paper. I am happy to sign whatever agreement you use. If my
situation does not meet the academic-approval bar, a straight no is genuinely
useful and I would rather have it quickly than wait.

**The analysis code.** The introduction says the analysis code was released, but
the OSF listing holds only the .npz traces and I could not find a repository. It
matters less than it did, since I could work from the original authors' releases
for RF and Holmes, but DF, Tik-Tok and k-FP are reimplementations from the paper
text and I would like to check them against yours. An unpolished tarball would
be more than enough.

**Your closing suggestion.** You propose designing Conflux scheduling that
mitigates the latency bias. Is anyone in your group already working on that? I
am scoping a small project in that direction and would rather not duplicate it.

**The information:** the OSF project has access requests enabled, but because
the node is public and has no private components, OSF renders no "Request
Access" control on it. As far as I can tell there is currently no way for anyone
to request the restricted data through the platform, which may not be what you
intended.

If Mohammadhamed Shadbeh is the right person for any of this, I would be
grateful if you could forward it.

Thank you for releasing the data. The pre/post-Conflux split with the latency
variants is unusually useful, and the `-rtt-*` files in particular let me check
part of your Conflux result without the restricted set.

Best regards,
Owen Kent
[affiliation, or "independent researcher, unaffiliated"]

---

## Notes before sending

- **Still exactly one field to fill:** the affiliation line. Be honest on it.
  The stated bar is academic research approval, and overstating an affiliation
  to clear it would poison the result and is not worth a dataset.
- **Why one email now.** The OSF route in draft 2 does not exist: the API
  reports `access_requests_enabled: true`, but the node is public with zero
  child components, so there is nothing for the button to attach to. Email is
  the only path, and both asks go to the same person, so two emails would be
  two interruptions for one conversation.
- **The order changed.** Draft 1 led with the code because it decided how much
  work Track A would be. Track A has since run, so the data request now leads:
  it is the only thing that would close the "reproduce one paper number" gate,
  and it has the longest unknown lead time.
- **The opening paragraph is doing work.** It shows the request comes with
  effort already spent, and the 0.008 / 0.318 contrast is a result they will
  find interesting, which is the best reason for them to reply at all.
- The Conflux question is the cheapest way to resolve the main no-go risk in
  `../track-b-memo.md`.
- If there is no reply in about a week, nothing downstream is blocked. Both
  tracks are complete without it; the data would upgrade Track A's corroboration
  to reproduction, and the code would firm up three of five implementations.
