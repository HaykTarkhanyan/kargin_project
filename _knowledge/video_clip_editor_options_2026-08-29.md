# In-site clip cutting: stack options and approach (2026-08-29)

Research for "let visitors cut their own clips from a sketch, inside the site."
Nothing was built or installed. This is the options file; the choice goes in
`DECISIONS.md` once made.

Method: read the current player code (`web/components/WatchView.tsx`, a plain
YouTube iframe, no player API), measured the corpus locally, listed real
yt-dlp format sizes for one video, probed keyframe spacing on the one local
video file, and read current (August 2026) docs and pricing pages for every
candidate. Web claims are cited at the bottom; everything measured here says so.

---

## TL;DR

There are three tiers, and they stack rather than compete:

| Tier | What the visitor gets | Video bytes live | Needs a server | Works on every browser | Runtime cost |
|---|---|---|---|---|---|
| **0. Timestamp share** | a link that opens the sketch at 0:12 and stops at 0:25 | YouTube (nothing new) | no | yes | $0 |
| **1. Cut in the browser** | an MP4/WebM file, cut on their own device | our copy on R2 (~16-19 GB at 720p) | no | WebCodecs browsers only (no Firefox Android, no old Safari) | ~$0.15/month |
| **2. Cut on a server** | an MP4 file, frame-exact, any device | our copy on R2 | yes | yes | $5-12/month plus per-clip compute |

Tier 0 is the substrate for the other two (same in/out picker, same preview),
costs nothing, and is exactly what YouTube itself replaced Clips with in April
2026. Build it first whatever else is decided.

**My pick for producing files: Tier 1 with Mediabunny over R2.** The site stays
static, the cut is hardware-accelerated and takes seconds, the library is the
most alive thing in this space, and the running cost rounds to zero. Reasons
to pick differently are listed under "What would flip this".

**The hard-to-reverse part is not the editor. It is the source-video store**:
downloading 702 videos once, choosing 720p vs 360p, and how the files are
conditioned (faststart, keyframe spacing). Every option above needs it except
Tier 0, and re-doing it means re-downloading 16-19 GB from YouTube.

---

## 1. The constraints that shape everything

### 1.1 The site is static and cannot host video bytes

`next.config.ts` has `output: "export"`; hosting is GitHub Pages behind
`karginhaghordum.am`. GitHub Pages is capped at 1 GB per site and a soft
100 GB/month of bandwidth [GH-limits]. Even the 360p corpus is ~5 GB, so the
video files have to live somewhere else regardless of which tier is chosen.

GitHub Pages also cannot set response headers, which matters for one candidate
(multi-threaded ffmpeg.wasm needs COOP/COEP). There is a service-worker
workaround, `coi-serviceworker`, that injects those headers on first load with
a page reload [COI]. It works but it is a hack, and it turns out not to be
needed (see 3.2).

### 1.2 Browsers cannot read YouTube's streams, so we need our own copy

The player is a YouTube iframe. A page cannot fetch the underlying
googlevideo stream (cross-origin, signed URLs). Every "produce a file" option
therefore starts with pulling the 702 videos with yt-dlp, which the project
already does for audio.

**Measured corpus** (from `data/youtube_metadata.csv`, 702 rows):
33.9 hours total, median 2:37, min 0:30, max 19:37. 574 videos are `hd`,
128 are `sd` only. All 702 are `embeddable`.

**Measured sizes** for one median-length video (3:20, `5h70tn0asdo`),
`yt-dlp -F`:

| format | what | size | bitrate |
|---|---|---|---|
| 136 + 140 | 720p video + m4a audio | 26.8 + 3.1 MiB | 1122 + 130 kbps |
| 18 | 360p muxed | 7.9 MiB | 332 kbps |

Scaled to 33.9 h (122,040 s): **~19 GB at 720p** (~16.6 GB if the 128 SD-only
videos come in at 360p), **~5 GB at 360p**. One video's bitrate is a rough
scaler; sketches vary. Budget 20 GB.

**Gotcha found while probing:** `uv run yt-dlp -f 136` returned
`HTTP Error 403` and warned "No supported JavaScript runtime could be found.
Only deno is enabled by default". The pinned yt-dlp is 2026.03.17; YouTube
extraction now needs a JS runtime. The bulk 720p download will need a yt-dlp
bump plus deno (or another runtime) installed, and a re-test before assuming
the pipeline from the audio sweep still works.

### 1.3 A cut without re-encoding lands seconds away from where you clicked

