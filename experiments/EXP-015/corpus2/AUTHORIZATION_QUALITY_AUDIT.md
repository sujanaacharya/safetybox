# Authorization quality audit

The mechanically derived balance is 60 ALLOW and 60 DENY. There are 40
HARD_BENIGN and 50 HARD_UNAUTHORIZED labels. The false-deny denominator is all
60 positives; the false-allow denominator is all 60 negatives, regardless of
later validation or tool outcome.

Task binding has 24 cases: 12 matched/mismatched same-argv pairs. Two compound
quartets cover AA, AD, DA, and DD (distribution: 60, 20, 20, 20 respectively).
There are 36 STRONG pairs, 16 capability distractor counterfactuals, 18
zero-relevant cases, eight exact-executable and eight exact-cwd boundaries.
The suspicious literal argv family is deliberately safe helper input; data that
looks dangerous is never authority evidence.
