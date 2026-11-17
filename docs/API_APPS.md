# Building an app that calls an API

Everything here was measured against the live services from the place your app
actually runs. Where a number appears, it is a reading rather than an estimate.

An app that calls an API is the most useful kind you can build here, and the
one with the most ways to go quietly wrong. Those ways are not the ones people
expect: almost none of the trouble is the request itself.

---

## The budget you are spending

| | |
|---|---|
| Your app is killed after | **20 seconds** |
| Pippa stops waiting after | **20 seconds** |
| Memory | 512 MB |
| Package size | 3 MB |
| Available to import | Python 3.12 standard library, `pippa_agentapp_sdk`, `PyYAML` |

Those two twenty-second limits are the same number, which means an app that
uses its whole budget is racing the thing that called it. Aim for a few
seconds. You have far more room than you think:

```
measured from a Lambda, cold start then warm, November 2026
  nominatim.search       108ms /  7ms      openmeteo.geocode     97ms / 94ms
  nominatim.reverse      126ms /  6ms      openmeteo.forecast    75ms / 71ms
  wikipedia.summary       26ms / 27ms      postcodes.io          24ms / 22ms
  wikimedia.pageviews    109ms / 26ms      police.crimes        103ms / 99ms
  api.nasa.gov           743ms / 673ms     carbonintensity      177ms /180ms
```

A three-call chain to Nominatim costs **342ms cold**. The budget is not your
problem. What follows is.

> **Do not time an API from your laptop.** The same calls above took **10 to 30
> seconds** measured from a developer machine, every time, on the first request
> to each host — a slow resolver at that desk, nothing to do with the API. If
> you conclude "this API is too slow for a 20s budget" from a laptop reading,
> you will throw away a perfectly good idea.

---

## Put the network behind one method

One method does the HTTP. Everything else calls it. This is not tidiness: it
is the only thing that makes the failure modes testable, and the failure modes
are most of the work.

```python
def _fetch(self, url: str, timeout: float = 6.0) -> bytes:
    """Every outbound request goes through here."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()
```

In a test, replace it on the instance — so the stub takes no `self`:

```python
app = App()
app._fetch = lambda url, timeout=6.0: SAMPLE_RESPONSE
```

**`urlopen` has no default timeout.** Without one, a single unresponsive host
holds your app until it is killed, and the user is told it failed with nothing
to show.

---

## The failure you will actually hit

Not a timeout. **A successful response that contains nothing.**

Every one of these is a real, verified behaviour of an API in `IDEAS.md`:

| You asked for | What you get | What a naive app does |
|---|---|---|
| a place that does not exist (Nominatim) | **`200` with `[]`** | `results[0]` → `IndexError`, "the app broke" |
| a place that does not exist (Open-Meteo geocoding) | **`200` with no `results` key at all** | `data["results"]` → `KeyError` |
| this month's crime (data.police.uk) | **`200` with `[]`** — the data lags a month | "no crime was reported here", which is false |
| an article with no views (Wikimedia) | **`404`**, not an empty series | "the service is down", which is also false |
| a topic with no article (Wikipedia) | **`404`** | same |

So: **check for emptiness before you index**, and when a source publishes
late, say which period you actually used. An answer about August presented as
an answer about November is worse than no answer, because nothing looks wrong.

---

## Two APIs refuse you without a User-Agent

Verified: **Nominatim** and **Wikipedia/Wikimedia** both return **`403`** to a
request with no `User-Agent`. Python's `urlopen` does not send a useful one.

```python
USER_AGENT = "pippa-agent-app-<yourapp>/0.1 (https://github.com/Pippa-Labs)"
```

Send it on every request to those hosts. It costs one line and it is the
difference between an app that works and an app that 403s on its first call in
production having passed every test you stubbed.

---

## Rate limits are a design input, not an error case

