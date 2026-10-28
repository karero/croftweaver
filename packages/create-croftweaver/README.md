# create-croftweaver

Installs the [Croftweaver](https://croftweaver.com) website skills for your AI coding
assistant with one command:

```bash
npm create croftweaver
```

It downloads the latest Croftweaver release from GitHub and copies its skills into the
folder your assistant reads them from. Then restart your assistant, open it in your websites
folder, and say `new website`.

To update, run the same command again.

You need [Node](https://nodejs.org) 22.12 or newer and an internet connection. It runs on
macOS, Linux and Windows, in any terminal. Building a site needs a recent security release of
Node, which the setup guide that comes with the skills names.

## Which assistant

| Assistant | Command | Where the skills go |
|---|---|---|
| Claude Code | `npm create croftweaver` | `~/.claude/skills` |
| Codex | `npm create croftweaver -- --codex` | `~/.agents/skills` |
| Antigravity | `npm create croftweaver -- --antigravity` | `~/.gemini/config/skills` |

## What happens to what is already there

- **Skills this command installed before** are replaced by the new release. It knows them by
  their folder names, which it keeps in `.croftweaver.json`, not by their contents. So change
  a skill in the toolkit, not in that folder: the next run overwrites an edit, and it also
  replaces a folder of your own that you put there under the same name.
- **A skill that is a link to another folder**, which is what the toolkit's own
  `scripts/install.sh` sets up, is left alone. It updates from that folder. Add `--force`
  (`npm create croftweaver -- --force`) to replace each link with a copy; the other folder
  is not touched.
- **Any other folder that has the name of a Croftweaver skill** is moved to a
  `skills-before-croftweaver-…` folder next to the skills folder. The command tells you
  where it went.
- **A skill Croftweaver no longer has** is removed, if this command installed it. The same
  holds here: a folder of your own under that name goes with it.

Before it unpacks anything, it checks the download against the `SHA256SUMS` file that each
release carries beside the zip. If the two don't match, or the release has no such file
(Croftweaver 0.31 and older), it installs nothing and says why.

If the download fails or cannot be read, the command says why and changes nothing.

If the command is killed before it finishes, a folder named
`.croftweaver-staging-…` can stay in the skills folder. Delete it once no install is
running.