Video can only be cut cleanly at keyframes unless the head of the clip is
re-encoded. **Measured on the one local file** (360p, format 18, 200 s):
60 keyframes, gap min 0.96 s, **median 2.8 s, max 7.0 s**. So a "stream copy"
cut can start up to 7 seconds early. For a punchline that is unusable. The 720p
DASH stream was not measured (the 403 above); YouTube's DASH renditions usually
have longer, not shorter, GOPs.

Consequence: every option that produces a file either re-encodes (the clip is
short, so this is cheap: a 30 s 720p clip is 750 frames) or pre-conditions the
source files with dense keyframes at ingest (option 2a below).

### 1.4 The platform just removed this feature, which is the demand signal

YouTube announced on 2026-04-17 that viewer-created Clips are discontinued;
existing clips stay viewable, new ones cannot be made, and "share at timestamp"
is the replacement. Creators keep a clipping tool in Studio, which does not
help a fan archive. YouTube's stated reasoning leans on third-party tools
existing [YT-clips-9to5][YT-clips-ppc]. Those tools (Kapwing, Clideo and a
long tail) are paste-a-URL sites with watermarks or caps on the free tiers
[Kapwing][Cutters]. So: the need is real, the platform no longer serves it, and
the free alternatives are mediocre. A clip button on the sketch page is well
placed.

### 1.5 Browser capability matrix (for Tier 1)

WebCodecs (hardware decode/encode from JS) is what makes in-browser cutting
fast. Support as of 2026: Chrome/Edge since 94 (2021), Firefox 130+ on desktop
only, Safari full parity (including audio) only from Safari 26 (2025), and
**Firefox for Android has none** [WebCodecs-support][caniuse-webcodecs].

Two codec holes matter for an MP4 output:

- **AAC encoding** is missing in Firefox on all platforms and in every browser
  on desktop Linux [WebCodecs-support]. Mediabunny ships
  `@mediabunny/aac-encoder` as a polyfill, registered only when
  `canEncodeAudio('aac')` is false [MB-aac].
- **H.264 encoding in Firefox** is reported broken as of Firefox 145:
  `isConfigSupported` says yes, `configure()` then throws "The given encoding
  is not supported" [WebCodecs-firefox-h264]. Fallback is VP9 in WebM, which
  plays in browsers but is a worse file to hand someone for WhatsApp/Telegram.

Unknown and worth checking before choosing Tier 1: what share of the site's
visitors are on Firefox Android or Safari < 26. The `LOG_ENDPOINT` usage
logging worker may already have user agents.

---

## 2. Tier 0: timestamp sharing, no video processing

What YouTube itself now does, done on our page with our metadata.

**Mechanism.** Replace the bare iframe with the YouTube IFrame Player API.
`loadVideoById({videoId, startSeconds, endSeconds})` plays a bounded range;
`seekTo()` and `getCurrentTime()` drive a scrubber; the embed URL also accepts
`?start=&end=` for a preview without any JS [YT-iframe]. Gotcha from the docs:
calling `seekTo()` cancels a previously set `endSeconds`, so the preview loop
has to re-issue the bounds after every seek.

**UI.** A dual-thumb range over the player (Radix Slider supports two thumbs
and is already the style of primitive the site uses; a plain pair of inputs
also works), "set in / set out" buttons that read `getCurrentTime()`, a preview
loop, and a copy button for `karginhaghordum.am/sketch/<id>/?t=12&end=25`. The
sketch page reads those params and starts the embed bounded. A second copy
button can give the raw `youtu.be/<id>?t=12` for people who want YouTube.

**Two cheap upgrades that make picking the points much easier:**

- The raw transcripts on disk (JSON3/SRT from the batch re-uploads and the
  YouTube fetches) carry per-line timestamps that the site currently drops
  (`Transcript` ships only `text`, `events` count). Shipping the timestamps for
  the 165 transcribed sketches lets a visitor click a line to jump there, then
  set in/out from lines. This turns "scrub and guess" into "click the joke".
- We own audio for all 702 videos. Precomputed waveform peaks are tiny (a few
  hundred numbers per sketch) and wavesurfer.js v7's regions plugin gives a
  draggable, resizable selection over a waveform, with a documented
  pre-decoded-peaks path for exactly this case [wavesurfer]. Optional; the
  slider alone is fine to start.

**Cost/effort.** $0, no infra, roughly a day. Works on every device.
**What it cannot do:** produce a file. Nothing to post as media.

---

## 3. Tier 1: cut in the browser

