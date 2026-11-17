# Troubleshooting

Every heading on this page is text you will really see. If something has gone
wrong, search this page for a distinctive line from the message.

## Start here

**Tell Claude.** That is the fix for nearly everything below.

Claude Code wrote your app and pushed it. It can read the build log, correct
the file and push again. You do not have to work out which entry applies.

> The last push failed. Please read the build log and fix it.

**You never run anything yourself.** There is no Python to install, no virtual
environment, and no command to type. Pushing to `main` is the deploy. The
**build** — GitHub Actions, the automatic job that runs on every push — installs
Python, checks the app, runs the tests and publishes it. Every error on this
page comes either from that build, or from Pippa once the app is live.

### Where the build log is

1. Open your repository on GitHub.
2. Click the **Actions** tab.
3. Click the newest run, named after your last commit.
4. Click the step with a red cross. The failure is at the bottom of its log.

Copy the address of that page. Giving Claude or an organiser the link beats
describing what you saw.

A green tick means the app published, unless the run's summary says **Nothing
to publish yet**: see [that entry](#nothing-to-publish-yet). A red cross means
nothing was published: every version you published before is untouched, and
goes on working exactly as it did.

---

# The app id and the author name

This is the most common reason a first deploy fails, so it is first.

## `Nothing to publish yet`

**Symptom.** The run on the **Actions** tab has a green tick, but the commit
has no `pippa/publish` status and no comment. Open the run, and its summary
says **Nothing to publish yet**, with one of two reasons:

```
manifest.yaml still has the placeholder app id hack.your_app_name_here. The next push with a real app id publishes.
```

```
Nothing to publish yet: choose your public author name (app_author_name in manifest.yaml). Claude will ask you for it.
```

**What it means.** The repository is not an app yet: `manifest.yaml` still
has one of the two blanks the template ships with, so the build skips the
push. It checks nothing and publishes nothing, and nothing is wrong with
Pippa.

- **The app id.** A new repository fills it in by itself, from its name,
  within a minute of being created: a commit from **github-actions[bot]**
  called *Set app.id from the repository name*. If yours has no such commit,
  the next entry says how to set the id by hand.
- **The author name.** `app_author_name` at the top of `manifest.yaml` is
  still `""`. It is the public name shown with your app, as "by <name>", and
  only you can choose it: a pseudonym, never your real name or your email
  address.

**The fix.** Tell Claude:

> The build says there is nothing to publish yet. Please do the first steps
> in CLAUDE.md and push again.

## `FAIL manifest.yaml declares 'hack.tides', but this repository publishes 'hack.tide_times'`

```
 FAIL manifest.yaml declares 'hack.tides', but this repository publishes 'hack.tide_times'
       Change `app.id` in manifest.yaml to: hack.tide_times
```

**What it means.** The app id in `manifest.yaml` is not the one this
repository publishes. An app id is not something you pick, so the build
refuses any other, however good it looks.

Your app id is decided by the name of your repository. Pippa works it out from
the repository the push came from, and your `manifest.yaml` has to agree.

The rule: take the repository name, drop the `pippa-hack-` prefix, turn every
hyphen into an underscore, and put `hack.` on the front.

| Repository | App id |
|---|---|
| `pippa-hack-tide-times` | `hack.tide_times` |
| `pippa-hack-splitthebill` | `hack.splitthebill` |
| `pippa-hack-grid-carbon` | `hack.grid_carbon` |

**The fix.** The second line of the message names the exact id. Tell Claude:

> The build says my app id is wrong. Please set it to the id in the log and
> push again.

Two things worth knowing. The check reads the repository the code was pushed
to, so renaming a folder on a laptop changes nothing. And if the repository is
renamed after a successful publish, the id changes with it and has to be
updated.

## `FAIL the repository is called 'tide-times', which does not start with 'pippa-hack-'`

**What it means.** Only repositories created for the hackathon can publish, and
the name is how that is recognised.

**The fix.** Push to the repository from your invitation email. If you or
Claude created a fresh one instead, ask an organiser — the repository needs
renaming on GitHub, and a new one needs setting up to publish at all.

## `FAIL manifest.yaml is not valid: app.id: 'hack.tide-times' is not a valid dotted lowercase id`

**What it means.** Ids are dotted and lowercase, and **hyphens are not allowed
anywhere** — not in `app.id`, not in an outcome id. Repository names use
hyphens; manifest ids use underscores.

**The fix.** `hack.tide-times` becomes `hack.tide_times`. An outcome id like
`tide-times.next` becomes `tide.next` or `tides.next`.

One extra rule that catches people: the **first** segment of an id may contain
only letters and digits. `working_days.between` is refused; `workdays.between`
is fine.

## `FAIL manifest.yaml is not valid: manifest.yaml needs app_author_name: the public name shown with your app (a pseudonym, not your real name or email).`

**What it means.** `manifest.yaml` names nobody: `app_author_name` is empty or
missing, and there is no older `publisher:` line under `app:` either. Every
app shows a name with it, so the toolkit refuses a manifest without one.

**The fix.** One line at the top of `manifest.yaml`, above `app:`:

```yaml
app_author_name: "Tidewatcher"
```

A pseudonym, never your real name or your email address: it is shown to
everybody. [The rules for it](#warn-app_author_name-must-be-3-to-30-characters)
are below. Claude asks you for it.

---

# Refused before anything is deployed

Pippa checks whose repository a push came from, and the manifest's public
parts, before it publishes anything. When it refuses, the commit comment says
the app was not published, and gives one of the sentences below word for
word. The message starts `REFUSED: the app was not published:` (while Pippa
is being updated, it can start `CODE_ERROR` instead). Nothing was published,
and every version you published before is untouched.

None of these is a bug in your code. Nothing here checks for them before you
push. The build's check (`scripts/check.py`, in the **Check the app** step)
warns about the author name, `owner_email` and an address in `manifest.yaml`,
as `WARN` lines in the run's log on the **Actions** tab, but only Pippa's
sentence reaches the commit comment.

## `This repository isn't linked to a Pippa builder account, so it can't publish.`

```
This repository isn't linked to a Pippa builder account, so it can't publish.
Apps are published only from the repository Pippa Labs created for you: a fork
or a copy can't publish. If you think this is wrong, ask an organiser.
```

**What it means.** Pippa decides who an app belongs to from the repository it
was pushed from, and it has no record of this one. That is what a fork, a
copy, or a repository somebody made by hand looks like.

**The fix.** Push to the repository from your invitation email (Claude can move
the code across). If that is the one you pushed to, ask an organiser and give
them the repository's name. No change to any file fixes this.

## `This repository isn't linked to anyone's Pippa account yet.`

```
This repository isn't linked to anyone's Pippa account yet. If you were just
invited, finish creating your Pippa account with the link in your invitation
email, then push again. Otherwise ask an organiser.
```

**What it means.** Pippa knows Pippa Labs made this repository for you, but
your Pippa account does not exist yet, so there is nobody to give the app to.

**The fix.** Create your account from your invitation email (step 4 of
`README.md`), then push again. Nothing in the repository needs to change. If
you already have an account, ask an organiser.

## `This repository publishes hack.tide_times. Set id: under app: in manifest.yaml to hack.tide_times and push again.`

**What it means.** The same thing as
[the app id entry](#fail-manifestyaml-declares-hacktides-but-this-repository-publishes-hacktide_times)
above, said by Pippa rather than by the check: the id in `manifest.yaml` is
not the one this repository publishes.

**The fix.** Set it to the id in the message, and push again.

## `Remove owner_email from manifest.yaml.`

```
Remove `owner_email` from manifest.yaml. Pippa knows who owns this app from your
repository, and anything in a public repository can be read by everyone,
including its history.
```

**What it means.** An older template put your email address in
`manifest.yaml`, as `owner_email`. It is not needed any more: who owns the
app comes from the repository. In a public repository like this one the
push is refused while the line is there, because anybody can read the
address in `manifest.yaml`, and it stays in the git history.

**The fix.** Delete the `owner_email:` line (it may be at the top, or under
`app:`), and push again. The address is still in the history of the commits
that had it: ask an organiser if you want it taken out.

## `manifest.yaml contains an email address (at app.summary).`

```
manifest.yaml contains an email address (at app.summary). Remove it: everything
in manifest.yaml is shown to people or stored with your app.
```

**What it means.** One of the values in `manifest.yaml` has an email address
in it, at the place named in brackets. Everything in the manifest is shown to
the people who install your app, or kept with it, so Pippa refuses an address
anywhere in it, an example one included. The message never repeats the
address.

**The fix.** Take it out of the value it names, and push again. If your app
needs to tell people how to reach somebody, it has nowhere to do that.

## `WARN app_author_name must be 3 to 30 characters.`

**What it means.** `app_author_name`, the public name shown with your app,
breaks one of its rules. `scripts/check.py` warns, and Pippa refuses the push
with the same sentence. There is one sentence per rule, and you are told the
first rule the name breaks, in this order:

| You will see | The rule |
|---|---|
| `app_author_name must not be an email address or a web address.` | no `@`, no `://`, no `www.` |
| `app_author_name can't contain "pippa", "official" or "verified".` | in any capitals: it would look as if Pippa vouched for the app |
| `app_author_name must be 3 to 30 characters.` | after trimming, and with runs of spaces counted as one |
| `app_author_name can only use letters, numbers, spaces, dots, hyphens and underscores.` | letters of any alphabet are fine |
| `app_author_name must start with a letter or a number.` | not with `.`, `-` or `_` |

So fix the one you are told about, and check the rest before you push again.

One comes before all of these, and `scripts/check.py` stops on it rather than
warning, because the manifest cannot be read at all:

```
 FAIL manifest.yaml is not valid: app_author_name must be text: put the name in quotes.
```

`app_author_name: 1337` is a number to YAML, not a name. Put it in quotes:
`app_author_name: "1337"`. Pippa refuses the push with the same sentence.

**The fix.** Choose a name that fits, and push again. It is shown to
everybody, so make it a pseudonym: never your real name, never your email
address.

## `Another builder already uses the name "Tidewatcher". Choose a different app_author_name.`

**What it means.** Somebody else's apps are already shown as "by
Tidewatcher". An author name is the only name people see, so two builders
cannot share one: a copy would let one pass off an app as the other's. You
can use your own name on all of your apps.

**The fix.** Choose a different `app_author_name`, and push again.

---

# The manifest

These all come from the build step named **Check the app**. They stop the
deploy, so nothing reaches Pippa.

## `FAIL manifest.yaml is not valid: app.version: '0.1' is not a semantic version`

**What it means.** `app.version` must have three numbers.

**The fix.** `0.1.0`, not `0.1` and not `v0.1.0`.

The number matters more than it looks. Each version keeps its own code, and a
version you have submitted for review cannot be pushed again, so a change to
it needs a new number. `docs/REVIEW_AND_SHARING.md` says when to change it.

## `FAIL manifest.yaml is not valid: outcomes[0].inputs[0].type: unknown type 'str' (allowed: string, integer, number, boolean, datetime, duration, timezone, array, object)`

**What it means.** The manifest has its own small type vocabulary and it is not
Python's. `str` is not a type here; `string` is.

**The fix.** Use one of the nine listed types. Two have extra rules:

- `array` must also declare `item_type`, or you get
  `an array must declare item_type`.
- `timezone` must be a real IANA name, such as `Europe/London`.

```yaml
      - name: areas
        type: array
        item_type: string
        description: The flood areas with a warning in force.
```

## `FAIL manifest.yaml is not valid: outcomes[0].output: must be a non-empty list`

**What it means.** Every outcome has to declare at least one output field. An
outcome that returns nothing cannot be described to a user before they install
it, so it is refused.

**The fix.** Declare the fields the app really returns. `inputs` may be empty;
`output` may not.

## `FAIL manifest.yaml is not valid: persistence: an Agent App may not persist anything; the agent is the only data store, so this must be 'none' (got 'session')`

**What it means.** `persistence: none` is the only accepted value, and the
field is required rather than defaulted, so that it has to be written and
meant.

**The fix.** Put it back:

```yaml
persistence: none
```

## `FAIL manifest.yaml is not valid: while scanning for the next token found character '\t' that cannot start any token`

**What it means.** There is a tab character in `manifest.yaml`. YAML forbids
tabs for indentation.

**The fix.** Replace every tab with spaces. Tell Claude, which is a ten-second
job for it.

## `FAIL manifest.yaml is not valid: mapping values are not allowed in this context`

**What it means.** YAML lost track of the structure, nearly always because of
indentation. The line number in the error is where YAML noticed, which is
usually one or two lines after the real mistake.

**The fix.** Tell Claude. If you are reading the file yourself, check these
four things in this order.

1. **Two spaces per level, consistently.** Mixing two and four spaces inside
   one block breaks it.
2. **List items line up.** Every `- name:` under `inputs:` must start at the
   same column.
3. **A colon inside an unquoted value.** `summary: Tides: when and where` is
   invalid. Quote it: `summary: "Tides: when and where"`.
4. **A `>-` block whose text is not indented.** The continuation lines must be
   indented further than the key:

   ```yaml
   # Correct
   summary: >-
     Works out how many days there are until a date you name, and says
     which day of the week it falls on.

   # Wrong - the text is at the same indent as the key
   summary: >-
   Works out how many days there are until a date you name.
   ```

`>-` means "fold these lines into one sentence and drop the trailing newline".
It exists so a long sentence can be wrapped in the file.

## `FAIL tide.times has 2 example phrase(s)`

```
 FAIL tide.times has 2 example phrase(s)
       Pippa chooses your app by comparing the user's message against these.
       With fewer than about three, your app will rarely be picked. Five to
       ten is a good number.
```

**What it means.** Exactly what it says, and it blocks the deploy.

**The fix.** Five to ten per outcome, in a person's words. See
[My app published but Pippa never uses it](#my-app-published-but-pippa-never-uses-it)
for what good phrases look like — that section is worth reading even when the
build is green.

## `WARN Add app_author_name to manifest.yaml: the public name shown with your app. Until then it shows publisher.`

**What it means.** The manifest was written for an older template: it has
`publisher:` under `app:` and no `app_author_name`. It still publishes, and
shows the `publisher` name, but Pippa warns on every push.

**The fix.** Move the name to the top of `manifest.yaml` and delete the
`publisher:` line:

```yaml
app_author_name: "Tidewatcher"
```

If `publisher` was your real name, this is the moment to choose a pseudonym
instead: the name is shown to everybody.

## `WARN README.md:12 contains the email address s***@<domain>`

**What it means.** A file in your repository has an email address in it, at
the line named. Every file can end up public, so the build refuses a push with
an address in any file (binary files and files over a megabyte aside), and
`.githooks/pre-commit` stops the commit before that. The address is never
printed whole: the first letter and the domain are enough to recognise it.

Addresses that cannot belong to anybody are fine: anything at `example.com`,
`example.org` or `example.net`, a domain ending `.example`, `.test` or
`.invalid`, and GitHub's no-reply addresses. So is a file name that only looks
like an address, such as a picture's `logo@2x.png`.

**The fix.** Take the address out of the file and push again. If it was an
example, use one at `example.com`. Once pushed, it stays in the git history:
ask an organiser if it was a real person's.

## `WARN the commit's author email is s***@<domain>, not a GitHub no-reply address`

**What it means.** The commit carries an email address that is not GitHub's
private no-reply one, and everybody who can read the repository can read it.
In a public repository like this one the build refuses the push:

```
Your commit shows the email address s***@<domain> publicly. Set
`git config user.email` to your GitHub no-reply address and amend the commit.
```

**The fix.** Set this repository's address to your no-reply one, and its name
to your pseudonym, so every later commit carries those instead:

```bash
gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"'
git config user.email "<id>+<login>@users.noreply.github.com"
git config user.name "Tidewatcher"     # your app_author_name
```

A commit you have not pushed yet can be fixed in place:
`git commit --amend --no-edit --reset-author`. One you have already pushed
stays in the history, because `main` cannot be rewritten: push a new commit,
and ask an organiser if the old one needs taking out. Claude sets the address
as one of its first steps (`CLAUDE.md`, step 1), and on GitHub, **Settings →
Emails → Keep my email addresses private** makes the edits you make on the
website use the no-reply address too.

---

# Shapes: inputs and outputs

## `OutputShapeViolation`

You will see one of these, either in the build log when the tests run, or from
Pippa after the app is live:

```
hack.tide_times returned a result that does not match the output shape
declared for 'tide.times': output.next_low: not declared in the manifest
(declared: height_m, next_high, port)
```

```
hack.tide_times returned a result that does not match the output shape
declared for 'tide.times': output.next_high: required value is missing
```

```
hack.tide_times returned a result that does not match the output shape
declared for 'tide.times': output.height_m: expected number, got str
```

**What it means.** `manifest.yaml` promises exactly which fields come back. The
runtime checks every result against that promise and refuses anything that does
not match — a field that was not declared, a declared field left out, or a
field of the wrong type. This is deliberate: a user sees a permission screen
built from the manifest before they install, so the manifest has to be the
truth.

**The fix.** The `output` block and the `return Result(data={...})` line have to
agree. The key names must be identical and the types must match.

```yaml
    output:
      - name: height_m
        type: number
      - name: next_high
        type: datetime
      - name: port
        type: string
```

```python
return Result(data={
    "height_m": 4.2,
    "next_high": "2026-10-22T18:14:00+01:00",
    "port": "Avonmouth",
})
```

Common causes, in rough order of frequency:

- **A field was added to `data` and not to the manifest.** Add it to `output`.
- **A code path returns fewer fields.** An error path that returns
  `{"port": port}` and nothing else still has to return every declared field —
  or should raise `AgentAppError` instead.
- **A field is sometimes absent.** Declare it `required: false`:
  ```yaml
      - name: next_low
        type: datetime
        required: false
  ```
- **`integer` received a `float`.** `3.0` is not an integer here. Use `number`,
  or cast with `int()`.
- **`integer` received a `bool`.** In Python `True` is an `int`; in a manifest
  it is not. Declare `boolean`.
- **`datetime` received a naive timestamp.** A `datetime` must carry a UTC
  offset. `datetime.now()` has none — and the code should be using
  `call.context.now` anyway.
- **`timezone` received something that is not an IANA name.** `Europe/London`,
  not `London` and not `GMT`.

You may also see:

```
hack.tide_times returned dict, not a Result
```

That means `handle` returned a plain dictionary instead of
`return Result(data={...})`.

The tests catch this in the build, because they go through `LocalRunner`, which
enforces the manifest the same way the live runtime does. If this reaches a
user, the tests were not covering that path — ask Claude to add one.

## `InputShapeViolation`

```
inputs do not match the manifest for 'tide.times': inputs.port: required value
is missing
```

```
inputs do not match the manifest for 'tide.times': inputs.postcode: not
declared in the manifest (declared: port, timezone)
```

**What it means.** The same check in the other direction. The app is handed only
the inputs the manifest declares — never more, never fewer than the required
ones. In practice this shows up in the build, while the tests run, because in
live use Pippa fills the inputs from the manifest and cannot invent a field
that was never declared.

**The fix.**

- **"required value is missing".** Either the test should pass that input, or
  the manifest should mark it `required: false` because the app can genuinely
  work without it.
- **"not declared in the manifest".** A key was passed that the manifest does
  not list. Add it to `inputs`, or drop it from the test.
- **A type complaint on `timezone`.** `'London' is not an IANA time zone`.
  Use `Europe/London`.

`required: false` means "may be absent", not "may be empty". An input the user
did not mention arrives as an empty string if the description asked for one —
which is what the description should ask for:

```yaml
        description: >-
          The port the user named. If the message does not name one, return
          an empty string rather than guessing.
```

Without that sentence the extractor will guess, and a guessed input produces a
confidently wrong answer.

## `this app does not serve outcome 'tide.time' (serves: tide.times)`

**What it means.** `UndeclaredOutcome`. Something asked for an outcome id that
is not in the manifest. Usually a typo in a test.

**The fix.** Match the id exactly, including the dot.

## `FAIL app.py does not define a class called App`

```
 FAIL app.py does not define a class called App
       The handler imports `App` from app.py. The name matters.
```

**What it means.** Pippa imports a class called `App` from `app.py`. The name is
part of the contract.

**The fix.** The class has to be called `App`, and `app.py` and `manifest.yaml`
have to sit at the top level of the repository — not in a `src/` folder.

## `ModuleNotFoundError: No module named 'app'`

**What it means.** The build could not find `app.py` where it expects it, at the
top level of the repository. A file in a subfolder is not found and, as it
happens, is not published either.

**The fix.** Move `app.py` and `manifest.yaml` back to the top level.

## `ValueError: Invalid format string`

**What it means.** `%-d` or `%-H` was used in `strftime`. Those are a GNU
extension: they work on some systems and raise on others, so this can appear in
the build or only after the app is live.

**The fix.** Build the string without them:

```python
pretty = f"{target.strftime('%A')} {target.day} {target.strftime('%B')} {target.year}"
```

---

# The build itself

## A step has a red cross

**Symptom.** The Actions run failed. The log ends with
`Error: Process completed with exit code 1`.

**What it means.** Which step failed tells you where to look.

| Step | What failed |
|---|---|
| **Check the dependencies** | `requirements-dev.txt` or a committed wheel file — see [`FAIL requirements-dev.txt line 10 installs the Pippa SDK`](#fail-requirements-devtxt-line-10-installs-the-pippa-sdk) |
| **Get permission to install the Pippa SDK**, **Install the Pippa SDK** | Not something you can fix. Ask an organiser. |
| **Check the app** | A rule above — the manifest, the app id, the class name, or the tests |
| **Publish** | The package or Pippa's own refusal — see below |
| **Get permission to publish** | Not something you can fix. Ask an organiser. |

**The fix.** Open the red step, scroll to the `FAIL` lines, and give Claude the
link to the run. Read the first `FAIL` rather than the last: the ones below it
are often knock-on effects.

## `FAIL the tests fail`

**What it means.** Claude wrote tests in `test_app.py`, and the build runs them
before it publishes. One of them did not pass, so nothing was deployed.

**The fix.** Tell Claude, with the link to the run. The pytest output directly
above that line names the failing test and the assertion.

This is the test suite doing its job. A failing test here is far better than an
app that publishes and then returns the wrong number to a real person.

## `FAIL the Pippa SDK is not installed`

**What it means.** The build's own setup did not complete. The toolkit is not
in the repository: the build installs it at the start of every run, before it
checks the app.

**The fix.** Not something you can fix in the app. Ask an organiser, with the
link to the run.

## `FAIL requirements-dev.txt line 10 installs the Pippa SDK`

**What it means.** The build installs the Pippa SDK itself, at the version your
app runs with, and refuses an app that brings its own. The same step refuses
these too, each with the file and the line:

- `sets a package index or download location` — a `-i`, `--index-url`,
  `--extra-index-url`, `-f` or `--find-links` line. Packages come from PyPI
  only.
- `installs from a file or folder` — a wheel, an archive or a path where a
  package name should be.
- `installs from a URL` — a link (`name @ https://...`, `git+https://...`)
  where a package name should be.
- `is a wheel file in the repository` — a `.whl` file anywhere, `vendor/`
  included.

**The fix.** Tell Claude, with the link to the run. It deletes the line or the
file named under the `FAIL` and pushes again. Nothing else in the app changes.

## `ERROR: the package is 5218 KB; the limit is 3072 KB.`

**Symptom.** The Publish step prints the size, then the five largest files:

```
ERROR: the package is 5218 KB; the limit is 3072 KB.

  Largest files:
    4100 KB  cities.json
     812 KB  logo.png
```

**What it means.** What ships to Pippa must stay under 3 MB. Directly above the
error, the log lists every file that was packaged:

```
Packaged 3 file(s), 14 KB:
  app.py
  manifest.yaml
  ports.json
```

Already left out, so these are never the cause: `.git`, `.github`, `vendor`,
`scripts`, `docs`, `__pycache__`, `.venv`, `venv`, `.pytest_cache`,
`.ruff_cache`, `.idea`, anything ending `.pyc`, `.pyo`, `.whl`, `.zip`,
`.tar.gz` or `.log`, plus `requirements-dev.txt`, `CLAUDE.md`, `README.md`,
`.gitignore`, `pytest.ini` and the `test_*.py` files.

**The fix.** It is a file at the top level — usually a committed data file, a
copied library folder or images. Options, in order of preference:

- Fetch the data at call time from a public API instead of shipping it.
- Trim a large JSON or CSV down to the rows the app uses.
- A library copied into the repository to dodge the import rule will not work
  anyway — see
  [ImportError or ModuleNotFoundError after the app is live](#importerror-or-modulenotfounderror-after-the-app-is-live).

## `ERROR: app.py is not in the package. It must be at the top level.`

**What it means.** `app.py` is in a subfolder, so it was not packaged.

**The fix.** Move `app.py` and `manifest.yaml` to the top level of the
repository, next to the `scripts/` folder.

## `PLATFORM_ERROR: the app was not published because of a problem on the Pippa platform`

```
PLATFORM_ERROR: the app was not published because of a problem on the Pippa
platform, not in the app. Reference: gh-1234567890-1
```

**What it means.** Something on Pippa's side failed: the build could not get
permission to publish, could not reach Pippa, or Pippa itself failed. Your app
is not the cause, and changing it will not help. The workflow in `.github/` is
managed by the organisers. Do not edit it: a push that changes it still goes
through, but Pippa only accepts a publish from the organisers' workflow,
unchanged, so an edited workflow cannot publish the app.

**The fix.** Do not change the code. You may re-run it once yourself
(Claude does not): Actions tab, open the failed **Publish to Pippa** run,
**Re-run jobs**, **Re-run all jobs**. If it fails again, show an organiser the
reference from the message. A run that ended with no `pippa/publish` status and
no comment on the commit counts as the same thing, unless its summary says
**Nothing to publish yet**: that is the placeholder app id or an empty
`app_author_name`, see [`Nothing to publish yet`](#nothing-to-publish-yet).

## `Pippa refused to publish this app:` ... `hack.` namespace

**Symptom.** The Publish step prints a banner:

```
====================================================================
Pippa refused to publish this app:

  <a message about the app id and the hack. namespace>
====================================================================
```

The exact wording comes from Pippa and may differ. What matters is that it
names your app id.

**What it means.** The signed token says which repository is publishing, and
Pippa derives the app id from that and nothing else. The manifest has to agree.
You cannot publish outside `hack.`, and you cannot publish as somebody else's
app — which is also why nobody can publish as yours.

**The fix.** Make `app.id` match the repository, as described under
[The app id](#the-app-id).

## `Pippa refused to publish this app:` ... secrets or connectors

**Symptom.** The same banner, with a message naming `secrets` or `connectors`.

**What it means.** Those two blocks declare that the app needs a real person's
credentials — a Google account, for example. Hackathon apps may not ask for
them. Nobody at a workshop can consent on a user's behalf to handing a
stranger's app a credential, so registration refuses any app that declares
either.

A related error appears earlier, during **Check the app**, if a secret is
declared without its connector:

```
 FAIL manifest.yaml is not valid: secrets: secret 'google_oauth' names
 connector 'google.calendar', which this manifest does not require
```

**The fix.** Both blocks come out of `manifest.yaml` entirely, and the idea has
to change so it does not need an account. The app can still call the public
internet. If a service needs **the app's own** API key, that is not a
`secrets:` block: declare it under `app_secrets:` and set its value in Pippa
(see [API keys](#api-keys)). Never put the key itself in a file. The no-key
APIs in `docs/IDEAS.md` avoid the question altogether.

## `Pippa refused to publish this app:` ... `is waiting for review, so its code can't change`

**Symptom.** The same banner, naming your app and the version you pushed:

```
hack.tide_times 0.1.0 is waiting for review, so its code can't change. Change
`version:` in manifest.yaml (for example to 0.1.1) and push again — or
withdraw 0.1.0 from review on the Apps page first.
```

**What it means.** You pressed **Submit for review** on that version, so it is
in the queue, and a version's code cannot change while it is there: the thing
a reviewer approves has to be the thing people run. Nothing was published, and
every version you already had is untouched.

**The fix.** It depends on what you want.

- **Leave it in the queue and go on working.** Change `app.version` in
  `manifest.yaml` (`0.1.0` becomes `0.1.1`) and push. The new version is a
  draft, private to you and your testers.
- **Change the version that is waiting.** On the Apps page, open your app's
  card under **Created by me**, then **Versions**, and press **Withdraw from
  review** next to it. It becomes a draft again: push with the same version
  number, then press **Submit for review** once more.

## `Pippa refused to publish this app:` ... `has been reviewed, so it is frozen`

**Symptom.** The same banner, naming your app and the version you pushed:

```
hack.tide_times 0.1.0 has been reviewed, so it is frozen. Change `version:` in
manifest.yaml (for example to 0.1.1) and push again.
```

**What it means.** A reviewer sent that version back, with a reason you can
read on your app's card. A reviewed version keeps the code the reviewer saw,
so it cannot be pushed again, and it cannot be submitted again either.
Nothing was published.

**The fix.** Change `app.version` in `manifest.yaml` (`0.1.0` becomes
`0.1.1`), fix what the reason names, and push. Then press **Submit for
review** next to the new version.

## `Pippa refused to publish this app:` ... `has already been approved and is in use`

**Symptom.** The same banner, naming your app and the version you pushed:

```
hack.tide_times 0.1.0 has already been approved and is in use. Bump the
version in manifest.yaml and push again — the new version is yours to test
privately, and the approved one keeps working for everyone until you submit
it and it is approved in turn.
```

**What it means.** A reviewer approved that version, so other people have it.
Replacing its code in place would mean the thing that was approved and the
thing people are running were two different things, which would make approval
worthless. That is why Pippa keeps a copy of every version's code, and why a
version is frozen from the moment it is submitted. Only a draft can be pushed
again under the same number.

**The fix.** Bump `app.version` in `manifest.yaml`:

```yaml
app:
  version: 0.2.0     # was 0.1.0
```

Push again. The new version publishes privately to you, the approved one goes
on answering questions for everybody who has it, and when you submit the new
one and it is approved it takes over. To try the new one yourself, install it:
**Update to latest** on your app's card.

## `Pippa refused to publish this app:` ... `is suspended by Pippa Labs, so new versions can't be published`

**Symptom.** The same banner, naming your app:

```
Tide Times is suspended by Pippa Labs, so new versions can't be published.
Read the reason on the Apps page and talk to an organiser.
```

**What it means.** A reviewer has suspended your app — every version of it.
While it is suspended, nothing can be published, a new version number
included. See [My app was approved and now it has
vanished](#my-app-was-approved-and-now-it-has-vanished).

**The fix.** Not a change to the code. Read the reason on your app's card on
the Apps page, and talk to an organiser about it.

## `Pippa refused to publish this app:` ... `has been withdrawn by an organiser`

**Symptom.** The same banner:

```
hack.tide_times has been withdrawn by an organiser and cannot be published
again. Ask an organiser why.
```

**What it means.** An organiser has stopped the app completely: no version of
it runs, and nothing can be published. This is not the **Withdraw from review**
button on the Apps page, which you press yourself and which only takes one
version out of the review queue.

**The fix.** Ask an organiser.

---

# API keys

An app that needs its own key declares it under `app_secrets:` in
`manifest.yaml`, reads it with `os.environ["NAME"]` inside `handle()`, and the
value is set in Pippa: **Apps**, **Created by me**, the app, **Keys**.
`docs/API_APPS.md`, "Using API keys", is the whole story.

## `Commit stopped: a file you are committing looks as if it holds a key.`

```
Commit stopped: a file you are committing looks as if it holds a key.
This looks like a key, a token or a password:
  app.py:12: a key-like value given to OPENWEATHER_API_KEY
```

**What it means.** The commit check (`.githooks/pre-commit`, which runs
`scripts/check_secrets.py`) found what looks like a key in a staged file, or a
file that holds keys by its nature, such as `.env` or a `.pem`. It names the
file and the line, never the value. Nothing was committed.

**The fix.** Take the value out of the file: declare the key under
`app_secrets`, read it with `os.environ`, put the value in `.env` on your
computer and under **Keys** in Pippa. Stage the file again and commit. Never
use `--no-verify`. If the value is genuinely not a key (a fake value in a
test), end the line with `# pragma: allowlist secret`; that does not work for
a key in a provider's own format (AWS, GitHub, OpenAI, ...) or a private key,
which is always a real one. If a staged file is
`.env`, unstage it: `git restore --staged .env`.

## `FAIL app.py:12: a key-like value given to OPENWEATHER_API_KEY`

The same finding from `scripts/check.py`, which checks every file git tracks,
so it also covers a copy of the repository where the commit check was never
switched on. The build stops here too, and publishes nothing.

**The fix.** As above. **If that commit was ever pushed, the key is already
in the history**, where anyone who can read the repository can find it.
Rotate it with the provider first (make a new key, delete the old one), set
the new one under **Keys**, then remove the old one from the code. The repository is public: assume the key has been copied.

## `a value that looks like a key was committed in app.py:12`

The build's own scan of the commits you pushed found a key. Nothing was
published. The key **was pushed**, so do the rotation above first, then remove
it from the code and push again. The message never shows the value.

## `FAIL app_secrets[0].name is 'openweather': it must be capital letters, digits and underscores, 3 to 64 characters, starting with a letter (like OPENWEATHER_API_KEY).`

**What it means.** An entry under `app_secrets` breaks one of the rules, and
Pippa would refuse the push. The others you may see:

- `... is reserved for the platform the app runs on`: names starting
  `PIPPA_`, `AWS_`, `LAMBDA_` or `OTEL_`, and system names such as `PATH` or
  `HOME`, belong to the platform. Choose another, such as one starting with the
  service's name.
- `... is declared twice`, `... needs a description`, `... has a description
  of 230 characters; at most 200`, `... required must be true or false`,
  `app_secrets declares 21 keys; an app may declare at most 20`.
- `... has scope: user`: keys that each user provides are not available yet.
  Leave `scope` out, or set it to `app`.

**The fix.** Change the entry as the message says, and push again.

## `WARN the app reads GIPHY_KEY (app.py:31), but manifest.yaml does not declare it under app_secrets`

**What it means.** The code reads an environment variable that the manifest
does not declare. Pippa only gives the app the keys it declares, so in Pippa
it will be missing (on your computer it may still be in `.env`, which is why
it can work here). It is a warning: the push still publishes.

**The fix.** Declare it under `app_secrets`, with a description, and set its
value under **Keys**.

## `WARN OPENWEATHER_API_KEY is read when app.py is imported (app.py:8), not in a call`

**What it means.** The key is read at the top of a file, when the module is
loaded. Pippa puts the key in `os.environ` for each call only, so at that
moment it is not there yet, and the app sees nothing.

**The fix.** Move the `os.environ` line inside `handle()`, or a method it
calls.

## `Published, but it can't run until you add OPENWEATHER_API_KEY in Created by me.`

**What it means.** The push published, but a key the app declares as
`required` has no value yet. Until it does, Pippa does not call the app:
whoever asks gets *"This app isn't ready yet: its builder still has to add
OPENWEATHER_API_KEY."*, nobody else can install it, and it cannot be submitted
for review.

**The fix.** No push needed. Open Pippa, **Apps**, **Created by me**, the app,
**Keys**, and set the value. The next question uses it.

## `This app isn't ready yet: its builder still has to add OPENWEATHER_API_KEY.`

What a person sees in the chat while a required key has no value: see the
entry above. Setting the key under **Keys** fixes it at once, for every
version of the app that declares it. A version published before the app
changed hands says something else ("This version was published before the
app changed hands", below).

## The key is set, but the app still says it is missing

- **The name must match exactly**, in capitals: the one under
  `app_secrets` in `manifest.yaml`, the one under **Keys**, and the one in
  `os.environ["..."]`.
- **The version that answers must declare it.** Pippa hands an app only the
  keys the published version's manifest declares. A version published before
  you added the `app_secrets` entry does not get it: push, and make sure the
  new version is the one installed (the badge names the version).
- **Read it inside `handle()`**, not at the top of a file (above).

## There is no **Keys** section on my app's card

- **No published version declares a key yet.** A key is listed under
  **Keys** once a version that declares it under `app_secrets` is published.
  Push first: the push publishes without the value.
- **You are signed in with another account.** Only the Pippa account the
  repository belongs to sees **Keys**, and only it can set them. See "My app
  published and I cannot find it in the Apps list", below.

## `This app has had a lot of requests in the last minute; try again in a minute.`

**What it means.** Pippa limits how often an app can be called: by default
20 times a minute and 300 times a day for each Pippa agent that calls it
(the assistant behind one Pippa account), and 120 times a minute and 3,000
times a day for the app from everybody together, its builder included. The
first limit is per agent, not per person: somebody with several Pippa agents
gets a share for each. Over a limit Pippa does not call the app at all.
Nothing is wrong with the app, and a call Pippa did not run is not counted.

**The fix.** Wait for the next minute. If real use needs more, ask an
organiser: Pippa Labs can raise one app's limits. Never make the app retry,
or call itself, to get round them.

## `This app has had a lot of requests today; try again tomorrow.`

The same, for the daily limits. They start again at midnight UTC.

## `This app can't run right now. Try again in a little while.`

**What it means.** Pippa could not read the app's keys, a fault on Pippa's
side, so it did not call the app. Nothing in the app causes it.

**The fix.** None in the repository, and no push helps. If it lasts, tell an
organiser when it happened.

## `This app can't run right now because Pippa can't count its requests. Try again in a little while.`

**What it means.** Pippa counts the calls to every app (the limits above).
This time it could not count the call, a fault on Pippa's side. An app with
no key set runs anyway, but an app that has a key set is not called, so
that nobody can spend the key without a limit. Nothing in the app causes it.

**The fix.** None in the repository, and no push helps. If it lasts, tell an
organiser when it happened.

## `This version was published before the app changed hands; its builder must publish again.`

**What it means.** An app's keys go only to a version published by its
current owner, from its current repository. This version was published
before one of those changed: Pippa Labs moved the app, or re-linked its
repository, to another Pippa account, or the repository was renamed, which
changes the app id. Every key was deleted in the change, and versions
published before the change get no keys, so Pippa does not run this one at
all. Nothing in its code causes it.

**The fix.** For the app's owner now: set its keys again under **Keys**,
push a version of your own, and make sure it is the one installed (the badge
names the version). If the repository was renamed, it publishes a new app id
from now on: set `app.id` to it first ("The app id and the author name",
above), push, and set the keys on that app's card.

## `Pippa refused to publish this app:` ... `app_secrets`

**What it means.** Pippa refused the declaration itself. Most often one of the
rules above (the build's check names it first). If the message says API keys
are not available, Pippa has not switched them on yet: no change to the app
fixes that. Tell an organiser, with the commit link.

---

# Who can see it

A published app is **private to its owner** until a reviewer approves it.
`docs/REVIEW_AND_SHARING.md` is the whole story; these are the ways it
surprises people.

## My app published and I cannot find it in the Apps list

**Symptom.** The build was green and the commit comment says the app is live.
(Live means published: the version is in Pippa, private to you and your
testers until it is approved.) You are signed in to Pippa, and the Apps page
does not have it under **Created by me**.

**What it means.** One of three things, in order of likelihood.

1. **The page has not reloaded.** It loads the list once. Reload it.
2. **You are signed in with another account.** The app belongs to the Pippa
   account your repository was created for: the one your invitation went to.
   Signed in as anybody else, you cannot see it. No **Created by me** tab at
   all is the usual sign. Sign in with that account; nothing in the
   repository needs to change, and nothing in it can change who the owner is.
3. **It is suspended.** See below.

## My tester cannot see my app

**What it means.** Usually one of:

- **The address.** A share is matched against the address they sign in to
  Pippa with, not the one on their laptop or their badge.
- **They have no Pippa account.** Sharing an app is not an invitation to the
  platform. They need an account of their own first.
- **Their page has not reloaded**, as above.

A tester sees your app, installs it and uses it, at the version you choose for
them. They cannot submit it, cannot add other testers, cannot choose a
version, and cannot see anything else you have published — that is
deliberate, not a fault.

## My tester gets an older version than the one I pushed

**What it means.** Testers get the version you choose for them, not simply the
newest. Usually one of:

- **You chose a version for them.** Your app's card under **Created by me**
  says which, under **Testers get**. To give them each new push, set it to
  **Your latest version** in the testers dialog — or pick the version you want
  them on.
- **The new version adds an outcome** — something new people can ask it to
  do. A tester has to agree to that, and Pippa does not ask them by itself:
  they keep the newest version they have agreed to. Their Apps page shows an
  **Update** button on your app, under **Shared with you for testing**. Ask
  them to press it.

## My app was approved and now it has vanished

**Symptom.** It was public and working. Now it is not in the list, and Pippa
answers as though it had never been installed — for other people and for you.

**What it means.** It has been **suspended**: a reviewer has pulled an app
that was approved. Unlike every other private state this one stops the app for
everybody, its builder included, because the reason to suspend something is
that it should stop.

**The fix.** Your app's card on the Apps page, under **Created by me**, shows
the reason it was suspended. Pushing again does not undo it — while the app
is suspended every push is refused, a new version number included — and
neither does submitting it again. Read the reason, and talk to an organiser.

## `Code not kept`

**Symptom.** Under **Versions** on your app's card, a version is marked **Code
not kept**.

**What it means.** That version was published before Pippa kept a copy of
each version's code, so there is nothing left to run. It cannot be installed
or run. Every version published since keeps its own code.

**The fix.** If it is still a draft, push it again with the same version
number: it is published afresh, with its code kept. Otherwise change
`app.version` in `manifest.yaml` and push.

If the version marked **Code not kept** was your approved one, the people who
installed your app cannot use it until a newer version is approved. Push a
new version, try it, and press **Submit for review** next to it.

---

# After it is published

## My app published but Pippa never uses it

**Symptom.** The run went green. The log said:

```
  YOUR APP IS LIVE IN PIPPA

  App      Tide Times  (hack.tide_times v0.1.0)
  Can do   tide.times
```

You installed it at [app.getpippa.ai/apps](https://app.getpippa.ai/apps). You
asked Pippa a question your app clearly handles. Pippa answered in her own
words, or said she could not help, and your app is nowhere to be seen.

**This is the most common problem, and it is usually not a bug in your code.**
The app was never called. From the outside that looks identical to the app
being broken, which is why this is the longest section here.

First, a quick check: when Pippa uses an app, the answer carries a badge naming
it — `[via Tide Times 0.1.0 by Tidewatcher]`, where `0.1.0` is the version that
answered. No badge means your app did not answer: either it was never called,
or it was called and refused, and from the chat the two look identical.

**Then ask the same question with `@` in front.** Start the message with `@`,
pick your app from the list, and send the same words. That skips routing —
Pippa calls your app whatever the words — so it tells the two apart:

- **It fails with `@` too.** Your app or its inputs are the problem, not
  routing, and nothing in this section will fix it. Pippa says why in one
  sentence; the entry
  [`Tide Times couldn't answer: …`](#tide-times-couldnt-answer-i-could-not-find-a-port-with-that-name)
  below explains each one.
- **It answers with `@`.** Your app works, and the rest of this section is for
  you. That is all it proves: it skipped routing, so it says nothing about
  whether Pippa would pick your app herself. Test that without the `@`, and
  with **Keep using** switched off, or every message goes to your app. The
  badge should say **picked by Pippa**, not **you picked it**.

**Before reading further, ask Claude to check your manifest against the
routing checker.** `scripts/routing_check.py` covers most of what the rest of
this section describes. It needs the Pippa toolkit, which only the build has,
so Claude reads it rather than running it. The build runs it after every
passed check, and its findings appear under **Warnings** in the commit comment
of the published app.

It lists the faults that stop an app being chosen — a phrase that reduces to
one ordinary word, two of your outcomes fighting over the same vocabulary, a
word another installed app already owns, a summary whose first clause says
nothing. Every one of those has been a real
app that was never called.

It cannot promise your app *will* be chosen — the decision is made by a model
reading your manifest alongside the manifests of every other app that person
has installed, which this repository cannot see. What it can do is rule out
the causes that live in your own file. Start there, then come back here.

There are two causes, and they need different fixes.

### Cause 1: the app is the wrong shape

Measured against the live system: apps that **answer with a fact or a figure**
get used. Apps that mainly **rewrite or generate text** usually do not, because
Pippa answers those herself before an app is ever consulted.

| Gets used | Usually does not |
|---|---|
| calculations and conversions | translating |
| live lookups — weather, tides, transport, prices, air quality | summarising, rewriting |
| anything about a named place | writing poems, names, copy |
| anything about a date or a time | definitions, acronyms |
| anything worked out from numbers the user gives | explaining how something works |
| | choosing for the user, opinions |

If your app is in the right-hand column, no amount of rewording will rescue it.
It will keep losing to Pippa's own answer. The fix is a different app, and it
is cheaper than it sounds — ask Claude to repoint the same repository at a
nearby idea from the left-hand column. `docs/IDEAS.md` has more than twenty,
each with a free API that needs no sign-up.

### Cause 2: the example phrases are too weak

Pippa does not have a list of commands. When a message arrives she compares it
against the `summary` and `example_phrases` of every outcome of every installed
app, and picks the best match. `example_phrases` are not documentation. They
are the behaviour that decides whether your app runs.

Work through this in order.

**1. Is it installed — and at the version you pushed?**
Publishing makes a version available. It does not install it, and publishing
a new version does not change the one installed for you. Open
[app.getpippa.ai/apps](https://app.getpippa.ai/apps), choose **Created by
me**, and read **Installed for you** on your app's card. **Not installed**:
press **Install**. An older version than the one you pushed: press **Update
to latest**, or switch on **Always use my latest version**. If your app is not
there, reload the page — the list is loaded once. If it is still not there, it
is a visibility problem rather than a routing one: see [My app published and I
cannot find it in the Apps
list](#my-app-published-and-i-cannot-find-it-in-the-apps-list).

**2. Ask it using one of your own example phrases, word for word.**
The single most useful test. Open `manifest.yaml` on GitHub, copy a phrase, and
type it exactly.

- **It works.** Good. The app is live and installed, and the only problem is
  that the phrases do not cover how people really ask. Go to step 3.
- **It does not work.** The wording is not the problem. Check that it is
  installed, that the Actions run really did publish the version you think,
  and that **Installed for you** names that version.

**3. Count the phrases.**
Fewer than three and the build fails. Three is barely enough. **Five to ten per
outcome** is the number that works.

**4. Write how a person asks, not how you would name a function.**

```yaml
# Weak - nobody types this
example_phrases:
  - get_tide_times
  - tide time lookup
  - query tidal data

# Strong - how someone actually asks
example_phrases:
  - when is high tide at
  - what time is low tide
  - is the tide in or out at
  - when does the tide turn
  - how high is the tide at
  - tide times for
```

**5. Use carrier words, not one specific subject.**
The subject changes every time somebody asks. Including it dilutes the match.

```yaml
# Weak - "Avonmouth" will almost never be in the real message
  - when is high tide at Avonmouth

# Strong - the part that is always there
  - when is high tide at
```

**6. Do not use words another app owns.**
"today", "tomorrow", "this week", "my calendar", "my schedule" and "what's on"
belong to **Pippa Diary**, the built-in app that handles the user's calendar. A
phrase containing one of those will usually lose to it, however good the rest
of your app is.

```yaml
# Weak - Pippa Diary will win this
  - what are the tides today

# Strong
  - when is the next high tide at
```

**7. Give each outcome its own vocabulary.**
If two outcomes both say "tide", Pippa has to choose between them by guessing,
and will sometimes pick the wrong one. Make the words clearly different, or
merge them into one outcome with an input saying which variant was wanted.
**One good outcome beats two that tie.**

**8. Fix the `summary` as well.**
The outcome's `summary` is matched too. Write it in the user's words: "Say when
the next high and low tide are at a named port", not "Tidal data retrieval
endpoint".

**9. Check the inputs can actually be extracted.**
If an outcome requires an input that is rarely present in a real message, Pippa
may skip the outcome. Keep required inputs to the ones a person would naturally
say, mark the rest `required: false`, and tell the extractor what to do when a
value is missing:

```yaml
        description: >-
          The port or coastal place the user named. If the message does not
          name one, return an empty string rather than guessing.
```

**10. Push again, and test the version you pushed.**
Routing reads the manifest of the version you get, so a change reaches it only
once you are on that version. Ask Claude to edit `manifest.yaml` and push. If
the version installed for you is a draft, keeping its number is fine: pushing
it again changes that very version. Bumping `app.version` instead lets the
badge tell the builds apart, but then install the new version (**Update to
latest** on your app's card) or have **Always use my latest version** on.
Wait for the green tick before testing again.

### A worked example

Before — published, installed, never used:

```yaml
outcomes:
  - id: tide.times
    summary: Tidal predictions service
    example_phrases:
      - tides
      - tide data today
```

After:

```yaml
outcomes:
  - id: tide.times
    summary: Say when the next high and low tide are at a named port
    example_phrases:
      - when is high tide at
      - what time is low tide
      - is the tide in or out at
      - when does the tide turn
      - how high is the tide at
      - next high tide for
      - tide times for
```

Two phrases became seven. The function-shaped summary became a sentence. The
word "today" went, because Pippa Diary owns it. That is usually the whole fix,
and Claude will do all of it if you say "my app is not being picked".

## The app is used, but it fails

**Symptom.** You can see the badge, or Pippa says the app could not do it. The
reply contains a short sentence such as:

```
I could not work out which date you meant.
```

or, less helpfully:

```
Something went wrong.
```

**What it means.** The app ran and raised. The important rule: **only
`user_message` is ever shown to a user.** The exception type, the message
passed to the constructor and the traceback all stay in the logs. So that
sentence is literally the `user_message` attribute of whatever was raised.

`Something went wrong.` is the default on `AgentAppError`. Seeing it means
either a bare `AgentAppError` with no `user_message`, or a plain Python
exception escaped — a `KeyError`, an `IndexError`, a JSON parse failure — and
was reported generically.

**The fix.** Tell Claude what you asked and what came back, word for word. It
will reproduce the case in a test and fix the handling. What good handling
looks like:

1. **Every failure gets a real sentence.**

   ```python
   class NoSuchPort(AgentAppError):
       user_message = "I could not find a port with that name."
       retryable = False
   ```

2. **Nothing catches everything and returns empty data.** An app that returns
   zeroes when it failed is worse than one that fails, because the user
   believes it.

3. **A service that is down or rate-limiting** has ready-made subclasses:
   `ServiceUnavailableError` ("That service could not be reached just now.")
   and `RateLimitedError` ("That service is busy. Please try again shortly.").
   Both are marked retryable.

4. **Something non-fatal** belongs in
   `Result(data={...}, warnings=("one source was unreachable",))` rather than
   failing the whole call.

## `Tide Times couldn't answer: I could not find a port with that name.`

**Symptom.** You started the message with `@` and picked your app. Instead of
an answer, Pippa replied with one sentence about it.

**What it means.** When somebody picks an app with `@`, Pippa does not choose
and does not fall back. She calls that app, and if it cannot answer she says
so, rather than answering from her own knowledge or trying another app. So the
sentence is a failure that an ordinary question would have hidden. The ones
you are likely to meet:

| Pippa says | What happened |
|---|---|
| `<App> couldn't answer: <a sentence>` | Your app raised. The sentence is its `user_message`. A generic one — `Something went wrong.` or `That app could not answer.` — means it raised without one, or a plain Python error escaped. `That app tried to do something it is not allowed to do.` is not yours: your app returned a result its manifest does not allow, and it was refused. See [`OutputShapeViolation`](#outputshapeviolation). |
| `<App> couldn't tell what you need from that message. Try something like: “<phrase>”.` | Your app was never called: a **required** input was missing, or an input — optional ones included — could not be read as the type your manifest declares (a time zone that does not exist, say). The suggestion is that outcome's first example phrase. |
| anything saying it **took too long** | Over the 20-second limit. See [The app times out](#the-app-times-out). |
| `<App> isn't installed`, `is switched off`, or `There's no app called … that you can use.` | Install it, or switch it on, on the Apps page. If it is not listed there, see [Who can see it](#who-can-see-it). |
| `That app changed while I was asking it. Ask again.` | The version that should answer changed while Pippa was asking it — a push while **Always use my latest version** is on, for example. Nothing is wrong with your app. Ask again. |
| `Apps aren't available right now`, or anything saying **on my side** | Pippa's side, not your app. Do not change the code. Try again, and tell an organiser if it lasts. |

**The fix.** Tell Claude what you asked and what came back, word for word, as
in [The app is used, but it fails](#the-app-is-used-but-it-fails). For the
second row, when a required input was missing, the better fix is usually to
make that input `required: false`. Then your app runs, notices the input is
missing, and the person gets your own sentence saying what to type instead of
a generic one.

If the same question works with `@` and fails without it, your app is fine and
the problem is routing: see
[My app published but Pippa never uses it](#my-app-published-but-pippa-never-uses-it).

**Your app reads `call.context.explicit` and it is never `True`?** Look at the
badge on the answer first. **picked by Pippa** means the message did not go to
your app by name: start it with `@` and pick the app from the list. **you
picked it** means the version that answered was published before the platform
update that added the flag, because each version keeps the SDK it was
published with. Picking it with `@` still works, but only a version published
after the update sees the flag: push (a draft can keep its version number; a
submitted version needs a new one), and once the build is green, make sure
the badge names the version you pushed.

## The app times out

**Symptom.** The user is told the app failed, and nothing in the code raised.

**What it means.** Twenty seconds is a hard limit. Past it the call is killed,
with no chance to tidy up or return a partial answer.

**The fix.** Tell Claude the app is timing out. The usual causes:

1. **A request with no timeout.** Without one, a slow server can hold the call
   far past twenty seconds.

   ```python
   with urllib.request.urlopen(request, timeout=5) as response:
       payload = json.load(response)
   ```

2. **Too many requests.** One or two is comfortable. A request per item in a
   list is not — take a slice.

3. **A slow public API.** Anything doing a geographic search over a large area
   can take many seconds on its own.

4. **Not failing honestly.** Catching the timeout and raising
   `ServiceUnavailableError` tells the user something true instead of leaving
   them waiting for the kill.

## `ImportError` or `ModuleNotFoundError` after the app is live

**Symptom.** The build was green, the tests passed, and every real call fails.
The error names a library:

```
ModuleNotFoundError: No module named 'requests'
```

**What it means.** Where the app runs, only three things are installed: the
Python 3.12 standard library, `pippa_agentapp_sdk` and `PyYAML`.

**The fix.** Tell Claude, which will swap the library for the standard library.

| Instead of | Use |
|---|---|
| `requests` | `urllib.request` plus `json` |
| `beautifulsoup4` | `html.parser`, or an API that returns JSON |
| `pandas` | lists, dicts, `statistics` |
| `numpy` | `math`, `statistics` |
| `python-dateutil` | `datetime.strptime`, `datetime.fromisoformat` |
| `pytz` | `zoneinfo` (standard library since 3.9) |
| `pyyaml` | already available |

A `requests` call becomes:

```python
import json
import urllib.request

request = urllib.request.Request(
    "https://api.frankfurter.app/latest?from=GBP&to=EUR",
    headers={"User-Agent": "pippa-hack-rates (hackathon project)"},
)
with urllib.request.urlopen(request, timeout=5) as response:
    data = json.load(response)
```

**Copying the library into the repository does not work.** The build refuses
wheel files, and a library large enough to matter would break the 3 MB limit
anyway.

## I pushed changes but the app did not update

Work through these in order.

**1. Did the build run?**
Open the Actions tab. If there is no run for the latest commit, the push did
not trigger one. The build runs on a push to `main` and nowhere else. Ask
Claude which branch it pushed to.

**2. Did the run go green?**
A red run means nothing was published: every version you had is untouched,
and so is the one you get. Open the run and read the failing step. A green run
whose summary says **Nothing to publish yet** published nothing either: the
app id is still the placeholder, or `app_author_name` is still empty.
See [`Nothing to publish yet`](#nothing-to-publish-yet).

**3. Does the run say "Cancelled"?**
A newer push cancels an older run that is still going. Look at the newest run.

**4. Is the version you get the one you pushed?**
The success banner names the version that was published:

```
  App      Tide Times  (hack.tide_times v0.2.0)
  Can do   tide.times
```

The badge on each answer names the version that answered. If it names a
different version from the banner, the version installed for you is not the
one you pushed: publishing a new version does not change it. On your app's
card under
**Created by me**, press **Update to latest**, or switch on **Always use my
latest version** so that every push is what you get.

Asking Claude to bump `app.version` with every meaningful change costs nothing
and makes this answerable at a glance — as long as you then get the new
version, as above.

**5. Did the file reach the package?**
Open the Publish step of the run and read the `Packaged N file(s)` list. It
names every file that was sent.

**6. Re-publish without a change.**
Actions tab, open the newest **Publish to Pippa** run, **Re-run jobs**,
**Re-run all jobs**; or ask Claude to push an empty commit
(`git commit --allow-empty -m "Publish again"`). Only a push to `main`
publishes, so there is no other button. Either way it publishes `main` again,
under the version number in `manifest.yaml`. So it works only while that version is a draft: a version you
have submitted is refused, like any other push of it.

**7. If the thing you changed was routing**, remember routing comes from the
manifest of the version you get. A change Claude made but did not push changes
nothing, and neither does a new version you have not installed (unless
**Always use my latest version** is on).

---

# How to ask for help

Come and find an organiser. Bring these four things, and the answer usually
takes under a minute:

1. **The repository name.** For example `pippa-hack-tide-times`.
2. **What you asked Pippa**, word for word. Copy and paste it; do not
   paraphrase, because the exact wording is often the problem.
3. **What Pippa said back**, word for word, including whether the reply carried
   a badge naming your app.
4. **A link to the Actions run.** Repository on GitHub, Actions tab, newest
   run, copy the address from the bar at the top.

Before you queue: paste the same four things into Claude Code and ask it to
look. It can open the build log, and it fixes most of this page without help.
