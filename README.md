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

Every time code is pushed to GitHub, a ready-made app image is built automatically (`ghcr.io/manny1994rd/eventsystem`). The Zima server just downloads it, so nothing gets built on the server.

> **One-time step on GitHub:** after the first build finishes (the **Actions** tab shows a green check), go to your GitHub profile → **Packages** → **eventsystem** → **Package settings**, and change the visibility to **Public**. Then the Zima server can download it without a GitHub login.

### Option A: from the ZimaOS dashboard (no terminal)

1. Open **App Store** → **+** (top right) → **Install a customized app** → **Import**.
2. Paste the contents of [`zimaos/church-events.yml`](zimaos/church-events.yml).
3. Change `APP_URL` to your Tailscale address (for example `https://zima.your-tailnet.ts.net`), then press **Install**.

### Option B: with a terminal

```sh
git clone https://github.com/Manny1994RD/EventSystem.git
cd EventSystem
cp .env.example .env
nano .env          # only APP_URL is required
docker compose up -d
```

### Sharing it through Tailscale

- **Tailscale Funnel** opens the app to anyone with the link. Church members need this for the public calendar:
  `tailscale funnel --bg 8000`
- **Tailscale Serve** only lets devices on your tailnet open it:
  `tailscale serve --bg 8000`

`APP_URL` must be the address Tailscale shows you, with `https://` in front.

### The first time you open it

1. The app asks for a **setup code**. You'll find it in the file `setup-code.txt` in the data folder (in ZimaOS: **Files** → `AppData/church-events/data`), or in the app's log (`docker compose logs app`).
2. Enter the code, then create your admin account.
3. The app starts with the 5 churches (Santiago, La Vega, Moca, Jarabacoa, Puerto Plata) and the event types already set up.
4. Go to **Users → Add a user** and create each person. Pick their role and their church, and give them a password.
5. Send everyone the link. Church members get the public calendar: `https://<your address>/public/`

A secret key is created automatically and kept in the data folder.

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

- `DATA_PATH` (default `/DATA/AppData/church-events/data`): the database (`db.sqlite3`), the flyers and photos (`media/`) and the secret key.
- `BACKUP_PATH` (default `/DATA/AppData/church-events/backups`): one backup per day, keeping the last 14. **Point this at a different drive** (for example a USB disk) so a broken disk doesn't take the backups with it.

The `scheduler` container makes the backups and sends the daily email reminders. ZimaOS shows each container's health (the app has a built-in health check), and restarts it if it stops.

To restore a backup: stop the app, extract the backup file into `DATA_PATH`, then start the app again.

### Updating

```sh
docker compose pull && docker compose up -d
```

In ZimaOS you can also open the app's settings and press **Update** (or **Rebuild**). To update automatically every night, turn on the `updater` service at the bottom of `docker-compose.yml`.

### Security built in

- After 5 wrong passwords, that account is locked for 15 minutes.
- Django's low-level admin (`/tech-admin/`) is **off** by default. To use it for a while, add `TECH_ADMIN_ENABLED=1` to `.env` and restart. Only superusers can open it.
- Only the person with the setup code can create the first admin account.
- Uploaded pictures are checked to make sure they really are pictures.
- Every push to GitHub runs all the tests first. Dependabot opens update requests for security fixes. Django stays on version 5.2, which gets security fixes until April 2028.

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