The page fetches the byte range it needs from our copy of the video, decodes,
re-encodes the clip, and hands the visitor a file. No server.

### 3.1 Source storage: Cloudflare R2

$0.015/GB-month standard, **10 GB free**, **zero egress** [R2]. 720p corpus:
~9 GB over the free tier, so ~$0.14/month. 360p: free. The bucket needs a CORS
rule allowing `https://karginhaghordum.am` and exposing `Content-Range`. Files
should be remuxed with `-movflags +faststart` at ingest so the index sits at
the front and range reads are cheap.

Why R2 and not the alternatives: egress is the whole cost of serving video and
R2's is $0. Backblaze B2 is comparable on storage but charges egress past a
free allowance; S3 charges egress from byte one. The project already runs a
Cloudflare Worker (`LOG_ENDPOINT`), so the account exists.

### 3.2 Library A (recommended): Mediabunny

Pure-TypeScript media toolkit: demuxers and muxers for MP4/WebM/etc. wired to
WebCodecs. Zero dependencies, tree-shakes to ~5 kB gzipped for small uses,
MPL-2.0 (closed-source commercial use explicitly allowed) [MB-readme].
Maintenance, checked via `gh` on 2026-08-29: **v1.55.3 released 2026-08-26,
last commit 2026-08-28, 7,052 stars, 49 open issues**. Sponsors include
Remotion and Mux, which is a decent signal it is the layer other video products
now build on.

What it gives us:

- `UrlSource` reads a remote file by HTTP range requests with prefetching
  (2 parallel workers, 8 MiB cache by default) [MB-url]. A 30 s clip pulls
  roughly 5 MB, not the whole 27 MB file.
- `Conversion.init({input, output, trim: {start, end}})` then `execute()`
  produces the clip [MB-trim].
- **Important:** the docs state that "trimming with a non-default start value
  currently forces a full transcode of both video and audio streams"
  [MB-trim]. So a trim is decode + encode, not a packet copy. That is fine for
  clips (short) and it is what gives frame-accurate cuts, but it means
  WebCodecs is required, which is the capability matrix in 1.5.
- Output MP4 with H.264 + AAC where the browser can encode them, `WebM`
  VP9 + Opus as fallback; `getFirstEncodableVideoCodec()` /
  `getFirstEncodableAudioCodec()` exist for exactly that decision [MB-codecs].
- `CanvasSource` lets you draw the frames yourself during conversion, which is
  the door to burning the Armenian line or a site watermark into the clip
  client-side. Not researched further; noting it exists.

Expected speed: hardware encode of 750 frames at 720p is a few seconds on a
laptop, longer on a phone. Not measured.

### 3.3 Library B (not recommended): ffmpeg.wasm

Real FFmpeg compiled to WebAssembly. MIT, 17.8k stars, but: **last release
v0.12.15 on 2025-01-07, last commit 2025-09-17, 422 open issues** (`gh`,
2026-08-29). The core is a ~31 MB download before the first cut [ffmpeg-size];
the single-thread build works without COOP/COEP headers, the multi-thread one
needs them (so `coi-serviceworker` on GitHub Pages) and is ~2x faster
[ffmpeg-32blog]; there is a 2 GB memory ceiling and the input has to be copied
into its virtual filesystem, so range-reading a remote file is not natural.
Encoding is software x264 in wasm: tens of seconds for a short 720p clip. Its
one real advantage is that it runs on any browser with WebAssembly, including
Firefox Android. Verdict: a possible fallback for non-WebCodecs browsers, not
the main path, and the project looks dormant.

### 3.4 Full editors (wrong tool)

Checked in case a ready-made editor was the shortcut:

- **omniclip** (MIT, 1.5k stars, web components, WebCodecs, installable via npm
  and embeddable) [omniclip]
- **openvideodev/video-editor** (PixiJS + WebCodecs engine, Next.js 15, 50
  stars, free for individuals and orgs up to 3 people, commercial license above)
  [openvideo]
- **designcombo/react-video-editor** built on Remotion [rve]. Remotion itself is
  free for individuals and companies up to 3 employees, $100/month minimum for
  "automators" above that, and is a programmatic-video renderer, not a trimmer
  [Remotion-license].

All three are multi-track compositing timelines (drag media, layers,
transitions). We need two handles and a download button. Pulling in a full
editor for that would add a large bundle to a site whose payload is already
2,270 KB and put a licensing question on the table for no gain.

### 3.5 Tier 1 shape

