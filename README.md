# Billable

**Demo:** [https://www.loom.com/share/78096e6e3b224ae79e21cf224568ebc7](https://www.loom.com/share/78096e6e3b224ae79e21cf224568ebc7)

The AI does not guess your day from memory. It watches the screen. GUM takes what is in front of you, turns it into text, and we look through that text for hard clues: a file name, a client name from your matter list, words like markup, review, or email. If two clients show up, it stops. If the stretch is too short, it stops. That is the whole deduction. It is picky on purpose, not a storyteller.

Once it has a draft, it acts. It searches Google Drive for the file it named. If the work looks like mail, it checks Gmail. Then it sits. Confirm is the only thing that writes. That write is a real sheet row, a read-back to prove the row is there, and a Slack note to the team. Hold does nothing. The agent is allowed to move money-adjacent records only after a person says yes.

That gate is the economic point. Lawyers bill in slices. Ten quiet minutes on a doc that never make the timesheet are gone. At firm rates that is not a rounding error. Billable’s job is to catch the slice while it is happening, put a draft in front of you, and get the hour onto an invoice instead of leaving it in your head.

## External apps

Google Drive, Gmail, Google Sheets, Slack. GUM is the screen observer, not one of those four.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp matters.example.json matters.json
```

Fill `.env` with your own Composio and OpenAI keys and connected account ids. Add your clients to `matters.json`. Do not commit those files.

```bash
python -m gum_lawyer.listen
python app.py
```

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/app. `python main.py` drafts only. `python main.py --confirm` writes after review.

## Reliability testing

`python eval.py` runs the four gate cases above. After Confirm, Sheets read-back must contain the same note or the write is treated as failed.
