# Microsoft 365 Status Watcher

A small, dependency-free CLI that watches Microsoft's macOS service-status RSS
feed and prints new or changed incidents in a readable format.

## Run

Requires Python 3.10 or later.

```sh
python3 watcher.py
```

The app checks the feed immediately, then refreshes every five minutes, or
whenever you press `Enter` in the terminal. It prints the current feed entries
on startup and only prints entries again when their content changes. Press
`Ctrl+C` to stop.

## Test

```sh
python3 -m unittest
```