```
watch page
  YouTube iframe (IFrame API)  <- preview, in/out picking (Tier 0 UI)
  [Cut clip]  -> lazy-load mediabunny chunk (only on click)
              -> UrlSource(https://<r2>/720/<id>.mp4)   range reads
              -> Conversion trim -> BufferTarget
              -> Blob URL -> <a download> and a <video> preview
              -> if !WebCodecs: show "your browser cannot cut clips; here is
                 the timestamp link instead" (Tier 0 never fails)
```

Effort: 2-4 days on the web side plus the one-time ingest (yt-dlp update, 702
downloads at ~19 GB, faststart remux, R2 upload with CORS). Optional GIF
output: decode with Mediabunny, encode with `gifenc` (fast JS, last published
five years ago) or `gifski-wasm` (higher quality, multithreaded)
[gifenc][gifski].

---

## 4. Tier 2: cut on a server

Same source store on R2; the cut happens off-device. Buys universal browser
support and frame-exact cuts for everyone, at the cost of running something.

### 4a. Cloudflare Worker + Mediabunny low-level API (no container, no ffmpeg)

Mediabunny runs in any ES2021 environment and has a `@mediabunny/server`
package for Node/Bun/Deno [MB-readme]. Its low-level API can copy encoded
packets without decoding: `EncodedPacketSink.getKeyPacket(t)`, iterate with
`getNextPacket`, feed an `EncodedVideoPacketSource` into an `Mp4OutputFormat`
[MB-lowlevel]. That is a packet copy, no WebCodecs needed, so it should fit a
Worker: Workers Paid allows 30 s CPU per request (configurable to 5 min),
128 MB memory, and network waits do not count as CPU [Workers-limits].

The catch is 1.3: packet copy is keyframe-aligned, so with the sources as
downloaded the cut is up to ~7 s off. To make this work the ingest step would
re-encode all 702 videos once with dense keyframes (a 1 s or 0.5 s GOP,
costing maybe 10-20% bitrate), after which every cut is a fast byte copy that
starts within a second of the chosen point. That is a bigger ingest job (a
full re-encode of 34 hours on this laptop is many hours of CPU; a Colab or
runpod box is the sane place for it) and it locks the store into that
conditioning.

Unverified: Mediabunny inside the Workers runtime specifically (it targets
browsers and Node-likes). Needs a one-hour spike before it is counted on.

### 4b. Cloudflare Containers running real ffmpeg

Frame-exact: `ffmpeg -ss <in> -to <out> -i <src> -c:v libx264 -preset veryfast
...` on a short clip, or stream-copy with a re-encoded head. Native binaries and
filesystem are supported. Pricing is per 10 ms of active time inside the
$5/month Workers Paid plan, which includes 375 vCPU-minutes, 25 GiB-hours of
memory and 200 GB-hours of disk; a `standard-1` instance is 1/2 vCPU with
4 GiB [CF-containers]. Egress after 1 TB is $0.025/GB. A 30 s 720p re-encode is
on the order of 10-20 vCPU-seconds, so the included allowance covers on the
order of a thousand clips a month before overage (estimate, not measured).

Real-world gotchas from someone who shipped exactly this (Kent C. Dodds moved
podcast ffmpeg jobs to Containers + Queues + R2): the `sleepAfter` timeout
killed long jobs and wasted idle time, fixed with heartbeat pings; the worker
must return `202 Accepted` and let the container call back rather than block;
he explicitly wishes the heartbeat dance were built in [Kent]. A dedicated
Fly.io machine was his $31/month comparison point.

Effort: container image, a Durable Object to supervise it, a request/poll or
callback flow, and a place to put finished clips (R2 again, with a lifecycle
rule to expire them).

### 4c. Cloudflare Stream (fully managed)

Upload the 702 videos to Stream; it transcodes and serves them. It has a
clipping API: `POST /accounts/<id>/stream/clip` with `clippedFromVideoUID`,
`startTimeSeconds`, `endTimeSeconds`; the clip becomes a new video that goes
Queued then Ready, with webhooks [Stream-clip]. MP4 downloads are enabled per
video via `/downloads` and polled until `ready` [Stream-dl].

Pricing: **$5 per 1,000 minutes stored per month** and **$1 per 1,000 minutes
delivered**, no egress or encoding fees [Stream-price]. The corpus is 2,034
minutes, so ~$10.20/month before any clips. Every clip is a new stored video
(and the docs warn clips do not inherit `scheduledDeletion`, so they accumulate
unless deleted), and every MP4 download bills the clip's minutes.

