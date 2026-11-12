# Local recovery and session storage

Windows sessions are protected with DPAPI under the Windows account running the
backend. Access and rotating refresh tokens never enter browser storage, logs,
Git, or the registration metadata file. Restart under the same Windows account
to restore the encrypted session. Other operating systems currently retain
memory-only ChatGPT credentials. Hosted API-key mode does not use this store.

Refreshes use the issued client ID, replace the rotating refresh token, and hold
a local file lock to serialize renewal. Rejected refreshes require sign-in;
transient network failures retain the session for retry. Disconnect attempts
remote revocation and always clears local credentials; the UI reports when remote
revocation could not be confirmed. Use a single backend process for this local app.

The old memory-only session cannot be migrated without a fresh sign-in. Once signed
in using this version, subsequent restarts on the same account should retain access.

## Consistent database backup

Run from the project root, choosing a new destination each time:

```powershell
.venv/Scripts/python -m app.maintenance backup reality.db .local/backups/reality-backup.db
.venv/Scripts/python -m app.maintenance inspect .local/backups/reality-backup.db
.venv/Scripts/python -m app.maintenance restore .local/backups/reality-backup.db .local/restored-reality.db
```

The SQLite online-backup API takes a consistent snapshot, then checks integrity and
required tables. Restore always targets a new file and refuses to overwrite live
data. To recover, stop the app, set `DATABASE_URL` to the verified restored file,
run migrations, and restart. Keep the previous database for rollback. Never restore
an untrusted database. Copy encrypted session files only if you understand their
Windows-account binding; database backups intentionally exclude credentials.

Sources: [OpenAI session lifecycle](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions),
[Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).