- **Nominatim** asks for about **one request per second**. If your app makes
  three calls, that is three seconds of deliberate waiting, and it is fine —
  you have twenty. Space them on purpose and write down why, or somebody
  removes the `sleep` as dead weight.
- **NASA `DEMO_KEY`** allows **30 requests an hour and 50 a day, per IP** —
  and your app shares an IP with everything else running there. A `429` is an
  ordinary Tuesday, not an edge case.

Handle `429` as *retryable*, with a message that says to try shortly. Do **not**
retry inside the call: you have one budget and the user is waiting.

---

## Catch `HTTPError` before `URLError`

`urlopen` raises `HTTPError` for any non-2xx, and `HTTPError` is a **subclass**
of `URLError`. Get the order wrong and a `404` is reported as "the service is
unreachable, try again" — a wrong message, marked retryable, about a request
that will never succeed.

```python
try:
    raw = self._fetch(url)
except urllib.error.HTTPError as exc:        # MUST be first
    if exc.code == 404:
        raise PlaceNotFound(f"no such place: {place!r}")
    if exc.code == 429:
        raise ServiceBusy(f"rate limited: {exc.code}")
    raise ServiceUnavailable(f"upstream returned {exc.code}")
except (urllib.error.URLError, TimeoutError, OSError) as exc:
    raise ServiceUnavailable(f"could not reach the api: {exc}")
```

Then give each error a `user_message` that names the thing:

```python
error = PlaceNotFound(f"nominatim returned no match for {place!r}")
error.user_message = f"I could not find anywhere called {place}."
raise error
```

"I could not find anywhere called Narnia" tells somebody what to retype.
"Something went wrong" does not.

---

## Using API keys

**Prefer an API that needs no key.** Almost every idea in `IDEAS.md` uses
one, and it is one less thing to go wrong. When the idea needs a key, the key
never goes in a file in this repository: Pippa keeps it for you, and hands it
to your app on each call.

**This repository is public**, so this matters more here than anywhere: a key
in any file, even for one commit, is a key anyone can copy, for good. With
`app_secrets` the key never comes near the repository.

### 1. Declare it in `manifest.yaml`

By name, with one sentence saying what it is for. Never the value.

```yaml
app_secrets:
  - name: OPENWEATHER_API_KEY
    description: "OpenWeather key, used to look up the forecast"
    required: true          # true unless the app can answer without it
```

The rules, which the check and Pippa both apply:

- The name is capital letters, digits and underscores, 3 to 64 characters,
  starting with a letter. It may not start with `PIPPA_`, `AWS_`, `LAMBDA_` or
  `OTEL_`, and may not be a name the system uses (`PATH`, `HOME`, `TZ`, ...).
- `description` is required, at most 200 characters. Reviewers and your Keys
  page show it.
- `scope` is `app` (the default; you may leave it out). One key per app,
  shared by every call. Keys that each user brings are not available yet.
- At most 20 keys per app, each value at most 4 KB.
- It is `app_secrets:`, not `secrets:`. A `secrets:` block asks a *user* for
  their credentials, and registration refuses it.

### 2. Read it inside `handle()`

```python
import os
import urllib.parse

from pippa_agentapp_sdk import AgentAppError, Call, Result


class KeyMissing(AgentAppError):
    """The app's API key is not set, so it cannot call the service."""

    user_message = "This app isn't set up yet: its builder still has to add its API key."
    retryable = False


class App:
    ...

    def handle(self, call: Call) -> Result:
        # Here, not at the top of the file: Pippa puts the key in os.environ
        # for each call, and it is not there while the module is imported.
        key = os.environ.get("OPENWEATHER_API_KEY", "")
        if not key:
            raise KeyMissing(
                "OPENWEATHER_API_KEY is not set: put it in .env on your computer, "
                "or under Keys on the app's card in Pippa"
            )
        place = call.inputs.get("place", "")
        # The address is written here, in full: the question's words only ever
        # go into the query's values, so nobody can choose where the key goes.
        query = urllib.parse.urlencode({"q": place, "appid": key, "units": "metric"})
        # Never put the key, this URL or the provider's error text in an error
        # message, a narrative or a print(): Pippa hides an exact copy of the
        # key, not every form of it ("Keep the key between your app and the
        # provider", below).
        raw = self._fetch("https://api.openweathermap.org/data/2.5/weather?" + query)
        ...
```

