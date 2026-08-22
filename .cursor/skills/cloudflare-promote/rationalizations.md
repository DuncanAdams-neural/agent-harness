# Cloudflare Promotion Rationalizations

| Excuse | Reality |
| --- | --- |
| “`wrangler deploy` is simpler.” | It creates and immediately routes 100% traffic. |
| “The preview loaded once.” | One response is not critical-path or observability evidence. |
| “One percent cannot hurt.” | One percent can corrupt shared state or trigger side effects. |
| “We can find the old version later.” | A rollback target must exist before traffic moves. |
| “Skip the hold; errors appear instantly.” | Latency, caches, queues, and low-volume paths delay failures. |

