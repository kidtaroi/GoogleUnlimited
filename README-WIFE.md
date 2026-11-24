# GoogleUnlimited — simple setup for macOS

This fork adds a small desktop helper so sign-in does not require opening browser developer tools.

## One-time install

1. Open Terminal and run:

```
cd ~/GoogleUnlimited-Wife
./install-on-mac.sh
```

2. Double-click **`WifeSetup.command`** in the folder.

## Sign in

1. Click **Sign in with Google**.
2. A private browser window opens on Google's sign-in page.
3. Sign in with the Google account you want to back up, and click **I agree**.
4. Come back to the helper window. It detects the sign-in, saves the account locally, and starts the background watcher.

The sign-in browser uses a temporary profile that is deleted afterward. The helper reads only the `oauth_token` cookie from that temporary session. It never reads cookies from your normal browser and never sends the token to any server. The token is stored in the local `gotohp` config with owner-only permissions.

## Daily use

Put photos or videos into the **Photo Backup Drop** folder in your Downloads folder. You can also use:

```
~/Google Photos Uploads
```

They are the same folder — Downloads contains a shortcut to the real folder, which lives in your home directory so the background watcher can read it. The watcher uploads anything you drop in automatically. You can leave the folder and the app alone.

The helper window also has:

- **Check status** — shows upload counts and recent activity.
- **Open backup folder** — opens the watched folder in Finder.
- **Stop backups** — stops the background watcher. It starts again at next login.

To start it again after stopping, double-click `WifeSetup.command` and click **Sign in with Google** (no need to re-enter the password unless the session expired).

## Important caveats

- This tool impersonates an original Pixel device to get unlimited, original-quality backup. That is an unofficial loophole, not a Google feature. Google can change or block it at any time, and it may violate Google's Terms of Service.
- Keep an independent backup of anything important. This is not a replacement for one.
- The uploader is an unsigned third-party binary. Only use it with an account you are comfortable taking that risk with.
- If macOS asks about the downloaded binary, the upstream project documents this as an antivirus false positive. Verify the checksum before allowing it if you want the extra assurance.