And test both cases. `monkeypatch` sets or removes the key for one test only,
and the fake value is obviously fake:

```python
def test_a_missing_key_is_said_plainly(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    with pytest.raises(KeyMissing):
        call({"place": "Leeds"})


def test_the_forecast_is_read(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key-000000000000000000")
    ...
```

### 3. Set the value in Pippa

**Only the app's owner can do this:** the Pippa account this repository was
created for. Signed in as anybody else (a tester, a reviewer, another of your
accounts) there is no **Keys** section, and nobody who uses the app is ever
asked for your key. Until the owner has saved a value, the app has no key, and
Pippa does not call it while the key is `required` ("If a key is missing",
below).

Push the version that declares the key first: it publishes without the value.
Then open **https://app.getpippa.ai**, **Apps**, **Created by me**, your app's
card, **Keys**. A key is listed there once a published version declares it.
Press **Add**, paste the value and save. Pippa stores it encrypted, never
shows it again (only its last four characters, for a key of 16 characters or
more), and never writes it to GitHub, the build or its own logs.

- **Rotate any time, without a push.** Save a new value and the very next
  call uses it, on every version of the app that declares it: drafts, the
  version testers have and the approved one. Deleting it works the same way.
- **The keys belong to the app's owner and its repository, not to its
  code.** Every key is deleted when Pippa Labs moves the app, or re-links
  its repository, to another Pippa account, and when the repository is
  renamed: the app id changes with the name, so the old id's keys are
  deleted and the new id starts with none. The owner then adds them again.
  A version published before the change gets no keys: Pippa does not run
  it, and the person asking is told *"This version was published before the
  app changed hands; its builder must publish again."* The owner pushes a
  version of their own, and that is the one people should have.
- **Pippa limits how often an app can be called**, so nobody can spend your
  key's quota without end. By default each Pippa agent (the assistant behind
  one Pippa account) can call an app 20 times a minute and 300 times a day,
  and the app takes at most 120 calls a minute and 3,000 a day from everybody
  together, you included; Pippa Labs can set different limits for one app.
  The first limit is per agent, not per person: somebody with several Pippa
  agents gets a share for each, up to the app's own limit. Over a limit
  Pippa does not call the app, and the person is told *"This app has had a
  lot of requests in the last minute; try again in a minute."* or *"This app
  has had a lot of requests today; try again tomorrow."* A call Pippa does
  not run (over a limit, with a key missing, or for any other reason here)
  is not counted.
- Even so, every person who uses your app spends that key's quota. Pick a key
  whose free tier you are happy to share, and set a spending cap with the
  provider if it offers one.

### 4. On your computer: `.env`

Nothing in this template runs on your computer (the build runs the checks
and the tests), so you rarely need one. If you do run the app here, you make
`.env` yourself, once, in the repository's folder, and type the values in. It
replaces a `.env` that is already there, so only when you have none:

```
cp .env.example .env        # macOS, Linux or Git Bash
copy .env.example .env      # Windows
```

Claude gives you that command and never runs it, and never needs to see the
values. `.claude/settings.json` stops Claude Code's file tools reading,
writing or creating `.env` and its copies (any other `.env.*` file but
`.env.example`, `.env~`, `.env - Copy`, `.env-*`, `.env_*`, `.envrc`), and
`CLAUDE.md` tells Claude never to open or make it from the shell either,
which no setting can fully stop.

`.gitignore` keeps `.env` out of every commit; `.env.example`, which is
committed, lists the same names with no values. Never put a value anywhere
else: this repository is public.

