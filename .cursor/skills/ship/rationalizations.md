# Ship Rationalizations

| Excuse | Reality |
| --- | --- |
| “CI will catch it.” | CI is a backstop, not permission to push known-untested work. |
| “The hook is broken, use `--no-verify`.” | Fix or report the hook; bypassing removes the control. |
| “Direct-to-main is faster.” | It removes isolation and rollback clarity. |
| “I can force-push the correction.” | Add a new commit unless the user explicitly requested history rewriting. |
| “The extra files are harmless.” | Unrelated files hide risk and make rollback harder. |

