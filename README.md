# Church Events / Eventos de la Iglesia

A web app for planning each quarter's church events across the region. It works on any phone or computer, and nobody has to install anything.

- Churches add their events for the quarter and send them for approval.
- The Regional Events Rep or the Overseer approves events, asks for changes or declines them.
- **2 events per day across the whole region.** A church can't send a third event for a full day. It can ask for an exception, and the Regional Events Rep or the Overseer can approve it.
- **Flyers:** the church uploads the flyer, and the Overseer or the Regional Events Rep reviews it. If the flyer needs changes, they send it to the Graphic Designer with notes. After the designer uploads the fix, they give the final OK. You can switch this to automatic approval in Settings.
- **Flyer deadlines:** due 2 weeks before the event, with a final deadline 1 week before. Both can be changed in Settings.
- **Changes after approval:**
  - If the Regional Events Rep or the Overseer moves an event, the change applies right away and the church is notified.
  - If a church asks for a change, the Regional Events Rep and the Overseer are notified and approve or decline it.
- **Quarters** run Jan–Mar, Apr–Jun, Jul–Sep and Oct–Dec. Submissions are due 2 weeks before the quarter starts. Anything sent after that is marked "late".
- **Public calendar** at `/public/`: members can see approved events without logging in. Under the month there is a slideshow of this week's and next week's events, with the flyer, the time and an **Invite on WhatsApp** button. The page refreshes itself.
- **Reports:** download as Excel or PDF, filtered by quarter, church, type or status.
- **Post-event reports:** after an event, the church reports how many Church of God members and supporters from other churches attended (and from which churches), invites, the cost, the **fragrance** (testimonies or something nice that happened) and photos. Bible socials also ask for members who supported, fruits and Bible studies; Seminars also get it from the start, and admins can switch the full report on or off for any event type in Settings. The Regional Events Rep and the Overseer are notified, and the totals show on the **After the event** page and in the Excel download.
- **Languages:** Spanish and English. Each person picks one with the ES / EN buttons.
- **In-app notifications** (🔔).
- **Email reminders:** off until an admin turns them on (see below). WhatsApp to the region's group chat is planned for later.

## Roles

| Role | Can do |
|---|---|
| Church Leader / Church Events Rep | Add, edit and send their church's events. Upload flyers. Ask for changes to approved events |
| Regional Events Rep / Overseer | Approve, decline or change any event. Approve exceptions. Review flyers and send them to the designer. See the region overview and reports |
| Graphic Designer | See the flyers that need fixes and upload the corrected versions |
| Tech Admin | Manage the system |

Anyone with **"can manage users and settings"** turned on (for example the Regional Events Rep) can add users and churches, edit event types and change the rules and deadlines.

## Installing on the Zima server

You need Docker, which ZimaOS already has. Open a terminal on the Zima server and run:

```sh
git clone https://github.com/Manny1994RD/EventSystem.git
cd EventSystem
cp .env.example .env
nano .env          # fill in SECRET_KEY, your Tailscale address and the admin password
docker compose up -d --build
```

The app now runs on port **8000**. The first time it starts, it creates the 5 churches (Santiago, La Vega, Moca, Jarabacoa, Puerto Plata), the event types and the admin user from `.env`.

### Sharing it through Tailscale

- **Tailscale Serve** makes the app reachable only by devices on your tailnet, over HTTPS:
  `tailscale serve --bg 8000`
- **Tailscale Funnel** opens the app to anyone with the link, which church members need for the public calendar:
  `tailscale funnel --bg 8000`

Put the address Tailscale gives you (for example `zima.your-tailnet.ts.net`) in `.env` under both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (with `https://` in front for the second one). Then restart:

```sh
docker compose up -d
```

### After installing

1. Open the link and log in with the admin username and password from `.env`.
2. Go to **Users → Add a user** and create each person. Pick their role and their church, and give them a password.
3. Send everyone the link. Church members get the public calendar: `https://<your address>/public/`

### Turning on email reminders

Email is off at first. When you're ready:

1. Log in as an admin and go to **Settings → Email reminders**.
2. Enter the email to send from (for example the Regional Events Rep's Gmail).
3. For Gmail, turn on 2-step verification on that account, create an "app password" at myaccount.google.com/apppasswords, and paste it into the password box.
4. Turn on **send emails**, then press **Save and send me a test email**.

Reminders go out once a day:

- 14, 7, 2 and 0 days before the quarter deadline, to churches that haven't sent everything.
- On each flyer's due date and final deadline.

You can also choose to email every notification. People only get emails if their account has an email address.

### Data and backups

Everything is stored in the folder set by `DATA_PATH` in `.env`:

- `db.sqlite3`: the database
- `media/`: the flyers
- `backups/`: one backup per day, keeping the last 14 (the `scheduler` container also sends the daily email reminders)

To restore a backup, stop the app (`docker compose down`), extract the backup file into `DATA_PATH`, then start it again.

### Updating

```sh
git pull
docker compose up -d --build
```

### Tech admin panel

`/tech-admin/` is Django's built-in admin, for low-level fixes. Only superusers can open it.

## Development

```sh
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py load_demo      # demo users; every password is demo12345
python manage.py runserver
```

The demo users are `regional`, `overseer`, `designer`, `rep.santiago`, `leader.lavega`, and so on.

- Tests: `python manage.py test`
- Translations: after changing any text, run `python manage.py makemessages -l es`, fill in the new entries in `locale/es/LC_MESSAGES/django.po`, then run `python manage.py compilemessages`.
