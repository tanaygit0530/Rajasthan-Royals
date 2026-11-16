# Deploying the evaluator site (private, free tier)

The site is static. All data and the report are **encrypted at build time** (AES-256-GCM, key derived from the
password with PBKDF2-SHA256, 250,000 iterations) and decrypted only in the visitor's browser after the password is
entered. So it stays private on any free host, without the host's paid password feature. It is also marked
`noindex` three ways (meta tag, `robots.txt`, `X-Robots-Tag` header).

Always build locally (the build needs the private data and the password, which never leave your laptop):

```bash
cd site
echo "SITE_PASSWORD=choose-a-strong-password" > .env.local    # only if you want to change the password
./run.sh            # exports, encrypts, builds, runs the security check, serves locally; Ctrl+C when happy
```

Then upload only the `site/dist` folder.

## Option A – Netlify Drop (no account setup, ~2 minutes)
1. Go to https://app.netlify.com/drop and sign in (free).
2. Drag the `site/dist` folder onto the page. Netlify gives you a URL like `https://random-name.netlify.app`.
3. Site configuration → Change site name → e.g. `rr-pressure-scout-<something-unguessable>`.
4. The `_headers` file in `dist` adds `X-Robots-Tag: noindex` automatically.

## Option B – Netlify CLI
```bash
cd site && npx netlify-cli deploy --dir=dist --prod
```

## Option C – Vercel CLI
```bash
cd site && npx vercel deploy dist --prod
```
`dist/vercel.json` sets the `X-Robots-Tag` header. In the Vercel dashboard, keep "Deployment Protection" off for
the production URL (the site has its own password gate), or evaluators will be asked to log in to Vercel.

## After deploying
1. Open the URL in a private window: you should see only the password screen.
2. Check that a wrong password is rejected and the right one opens the site.
3. Optional: `curl -s https://<your-url>/enc/players.json.bin | head -c 64 | xxd` – only random bytes.
4. Send evaluators the URL and the password **in separate messages**.

## Updating
Re-run `./run.sh` (new data or a new password) and upload `dist` again. A new build uses a new random salt, so old
cached data cannot be decrypted with the new password.
