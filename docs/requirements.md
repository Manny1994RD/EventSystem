# Church Event System: Draft Requirements

Status: draft for discussion. Items marked **[?]** are open questions.

## 1. Goal

Replace the quarterly "send in your event list and flyers, then wait" process with one place where:

- each church submits its events for the coming quarter before the deadline,
- flyers are uploaded and reviewed in the same place,
- everyone can see a shared calendar so events don't pile up on the same day,
- the regional events rep can see every church's events and their status.

## 2. Roles

| Role | Who | Can do |
|---|---|---|
| **Local Events Rep** | One or more per church | Create and edit their church's events, upload flyers, submit the quarter |
| **Church Leader** | Pastor or leader of a church | Same as Local Rep, plus sign off before the church submits **[?]** |
| **Flyer Reviewer** | Person who checks flyers | Approve a flyer or send it back with comments |
| **Regional Events Rep** | One per region | See every church's events, approve or decline events, set deadlines, override the calendar limit |
| **Viewer** | Any member | See the calendar of approved events (read-only) |

One person can hold more than one role.

## 3. Quarterly cycle

```
Regional rep opens Q window ──► Churches add events (Draft)
                                       │
                                       ▼
                          Church submits the quarter (Submitted)
                                       │
               ┌───────────────────────┼────────────────────────┐
               ▼                       ▼                        ▼
       Flyer review             Regional review           Calendar check
  (Approved / Changes)   (Approved / Changes / Declined)   (max 2 per day)
               └───────────────────────┬────────────────────────┘
                                       ▼
                     Event Approved + Flyer Approved = Ready
                                       │
                                       ▼
                       Shown on the shared calendar
```

- **Submission window:** the regional rep sets an open date and a deadline for each quarter (for example, Q1 Jan–Mar submissions are due by Dec 15).
- **Reminders:** emails go out to churches that haven't submitted, at 2 weeks, 1 week and 2 days before the deadline.
- **Late submissions:** after the deadline a church can still submit, but the submission is marked **Late** and the regional rep decides whether to accept it. **[?]**

## 4. Event fields

| Field | Required | Notes |
|---|---|---|
| Title | Yes | |
| Type | Yes | Bible social, Seminar, Cleanup, Blood donation, Youth, Outreach, Other (the list can be edited) |
| Church | Yes | Filled in automatically from the person's account |
| Date and start/end time | Yes | |
| Location / address | Yes | |
| Description | Yes | |
| Contact person and phone | Yes | |
| Needs support from other churches? | No | Yes/no plus notes, e.g. "need 5 volunteers" |
| Expected attendance | No | |
| Flyer | Required before approval **[?]** | Image or PDF |

## 5. Statuses

**Event:** Draft → Submitted → (Changes requested ↔ Submitted) → Approved / Declined → (Cancelled)

**Flyer:** Not uploaded → Pending review → Approved / Changes requested (with a comment) → re-upload → Pending review

The person who submitted sees every comment and status change and gets an email when one happens.

## 6. Calendar rule: at most 2 events per day

- When someone picks a date, the form shows what is already booked that day.
- If the day already has 2 events, the date is blocked. Only the regional rep can override it.
- Submitted and approved events count toward the limit (drafts don't), so the first church to submit gets the date.
- Whether the limit applies across the whole region or to each church separately is still open. **[?]**

## 7. Screens (MVP)

1. **Log in**
2. **My church's quarter**: list of events for the open quarter, with statuses, the deadline countdown and a "Submit quarter" button
3. **Event form**: the fields above, with the calendar check built in
4. **Shared calendar**: month view of every church's events, color-coded by status
5. **Flyer review queue** (Flyer Reviewer): flyer preview with Approve and Request changes buttons and a comment box
6. **Regional dashboard**: every church with its submitted/late/missing status and its events, plus approve/decline and CSV/PDF export of the quarter report
7. **Settings** (Regional): churches, users and roles, event types, quarter deadlines

## 8. Suggested tech

- A **web app** that works on phones, so nobody has to install anything.
- **Next.js** for the app and **Supabase** for logins, the database and flyer storage. Both have free tiers that cover a region of churches.
- Email through Supabase or Resend.

## 9. Build phases

1. **MVP**: logins and roles, events, quarterly submission, flyer upload and review, shared calendar with the 2-per-day rule, regional dashboard
2. **Next**: email reminders, export of the quarterly report, a sign-up list for volunteers on events that need support
3. **Later**: post-event reports (attendance, photos), a year-over-year history

## 10. Open questions

1. How many churches are in the region, and how many people per church will submit?
2. Who gives final approval of events: the regional rep, someone above them, or both? Does a pastor need to sign off before a church submits?
3. Is the flyer reviewer the same person as the regional rep, or someone else?
4. Does the 2-per-day limit apply to the whole region or to each church? Should a full day be blocked, or only show a warning?
5. Do flyers have to be in at submission time, or can they come later (for example, 3 weeks before the event)?
6. Does the event schedule follow calendar quarters (Jan–Mar, Apr–Jun, …)? What are the exact submission deadlines?
7. After an event is approved, what happens if it moves to another date or is cancelled? Does it need approval again?
8. Does the approved list go to anyone outside the region (a conference or headquarters)? In what format?
9. Does the app need more than one language?
10. Who will maintain the app once it's built, and is there a budget for hosting (it can probably be $0)?
