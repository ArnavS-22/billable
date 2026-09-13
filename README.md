# Billable

**Demo:** https://www.loom.com/share/78096e6e3b224ae79e21cf224568ebc7    (Ends at 2:00)     

**1. What it does**

Billable is an AI agent for lawyers who forget to record small pieces of work. If a lawyer spends ten minutes reviewing a client's contract and forgets to record it, the client is never charged and the lawyer does not get paid. Billable catches that work while it is happening and prepares it to be recorded.

**2. How it works**

GUM observes activity on the screen and turns it into text. Billable looks for concrete clues like client names, file names, and words showing what work is happening. What makes Billable unique is that it creates structured observations from what the user is doing and evaluates each observation for enough evidence before taking action. (See Section 6 for the evaluation process.)

It then decides who the work is for and whether enough meaningful work happened. If two clients appear or there isn't enough evidence, it stops instead of guessing.

When confident, it creates a draft with the client, time, and description of the work. The user can Confirm or Hold it.

**3. The agentic workflow**

After Confirm, Billable acts across multiple apps. It checks Google Drive for the relevant document and Gmail when relevant, writes the record to Google Sheets, reads it back to verify it was saved correctly, and then sends a confirmation through Slack.

**Observe → Decide → Confirm → Act → Verify → Notify**

**4. External apps**

Google Drive, Gmail, Google Sheets, and Slack.

**5. Economic value**

If a lawyer works for ten minutes but forgets to record those ten minutes, they do not get paid for that work. Billable helps make sure lawyers get paid for work they already did.

**6. Reliability**

We tested four cases: a clear client, an unknown client, activity that is too short, and two conflicting clients. The agent only moves forward when it has enough evidence.

After writing to Google Sheets, it reads the record back. If the information isn't there, the action is treated as a failure.

Run the tests:

```bash
python eval.py
```

**7. Setup**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp matters.example.json matters.json

python -m gum_lawyer.listen
python app.py
```