### If a key is missing

- **Publishing still works.** A push never fails only because a key has no
  value yet; the commit comment says *"Published, but it can't run until you
  add OPENWEATHER_API_KEY in Created by me."*
- **Pippa does not call the app** while a `required: true` key is missing. The
  person asking sees *"This app isn't ready yet: its builder still has to add
  OPENWEATHER_API_KEY."*
- **Nobody else can install it, and it cannot be submitted for review,** until
  every required key is set.
- A key declared `required: false` is simply absent from `os.environ`: your
  code decides what to do without it.
- **If Pippa cannot read the keys** (a fault on Pippa's side), it does not
  call the app either, and the person is told *"This app can't run right now.
  Try again in a little while."* Nothing in the app causes it, and no push
  fixes it.
- **If Pippa cannot count the calls** (also a fault on Pippa's side), it does
  not call an app that has a key set, so that nobody spends your key
  uncounted, and the person is told *"This app can't run right now because
  Pippa can't count its requests. Try again in a little while."* An app with
  no key set runs as usual. Again, no push fixes it.

### Keep the key between your app and the provider

While your app runs, its code is the one thing that holds the key. Pippa
cannot see what the code does with it, so these four are up to you:

1. **Never let the question choose where the key is sent.** Write the
   provider's address into the code, in full. Nothing from the question, or
   from any other input, may decide the host, the URL, a redirect to follow
   or the header the key goes in. The question's words go only into the
   values of the query (`urlencode`) or into one quoted path segment
   (`quote(..., safe="")`) after that fixed address. An app that fetches an
   address the person typed must never send the key with it.

   A key that goes in a header must not follow a redirect either. Python's
   `urllib` sends every header given to `Request(headers=...)` or
   `add_header()` on to whatever address a redirect names, another host
   included, and `Authorization` with them. Attach the key with
   `add_unredirected_header`, which stays with the first request only:

   ```python
   def _fetch(self, url: str, key: str, timeout: float = 6.0) -> bytes:
       request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
       # Never in headers= or add_header(): those follow a redirect anywhere.
       request.add_unredirected_header("Authorization", f"Bearer {key}")
       with urllib.request.urlopen(request, timeout=timeout) as response:
           return response.read()
   ```

   Or refuse redirects outright, so that a `3xx` is an error like any other.
   It arrives as an `HTTPError` with the status in `.code`, which the
   `except` in "Catch `HTTPError` before `URLError`" already handles:

   ```python
   class _NoRedirect(urllib.request.HTTPRedirectHandler):
       def redirect_request(self, req, fp, code, msg, headers, newurl):
           return None  # the opener raises HTTPError instead of following it

   _OPENER = urllib.request.build_opener(_NoRedirect)
   # In _fetch: with _OPENER.open(request, timeout=timeout) as response:
   ```

2. **Never give a model or a tool a way to read the environment.** If your app
   asks a language model for anything, give it no tool that can read
   `os.environ` or a file, run code, or fetch an address it chooses, and never
   put the key in a prompt. A model can be talked into repeating whatever it
   can reach.
3. **Never return, print or log a key, in any form.** Pippa hides an exact
   copy of a key, and its URL-encoded copy, in what your app returns (`data`,
   the `narrative`, `warnings`, error messages) and in what it prints. It
   does not recognise the key in any other form: base64 (as in a `Basic`
   sign-in header), split in two, reversed, in lower-case `%xx`, JSON-escaped
   or only its first part. Those reach the person asking, word for word.
4. **Never pass on a provider's error.** Some services repeat the request in
   their error messages and response bodies, the URL with your key in it, or
   the key itself, sometimes encoded. Never put a provider's error text, its
   response body or the request URL in a `user_message`, `narrative`, `data`,
   `warnings` or a log line. Say what happened in your own words, from the
   status code, as in "Catch `HTTPError` before `URLError`", above.

### Never commit a key

The commit check (`.githooks/pre-commit`), `scripts/check.py` and the build
all look for keys in your files and stop the commit or the publish, naming the
file and line but never the value. A line that only looks like a key, such as
a made-up test value, can end with `# pragma: allowlist secret`. That comment
never lets through a key in a provider's own format (AWS, GitHub, OpenAI,
Slack and so on) or a private key: no test needs a real one. `.env.example`
is checked too, commented lines included, because it is committed.

**If a key was ever committed and pushed, rotate it with the provider first**
(make a new one, delete the old one), then set the new one under Keys.
Deleting it from the code is not enough: it stays in the git history, where
anyone who can read the repository can find it.

A provider's public demo key is the one exception: NASA's `DEMO_KEY` belongs
to nobody, is in their own documentation, and may sit in the code as a named
constant with a comment saying so. Its limits are tight (above): 30 requests
an hour per IP, shared. Tested against `api.nasa.gov`:

| | |
|---|---|
| key missing | `403` `{"error": {"code": "API_KEY_MISSING"}}` |
| key wrong | `403` `{"error": {"code": "API_KEY_INVALID"}}` |
| over the limit | `429` |

Three different causes behind one status code. Read the body, not just the
status, and say which one happened.

---

## Do not return everything you were given

One month of street-level crime for central London is **1.25 MB and 3,245
items**. Returning that is three separate mistakes: it blows the result size,
it takes a long time to render, and nobody asked for 3,245 crimes.

Aggregate. Return the total, the top few categories with counts, and the
period you measured. The shape of a good answer is a handful of numbers a
person can read aloud.

---

## Checklist before you push

The build runs `scripts/check.py`, the tests and `scripts/routing_check.py` on
every push; they need the Pippa SDK, which is not in this repository, so
nothing runs locally. Routing findings come back under **Warnings** in the
commit comment only once the app is live, so check `manifest.yaml` against
`scripts/routing_check.py` by reading it before pushing.

And in your tests, with the network stubbed:

- [ ] the happy path, against a payload you captured from the real API
- [ ] empty result — `[]`, a missing key, no items
- [ ] `404`, `403`, `429`
- [ ] a timeout: have the stub raise `TimeoutError`
- [ ] bad user input — a place that is not a place
- [ ] each one raises **your** error subclass with a `user_message`

Call the real API once, by hand, before you trust your parsing. Then delete
that script. A test that reaches the network fails on a train, and its
expected numbers change tomorrow.

---

## Follow-ups: the words still decide

A follow-up like *"and last week?"* is answered by whichever app answered the
turn before it — that is how it is meant to work, and Pippa is given the
transcript to make it possible.

It is not reliable when the follow-up's own words belong to a different
installed app. Measured live, same question, same app, ten runs each:

| Follow-up after an app answered | Reached the right app |
|---|---|
| "and in metres" (after a unit conversion) | **every time** |
| "and over 30 years" (after a loan figure) | **every time** |
| "what about the month before" (after a crime figure) | 2 in 3 |
| **"and last week?"** (after a Wikipedia figure) | **1 in 3** — and it reached *Pippa Diary* twice |

"last week" is Pippa Diary's vocabulary. The transcript pulls one way, the
words pull the other, and the words often win.

**What to do about it.** You cannot stop a user typing "and last week?", and
you should not try. But you can make the first answer carry the subject
forward, so the follow-up is less bare:

> *"The ISS drew 66,222 Wikipedia views over the 30 days to 1 November."*

followed by *"and last week?"* is a much weaker signal than:

> *"**Wikipedia views for the ISS**: 66,222 over the 30 days to 1 November."*

Name your subject in the `narrative` — not just the number. It is the only
part of the previous turn the next one can lean on.

And when you write your own follow-up test prompts, write the realistic ones
rather than the convenient ones. A follow-up that happens to contain your own
app's vocabulary proves very little; the one that contains somebody else's is
the test.