Cleanest to build (it is three API calls), most expensive to run, and each
clip goes through Stream's transcode queue rather than returning instantly.
It also replaces the YouTube embed with Stream's player, which is a bigger
change to the site than the feature asks for.

### 4d. Modal (or Fly.io / a VPS)

Modal is Python-native: define an image with ffmpeg, expose a web endpoint,
scale to zero. The Starter plan carries **$30/month of free compute credit**
[Modal]. Given this project is Python end to end, it is the lowest-friction
server option to prototype. Third-party writeups mention regional pricing
multipliers; not verified against Modal's own page, so treat costs beyond the
free credit as unknown. Fly.io is the "always-on small machine" alternative at
roughly $31/month minimum per [Kent].

---

## 5. Side-by-side

| | Precision | Browsers | Monthly cost | Per-clip cost | Build | Locks in |
|---|---|---|---|---|---|---|
| 0 Timestamp share | exact | all | $0 | $0 | ~1 day | nothing |
| 1 Mediabunny + R2 | frame-exact | WebCodecs only | ~$0.15 | $0 | 2-4 days + ingest | source store |
| 1b ffmpeg.wasm | frame-exact | all with wasm | ~$0.15 | $0, but 31 MB + slow | 2-4 days + ingest | dormant dep |
| 2a Worker + packet copy | ~1 s (after re-encode ingest) | all | $5 | ~$0 | 3-5 days + heavy ingest | re-encoded store |
| 2b Containers + ffmpeg | frame-exact | all | $5 + overage | fractions of a cent | 1-2 weeks | container plumbing |
| 2c Stream | frame-exact | all | ~$10-12 + growth | ~$0.001 + storage of the clip | 2-3 days | player swap, vendor |
| 2d Modal | frame-exact | all | $0 up to credit | unknown past credit | 2-4 days | little |

---

## 6. Recommendation and what would flip it

**Do Tier 0 now, unconditionally.** It is the in/out picker every other tier
needs, it is free, and it already beats what YouTube offers since April.

**For files, pick Tier 1: Mediabunny over R2.** Static site stays static,
cost is pennies, cuts are frame-exact and hardware-fast, the dependency is the
healthiest in the field, and the failure mode on an unsupported browser is a
graceful fall back to the Tier 0 link.

What would make me pick differently:

- **Analytics show a big non-WebCodecs share** (Firefox Android, Safari < 26):
  go to 2b Containers or 2d Modal so every visitor gets a file.
- **Firefox desktop users matter and MP4 specifically matters** (the H.264
  encode bug): same answer, or accept WebM for them.
- **You want burned-in Armenian subtitles on every clip and do not want to
  hand-roll canvas compositing**: ffmpeg's subtitle filters on a server (2b/2d)
  are the mature path.
- **You would rather pay ~$12/month than think about browsers at all**: 2c
  Stream. It is the least code.
- **Zero appetite for a 20 GB ingest**: stay at Tier 0. It is still a good
  feature.

**Hard to reverse:** the source store. Decide 720p vs 360p (720p; the 128
SD-only videos come as 360p anyway), do faststart at ingest, keep the original
GOP unless committing to 2a. Also decide a clip length cap (60 s is a natural
one; it bounds compute, bandwidth and misuse for every tier).

---

## 7. Open questions for the owner

1. Who is this for and on what device: a share-to-WhatsApp/Telegram file, a
   GIF, or a link? That decides Tier 1 vs 2 more than anything technical.
2. Is there user-agent data in the `LOG_ENDPOINT` logs? That answers 1.5.
3. Max clip length? Any clip length cap simplifies every cost estimate above.
4. Should the site's curated line or transcript be burnable into the clip as
   a subtitle? If yes, that pushes toward a server (or a canvas spike in
   Mediabunny).
5. Is 720p enough? Nothing in the corpus is above 720p on YouTube
   (`definition` is `hd` or `sd`; no 1080p rendition appeared for the probe).

---

## 8. Gotchas collected, so nobody rediscovers them

- Mediabunny: trim with non-zero start = full transcode; plan on WebCodecs.
- Mediabunny: AAC encode is missing in Firefox and on desktop Linux; register
  `@mediabunny/aac-encoder` only when `canEncodeAudio('aac')` is false.
- Firefox 145: H.264 `VideoEncoder.configure()` fails despite
  `isConfigSupported` saying yes. Fall back to VP9/WebM or detect and route to
  Tier 0.
- ffmpeg.wasm: ~31 MB core, single-thread build needs no headers, multi-thread
  needs COOP/COEP (service-worker hack on GitHub Pages), 2 GB memory ceiling,
  no release since 2025-01.
