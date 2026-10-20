# Church Event System: Requirements

Status: round 3. The first version is built (see README.md). Section 13 lists the decisions made so far and what is still open.

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

## 13. Decisions (round 3)

| Topic | Decision |
|---|---|
| Fixed flyer from the designer | Goes back to the Overseer for the final OK. A setting can make it automatic. |
| Who approves events | The Regional Events Rep **or** the Overseer. Either one is enough. |
| Who submits | The Church Leader **or** the Church Events Rep. No extra sign-off needed. |
| Flyer timing | Target: 2 weeks before the event. Final deadline: 1 week before. After the deadline the event is flagged as late, not blocked. |
| Language | Spanish and English, with a switch. Spanish is the default. |
| Notifications | In the app for now. WhatsApp group messages are a later project. |
| Admin | The Regional Events Rep (with "can manage users and settings" turned on) and a Tech Admin |
| Members | A public calendar link with no login |
| Reports | Excel and PDF |
| Hosting | Docker on the Zima server, shared through Tailscale (Serve or Funnel) |
| Quarters | Calendar quarters. Submissions due 2 weeks before the quarter starts. |
| Daily limit | 2 per day across the whole region. A church can ask for an exception; a reviewer approves it. |
| Ease of use | Big buttons, a to-do list on the home screen, a step tracker on each event, a live "is this day free?" check, and confirmation before anything is deleted |

## 14. Decisions (round 4)

| Topic | Decision |
|---|---|
| Who reviews flyers | The Overseer **or** the Regional Events Rep. Either one can approve or send to the designer. |
| Public calendar | Public, with no contact phone numbers |
| WhatsApp (later) | One group chat for the whole region |
| Email | Built but **off**. When ready, an admin enters the Regional Events Rep's email in Settings → Email reminders, turns it on, and sends a test. |

## 15. Still open

1. WhatsApp group messages: a separate project, for later.
2. Post-event reports (attendance, photos): do you want them in a later phase?
