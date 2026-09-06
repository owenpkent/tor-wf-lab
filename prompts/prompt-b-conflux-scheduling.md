# Prompt B: Conflux scheduling (aim for a go/no-go)

> Verbatim as given. Do not edit.

Reference for both: Shadbeh, Khajavi, Wang, "Reality Check for Tor Website
Fingerprinting in the Open World", arXiv:2603.07412. Code and data at
https://osf.io/9m8ea/ (synthetic monitored traces open; real non-monitored set
behind a data use agreement).

I am considering a multi-week project on Tor's Conflux traffic splitting as an
incidental website fingerprinting defense. This session is scoping, not
implementation. I want a decision at the end, not code.

Background: arXiv:2603.07412 shows Conflux drops DF's F1 from 0.939 to 0.379
for a guard observing one leg, but a guard with a 128ms latency advantage
recovers TPR from 0.189 to 0.736 by winning LowRTT primary-leg selection. Their
closing suggestion is designing scheduling that mitigates this latency bias.

## Questions, in order

1. Read Tor proposal 329 (https://spec.torproject.org/proposals/329-traffic-splitting.html)
   and the Conflux scheduling implementation in tor. Summarize how LowRTT picks
   the primary leg, where in the code that decision lives, and what state it
   depends on.
2. Conflux exists to reduce congestion and head-of-line blocking. Work out
   whether an alternative policy that reduces latency bias can be expressed
   without giving that up. This is the crux. If the answer is that any policy
   spreading traffic more evenly across legs necessarily reintroduces
   head-of-line blocking, the project is likely dead and I want to know now.
3. Sketch two or three candidate policies at the level of a paragraph each, with
   the specific tradeoff each one makes.
4. Assess whether Shadow (the Tor network simulator) can evaluate these. What
   would a minimal experiment look like, what does it need to model, and roughly
   how long does the setup take?
5. Check whether anyone has already proposed this. Search the tor-dev list,
   Tor's GitLab issues, and recent literature. If it is already in progress,
   that is a no-go and I would rather find out in hour two than week three.

## Deliverable

A short memo with a clear go or no-go recommendation and the reasoning. Be
willing to say no-go. I would rather kill this now than sink a month into it.

## Hard constraint

Do not write any Tor patches this session.
