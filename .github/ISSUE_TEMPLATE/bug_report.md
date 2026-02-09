---
name: "Bug Report"
description: "Report a reproducible bug or unexpected behavior in maia-messaging"
title: "[BUG] <Brief description of bug>"
labels: ["bug"]
assignees: ''

---

**Describe the Bug**
A clear and concise description of what the bug is. What did you expect to happen? What actually happened?

**Steps to Reproduce**
Please provide a *minimal* reproducible example:

```python
from messaging import TwilioProvider, TwilioConfig, WhatsAppText

# Example setup...
provider = TwilioProvider(TwilioConfig(
    account_sid="AC...",
    auth_token="...",
    whatsapp_number="whatsapp:+14155238886",
))

# The call that causes the bug
result = provider.send(WhatsAppText(to="whatsapp:+5511999999999", body="Hello"))
```

**Expected Behavior**
A clear description of what you expected to happen.

**Actual Behavior**
What actually happened? Include any error messages or unexpected output.

**Error Output / Traceback**
```text
Paste the full traceback or error output here.
```

**Environment:**
*   **maia-messaging Version:** [e.g., 0.3.0 - run `pip show maia-messaging`]
*   **Python Version:** [e.g., 3.11.9 - run `python --version`]
*   **Provider Used:** [e.g., TwilioProvider, SendGridProvider, TwilioSMSProvider]
*   **Operating System:** [e.g., Ubuntu 22.04, macOS Sonoma]

**Additional Context**
Add any other context about the problem here.
