# Importer

Brings the old MongoDB notes into the app. Only the `dev` account and table are supported for now.

## Fragments from a MongoDB export

```bash
cd backend && source .venv/bin/activate
aws sso login --profile smartvibes-dev

python -m importer.import_mongo <export.json> --user-id <cognito-sub>        # dry run: plan and problems
python -m importer.import_mongo <export.json> --user-id <cognito-sub> --yes  # write
```

- `--user-id` is the Cognito `sub` of the user who will own the fragments (`GET /me` returns it).
- `--tag-separator` says what splits the old `tags` string (default `,`).
- Each record's ID is built from its `createdAt` and a hash of its Mongo `_id`, so running the
  import again overwrites the same items instead of adding copies, and the items keep their
  original dates and order. (The fast Home list finds items by the time in their ID.)
- The app's own limits apply (text up to 2,000 characters, at most 10 tags of 30 characters).
  Records that break a limit are listed and skipped. Leading and trailing spaces are trimmed.
- `owner` and `__v` are ignored.
