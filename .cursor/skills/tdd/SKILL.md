---
name: tdd
description: Use when implementing a feature or bug fix that changes observable behavior.
user-invocable: true
tier: rigid
kind: implementation
---

# Test-Driven Development

## Iron Law

```
NO BEHAVIOR CHANGE WITHOUT A TEST THAT FAILS FOR THE RIGHT REASON FIRST
```

Exemptions: documentation, comments, formatting, and mechanical configuration with an equivalent deterministic validator. Record the exemption in the plan.

## Cycle

1. Specify one observable behavior.
2. Add the smallest focused test and run it.
3. Confirm it fails because the behavior is absent, not because the test is broken.
4. Implement the smallest change that passes.
5. Run focused tests, then the relevant broader suite.
6. Refactor only while green.

## Red flags

- Writing the implementation before the test.
- A test that passed before the change.
- Mocking away the behavior under test.
- Deleting or weakening a failing assertion.
- Calling a change “too small to test.”

## Common rationalizations

See `rationalizations.md`. If one matches your reasoning, stop and restart the cycle.

## Self-review

- [ ] The pre-implementation failure was observed.
- [ ] The failure reason matched the missing behavior.
- [ ] The implementation is no broader than necessary.
- [ ] Focused and regression tests are green.
- [ ] No test was muted, deleted, or weakened.

