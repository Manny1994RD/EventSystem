# Church Event System: Requirements

Status: draft, round 2. Items marked **[?]** are still open.

## 1. Goal

Replace the quarterly "send in your event list and flyers, then wait" process with one app where:

- each church submits its events for the coming quarter before the deadline,
- flyers are uploaded and reviewed in the same place, and handed to the graphic designer when they need changes,
- everyone can see one shared calendar for the region, so no more than 2 events land on the same day,
- the regional events rep and the overseer see every church's events and their status, and can download the report.

The app runs on our own Zima server. All data (database and flyer files) is stored on that server.

## 2. Region and churches

Northern region, 5 churches to start:

- Santiago
- La Vega
- Moca
- Jarabacoa
- Puerto Plata

Admins can add churches (or deactivate them) from Settings. Users, events and reports are all linked to a church. The system supports more than one region later if needed.

## 3. Roles

| Role | Scope | Can do |
|---|---|---|
| **Church Events Rep** | Their church | Create and edit their church's events, upload flyers, submit the quarter, request changes to approved events |
| **Church Leader** | Their church | Everything the Church Events Rep can do, plus see their church's history **[?] sign-off before submitting?** |
| **Regional Events Rep** | Whole region | See every church's events, approve or decline events, move dates (no re-approval needed), override the 2-per-day limit, manage quarters and deadlines |
| **Overseer** | Whole region | Review and approve flyers, approve events, move dates (no re-approval needed), override the 2-per-day limit, download reports |
| **Graphic Designer** | Flyers sent to them | See flyers that need changes along with the overseer's notes, upload the corrected version |
| **Admin** | Whole system | Create and deactivate users, assign roles and churches, add churches, edit event types **[?] who is admin: Regional Rep, Overseer, or both?** |
| **Viewer** | Read only | See the calendar of approved events **[?] do members need a login, or is it a public link?** |

One person can hold more than one role.

## 4. Quarterly cycle

```
Regional rep opens the quarter's submission window
            │
            ▼
Churches add events (Draft) ── calendar check: max 2 per day across the region
            │
            ▼
Church submits the quarter (Submitted)
            │
            ▼
Event review by the Regional Rep / Overseer ──► Approved / Changes requested / Declined
            │
            ▼
Flyer upload (due at least 1–2 weeks before the event)
            │
            ▼
Overseer reviews the flyer
     ├── Approved ───────────────────────────────► Event is READY
     └── Needs adjustment ──► Graphic Designer fixes it and uploads the new version
                                       └──► back to the Overseer [?]
```

- **Submission window:** the regional rep sets an open date and a deadline for each quarter.
- **Reminders:** sent to churches that haven't submitted, before the deadline.
- **Late submissions:** marked **Late**. The regional rep or overseer decides whether to accept them.

## 5. Calendar rule: max 2 events per day, across the whole region

- When someone picks a date, the form shows what is already booked across the region that day.
- If the day already has 2 events, the church **cannot submit** that event.
- The Regional Events Rep or the Overseer can **override** the limit to approve a 3rd (or later) event. The override is logged with the name of the person who made it and their reason.
- Submitted and approved events count toward the limit. Drafts don't.

## 6. Flyer rules

- A flyer can be uploaded at submission time or later.
- **Due date:** at least 1–2 weeks before the event. **[?]** Proposed: a reminder 3 weeks before, a warning at 2 weeks, and the event is flagged **Flyer overdue** at 1 week.
- **Statuses:** Not uploaded → Pending overseer review → Approved, or Pending overseer review → Sent to designer (with notes) → Designer uploaded a revision → Pending overseer review **[?]** → Approved
- Every version of a flyer is kept, so you can see what changed.

## 7. Changes after approval

| Who changes the event | Result |
|---|---|
| Regional Events Rep or Overseer | The change applies right away. No re-approval. The church is notified. |
| The church (Rep or Leader) | Becomes a **change request**. The Regional Events Rep and the Overseer are notified and approve or decline it. The approved version stays in place until they decide. |

Cancellations follow the same rule. The calendar limit is checked again whenever a date moves.

## 8. Event fields

| Field | Required | Notes |
|---|---|---|
| Title | Yes | |
| Type | Yes | Bible social, Seminar, Cleanup, Blood donation, Youth, Outreach, Other (Admin can edit the list) |
| Church | Yes | Filled in automatically from the user's account |
| Date and start/end time | Yes | |
| Location / address | Yes | |
| Description | Yes | |
| Contact person and phone | Yes | |
| Needs support from other churches? | No | Yes/no plus notes |
| Expected attendance | No | |
| Flyer | Before the flyer due date | Image or PDF |

## 9. Reports

- The Overseer (and the Regional Rep) can download the quarter's report, filtered by church, status and event type.
- **Format:** Excel and/or PDF **[?]**
- Contents: every event, its status, flyer status, dates, contact and who approved it.

## 10. Screens (MVP)

1. **Log in**
2. **My church's quarter**: event list, statuses, deadline countdown, "Submit quarter" button
3. **Event form**: with the calendar check built in
4. **Shared calendar**: month view of the whole region, color-coded by church or status
5. **Flyer review** (Overseer): preview, then Approve, or send to the designer with notes
6. **Designer queue** (Graphic Designer): flyers that need changes, the notes, a box to upload the revision
7. **Regional dashboard**: each church's submitted/late/missing status, approvals, change requests, overrides, report download
8. **Settings** (Admin): users and roles, churches, event types, quarters and deadlines

## 11. Hosting: self-hosted on the Zima server

- Shipped as a **Docker Compose** app (ZimaOS runs Docker apps natively):
  - `app`: the web app (Next.js, works on phones)
  - `db`: PostgreSQL, data saved to a volume on the Zima server
  - flyer files saved to a folder on the Zima server
- Logins are handled by the app itself, with passwords stored hashed. No outside service holds the data.
- **Backups:** a nightly database dump and a copy of the flyer folder to another drive. **[?]**
- **Access from outside the house/church:** to share one link with everyone, the server must be reachable from the internet over HTTPS. Options: Cloudflare Tunnel (free; needs a domain), Tailscale Funnel, or port-forwarding with a domain. **[?]**

## 12. Build phases

1. **MVP**: users and roles, churches, events and quarterly submission, the calendar rule and overrides, flyer review and designer handoff, change requests, regional dashboard, report download, Docker setup for Zima
2. **Next**: email/WhatsApp notifications and reminders, volunteer sign-ups for events that need support
3. **Later**: post-event reports (attendance, photos), history across years

## 13. Open questions (round 2)

1. After the graphic designer uploads the fixed flyer, does it go back to the Overseer for a final OK, or is it approved automatically?
2. Who approves the **event itself** (not the flyer): the Regional Events Rep, the Overseer, or either one?
3. Does the Church Leader need to sign off before their church submits, or can the Church Events Rep submit alone?
4. Flyer deadline: is 2 weeks the target and 1 week the hard cutoff? What happens after the cutoff (block the event, or only flag it)?
5. App language: Spanish, English, or both with a switch?
6. Notifications: email, WhatsApp, or both? (Email is free. WhatsApp needs a WhatsApp Business account and may cost a little.)
7. Who is the Admin who creates users: the Regional Events Rep, the Overseer, or both?
8. Do church members need a login to see the calendar, or should there be a public calendar link?
9. Report format: Excel, PDF, or both?
10. Is the Zima server already reachable from the internet? Do you have a domain name (e.g. `eventos.yourchurch.org`)?
11. Quarter dates: calendar quarters (Jan–Mar, Apr–Jun, …)? What is the usual submission deadline (e.g. 2 weeks before the quarter starts)?
