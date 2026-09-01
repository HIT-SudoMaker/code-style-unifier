# Triage Labels

| Canonical role | Repository label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | A maintainer must evaluate the issue. |
| `needs-info` | `needs-info` | The issue needs more information. |
| `ready-for-agent` | `ready-for-agent` | The issue is sufficiently specified for an agent. |
| `ready-for-human` | `ready-for-human` | The issue requires human action. |
| `wontfix` | `wontfix` | The issue will not be actioned. |

## Local decision closure

`resolved` is not a triage role or repository label. A local decision ticket
whose decision has been accepted and recorded closes with:

`Status: resolved (YYYY-MM-DD)`

`wontfix` means the issue will not be actioned; it must not substitute for a
decision that was made and recorded.