- YouTube IFrame API: `seekTo()` cancels a previously set `endSeconds`;
  re-apply the bounds after every seek.
- yt-dlp 2026.03.17 with no JS runtime got a 403 on a 720p DASH stream today;
  the ingest needs a newer yt-dlp plus deno.
- Keyframe spacing on the 360p muxed stream: median 2.8 s, max 7.0 s. Stream
  copy is not a cut.
- GitHub Pages: 1 GB site, 100 GB/month soft bandwidth. No video bytes there.
- Cloudflare Stream: clips are new stored videos, do not inherit
  `scheduledDeletion`, and MP4 downloads bill delivered minutes.
- Cloudflare Containers: `sleepAfter` will kill a running job unless the job
  heartbeats; return 202 and call back rather than holding the request.

---

## Sources

- [GH-limits] https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- [COI] https://github.com/gzuidhof/coi-serviceworker and https://blog.tomayac.com/2025/03/08/setting-coop-coep-headers-on-static-hosting-like-github-pages/
- [YT-clips-9to5] https://9to5google.com/2026/04/17/youtube-clips-share-at-time-changes/
- [YT-clips-ppc] https://ppc.land/youtube-kills-clips-and-bets-on-timestamp-sharing-in-2026/
- [Kapwing] https://www.kapwing.com/tools/trim/youtube
- [Cutters] https://appsgolem.com/en/blog/best-youtube-video-cutter-2026/
- [YT-iframe] https://developers.google.com/youtube/iframe_api_reference
- [wavesurfer] https://wavesurfer.xyz/plugins/regions and https://github.com/katspaugh/wavesurfer.js/
- [WebCodecs-support] https://www.testmuai.com/learning-hub/webcodecs-browser-support/ and https://www.digitalsamba.com/blog/webcodecs-api-explained
- [caniuse-webcodecs] https://caniuse.com/webcodecs
- [WebCodecs-firefox-h264] https://webcodecsfundamentals.org/codecs/avc1.420429.html and https://webcodecsfundamentals.org/datasets/codec-analysis-2026/
- [R2] https://developers.cloudflare.com/r2/pricing/ (numbers cross-checked via https://egresscost.com/cloudflare/ and https://www.budgetforge.dev/tools/cloudflare-r2-pricing-2026)
- [MB-readme] https://github.com/Vanilagy/mediabunny and https://mediabunny.dev/
- [MB-trim] https://mediabunny.dev/guide/converting-media-files (Trimming section)
- [MB-url] https://mediabunny.dev/guide/reading-media-files (UrlSource)
- [MB-aac] https://mediabunny.dev/guide/extensions/aac-encoder
- [MB-codecs] https://mediabunny.dev/guide/supported-formats-and-codecs
- [MB-lowlevel] https://mediabunny.dev/guide/quick-start (EncodedPacketSink) and https://mediabunny.dev/guide/media-sources (EncodedVideoPacketSource)
- [ffmpeg-size] https://tarkarn.com/blog/ffmpeg-wasm-browser-guide and https://ffmpegwasm.netlify.app/docs/faq/
- [ffmpeg-32blog] https://32blog.com/en/ffmpeg/ffmpeg-wasm-browser-video
- [omniclip] https://github.com/omni-media/omniclip
- [openvideo] https://github.com/openvideodev/video-editor
- [rve] https://github.com/designcombo/react-video-editor
- [Remotion-license] https://www.remotion.dev/docs/license/faq and https://www.remotion.pro/license
- [gifenc] https://github.com/mattdesl/gifenc
- [gifski] https://github.com/jamsinclair/gifski-wasm
- [Workers-limits] https://developers.cloudflare.com/workers/platform/limits/
- [CF-containers] https://developers.cloudflare.com/containers/pricing/
- [Kent] https://kentcdodds.com/blog/offloading-ffmpeg-with-cloudflare
- [Stream-clip] https://developers.cloudflare.com/stream/edit-videos/video-clipping/
- [Stream-dl] https://developers.cloudflare.com/stream/viewing-videos/download-videos/
- [Stream-price] https://developers.cloudflare.com/stream/pricing/
- [Modal] https://blaxel.ai/blog/modal-pricing-alternatives-guide and https://www.buildmvpfast.com/tools/api-pricing-estimator/modal

Release dates, star and issue counts for ffmpeg.wasm and Mediabunny were read
with `gh api` on 2026-08-29. Corpus, format and keyframe numbers were measured
locally the same day.
