# Out of Comfort Zone — Malaysia Business News Instagram Automation

Account: **@outofcomfortzone.daily** · Time zone: **Asia/Kuala_Lumpur**.

## Safety-first status

- **Demo runs do not publish**. Uses 5 unmistakably fake SAMPLE ONLY items for graphics testing, without accessing The Edge Malaysia.
- Live preparation uses publisher RSS metadata, verifies each publisher article URL still exists, selects exactly five recent and non-repeated items, and skips incomplete days. **RSS attribution plus URL checking is not independent verification of the article's assertions.** Only enable unattended news publishing after editorial review of the feed's reliability and permissions.
- News summaries are compact publisher-feed excerpts / minimally edited source metadata: they are **not AI fact-checks** or independently authored reporting. Do not call them original investigative summaries.
- **Publishing is disabled by default** and requires BOTH repository variables `ENABLE_PUBLISH=true` and `RIGHTS_CONFIRMED=true`.
- Images use original PIL vector art, **not copied article photographs**, with clear attribution and publisher URLs in the Instagram caption.
- A successful Meta publication updates the seen-story history. A failed run does not falsely report publication.

## 1 — Run the safe test

1. Create a new **private GitHub repository** (e.g. `out-of-comfort-zone-news`) and upload all files, including the `.github/workflows` directory.
2. In **Actions**, choose **Prepare Malaysia news carousel** → **Run workflow** → keep `demo=true` → Run.
3. Download `instagram-carousel` from that workflow's **Artifacts** section and inspect the six `.jpg` slides and caption. It is deliberately synthetic demo text; **never publish it**.
4. You can test locally: `pip install -r requirements.txt`, then `python -m unittest discover -s tests`, then `python src/pipeline.py prepare --demo`.

## 2 — Configure GitHub Pages image hosting

Meta pulls carousel images from publicly accessible URLs. A *private* GitHub repository with public GitHub Pages output might not be available on all plans/account configurations. **Free simple option: create a separate public repository for the generated `docs/daily` assets and publish it with GitHub Pages**, or use a public repository for this project with all tokens stored only in Secrets. No copyrighted publisher photography is stored.

For a public project repository:

1. GitHub repository → **Settings → Pages → Build and deployment → Deploy from a branch**.
2. Branch: `main`; folder: `/docs`; Save.
3. Set **Actions → General → Workflow permissions** to `Read and write permissions` (for committing generated files and history).
4. Verify the image URL after a *live* prepare run, e.g. `https://USERNAME.github.io/REPOSITORY/daily/YYYY-MM-DD/01_cover.jpg`.
5. Store `PAGES_BASE_URL=https://USERNAME.github.io/REPOSITORY` in **Settings → Secrets and variables → Actions → Variables**. Do not include `/docs` in this URL.

Do not enable publishing until Pages serves **all six current-day photos** from the public URLs. GitHub Pages deployment can lag, so the 7:30 target is not guaranteed.

## 3 — Meta authorization (Instagram Login path)

Use **[Meta for Developers](https://developers.facebook.com/)** to create an app and add the **Instagram API with Instagram Login** product. Follow Meta's current steps for **Business Login for Instagram**, not the older Facebook Login flow.

1. Confirm the Instagram account is **Business or Creator** and that you control it.
2. Configure Instagram Login and request only `instagram_business_basic` and `instagram_business_content_publish`.
3. Add the Instagram account as an app/tester or eligible authorized account as Meta requires; perform the Meta login, permissions grant, and generate an authorized Instagram user token. App permissions, testing status and App Review requirements depend on your account and distribution.
4. Resolve the **Instagram Professional account ID** through Meta's authorized `me` endpoint or Meta's own API setup instructions. Do **not** use the numeric Metricool brand ID, Instagram username, or personal profile ID in its place.
5. Follow Meta guidance to exchange for a longer-lived token and renew it on time. A short-lived token cannot sustain unattended daily posting indefinitely.
6. In GitHub repository → **Settings → Secrets and variables → Actions → Secrets**, create `IG_ACCESS_TOKEN` and `IG_USER_ID`.
7. In **Variables**, set `META_API_VERSION` to the current supported Instagram Graph API version (initial template default `v24.0`; check Meta's changelog before enabling), and `PAGES_BASE_URL` to the published GitHub Pages base address.
8. Keep `ENABLE_PUBLISH=false` until you have reviewed a live preview and demonstrated account authorization.

**Never enter tokens in repository code, public Issues, README, or chat.** You authenticate in Meta directly.

## 4 — News licensing and editorial safeguards

Read **[The Edge Malaysia terms](https://theedgemalaysia.com/article/terms-use)** and obtain necessary written permission before automated commercial reuse of its RSS summaries or other material. The script intentionally does not bypass subscriptions, copy full article text, or reuse copyrighted images. Public visibility or an RSS endpoint does **not** grant republication rights. The `RIGHTS_CONFIRMED` flag must reflect actual authorization, not a guess.

RSS feed URL is configurable as `EDGE_FEED_URL` (default `https://myassets.theedgemalaysia.com/arc/outboundfeeds/rss`). Live feed availability and licensing must be checked by you. Automated access to publisher URLs is subject to its rules; seek authorization first.

Live quality checks require **exactly five distinct recent feed items**, with nonempty source snippets and resolvable direct publisher article URLs. If fewer than five pass, **skip that day's carousel**. No fake articles, links, or photos are inserted.

## 5 — Daily schedule

- **07:05 MYT** GitHub Actions `prepare.yml` fetches feed, scores headlines, checks links, creates `docs/daily/YYYY-MM-DD` original graphics, and commits them to the branch for Pages.
- **07:30 MYT** `publish.yml` attempts the six-image carousel through the official Instagram API only if both authorization flags are true and all images are accessible at Pages URLs.
- GitHub scheduled actions can start late; **7:30 AM is a target**, not a guaranteed deadline.
- Production publishing is not enabled or remotely deployed just by downloading this project.

## 6 — First safe production test

1. **First test:** run workflow `Prepare Malaysia news carousel` with `demo=true`. Inspect the artifact. This test never posts.
2. With licensing confirmed, run `Prepare Malaysia news carousel` with `demo=false`. Inspect the generated live article headlines, published dates, URLs, captions and slides **manually**. If the feed returns fewer than five eligible stories, expect a safe failure.
3. Confirm all six generated image URLs load publicly from GitHub Pages.
4. Keep `ENABLE_PUBLISH=false` while verifying Meta authorization and media access.
5. Only after you've reviewed the news feed and verified permitted publication, set `RIGHTS_CONFIRMED=true`, `ENABLE_PUBLISH=true`. A **manual run of Publish Instagram carousel then makes a real PUBLIC post**; it is not a dry-run. Do not click it until ready for a live publication.
6. Monitor Actions status and Instagram profile. The workflow does not send phone push notifications out of the box.

## Limitations and follow-ups

- This project uses template graphics, not a paid AI image model.
- The feed's snippets may be promotional or incomplete; the script refuses short descriptions but does not independently fact-check them. Editorial/legal review recommended before unattended public news posting.
- Instagram captions normally contain non-clickable plain-text external links. For clickable articles, place a link to your own licensed links page in your bio.
- Meta's API version, permission names, and app-review requirements may change; review official documentation before entering credentials.
- On a GitHub Free public repository, keep all tokens in Actions Secrets. External services, bandwidth and accounts can carry separate cost/limit terms.
