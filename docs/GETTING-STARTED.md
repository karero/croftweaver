# Getting started — the gentle version

Never opened a terminal? Never installed a developer tool? **You're in the right place.**
This page walks you through your very first website with website-builder, in plain
language. You won't need to understand the whole toolchain — your AI assistant handles the
technical parts and explains each step as it goes.

If you get stuck at any point, you can always type **"what does this do?"** or **"I'm
confused, can you explain that more simply?"** to your assistant. That's allowed, and it
works.

🇩🇪 You can also do this entire journey in German (or any language): write to your
assistant in your language and it answers in it — the copy-paste prompt below works the
same, or add "Bitte auf Deutsch." after it.

---

## What you need first

Just three things to begin:

1. **An AI coding assistant.** Pick one:
   - **Claude Code** (recommended) — see the [setup guide](https://code.claude.com/docs/en/setup).
   - **OpenAI Codex** or **Google Antigravity** also work.
2. **A GitHub account** (free) — this is where your website's files will live safely.
   You'll make one at [github.com](https://github.com) if you don't have it; your assistant
   will point you there when it's time. The account and the website in it are **yours**, so
   we recommend protecting them: turn on two-factor sign-in and add a **passkey** (you then
   sign in with your fingerprint, face or phone, and a stolen password alone is not enough to
   get in). It's optional unless GitHub itself asks you for it.
3. **Your computer.** macOS, Linux, or Windows are all fine.

You do **not** need to install anything else right now. Tools like Node, git, or image
helpers get installed later — only if and when your site actually needs them, and your
assistant will offer to do it for you.

A **Cloudflare account** (also free) comes up later, when you're ready to publish your site
to the internet. You don't need it on day one. It's yours as well, so we'll recommend
protecting it the same way, with two-factor sign-in (your fingerprint or face unlock works).

---

## Step by step

### 1. Choose a home for your websites

Your website will live in a folder on your computer — a container for its files, like the
folders you already know. We suggest one called **Websites**, inside your **Documents**
folder. You can open Documents from your computer's file manager (Finder on a Mac, File
Explorer on Windows), so your site stays easy to find. If you already have a folder where
you keep your projects, use that one instead — it's yours to choose.

If your Documents folder syncs to iCloud or OneDrive, pick a folder outside it, for example
a Websites folder in your home folder (the one with your name on it). Your site's files are
backed up on GitHub, in your own account — you set that up with your assistant — so you
don't need iCloud or OneDrive for that. That backup only protects you when GitHub is
properly synced: before you stop for the day, ask your assistant to make sure GitHub has
your latest work.

This folder can hold as many websites as you like: each new site gets its own folder inside
it, so it doesn't need to be empty. Please don't use Downloads — things get lost there.

Don't have it yet? Make a new folder called **Websites** in the place you chose above.
(Stuck? Start your assistant as in step 2 and ask it to make the folder for you.)

### 2. Open your AI assistant in your websites folder

Start the assistant you installed (for example, Claude Code) and have it work in the folder
you chose in step 1. If you use an app, choose that folder as the one to work in. If you
use a terminal, go to the folder first and start the assistant from there. Not sure how?
Start it anywhere and ask: *"How do I open you in my websites folder?"*

You'll get a chat box where you type to it in normal language — like texting a
knowledgeable friend.

### 3. Paste the starter prompt

Copy this into the chat and send it:

> I want to use the website-builder skill suite (https://github.com/karero/website-builder)
> to create a new website. Please guide me step by step in plain language.
> First, check which required tools this computer already has.
> Explain every command before you run it, and install missing tools only when they're
> actually needed. Then install the website-builder skills. My websites live in one
> folder: check which folder you're open in and ask me whether that's it; if not, ask me
> which one it is (suggest Documents/Websites unless I already keep my projects somewhere
> else, or my Documents folder syncs to iCloud or OneDrive — then suggest a Websites
> folder in my home folder). Tell me when to restart or reopen you in that folder so the
> skills load, then start `new website` there. When the site has its own folder, tell me
> where it is on my computer (its full path).

The assistant will take it from there: it checks what's on your computer, installs the
website-builder skills, and asks your approval before doing anything that changes your
system. If it asks whether the folder it's in is your websites folder, say yes only if
it's the one you chose in step 1; otherwise tell it which folder to use. If you land in an
empty chat after it restarts, type `new website`.

### 4. Answer its questions

Once it runs **`new website`**, the assistant interviews you about the site you want. These
are *decisions*, not commands — things like:

- What is this website for? Who is it for?
- What should it be called?
- Roughly what pages do you want?
Later, once it has worked out with you what you offer and for whom, it asks one optional
question: whether you want the home page told as a story, with your visitor as the hero.
It explains the idea first and asks only once.

Answer in your own words. There are no wrong answers, and you can change your mind.

### 5. Let it build

From your answers, the assistant creates the site, drafts the pages, adds the behind-the-
scenes things that make a site fast and findable (SEO, accessibility checks, structured
data), and runs its own quality tests. It'll show you what it made and help you adjust.

**Where your site lives.** Your site gets its own folder inside the folder you chose in
step 1. To see where it is on your computer, ask the assistant: *"Show me where my
website's folder is."* Next time you want to work on that site, open your assistant in the
site's own folder.

### 6. Publish when you're ready

When the site looks good, the assistant helps you put it online (this is where the free
Cloudflare account comes in). Again — it walks you through it.

---

## A few reassurances

- **Nothing happens without your say-so.** The assistant asks before installing anything or
  making changes.
- **You can stop and ask anytime.** "Slow down", "explain that", "what just happened" all
  work.
- **You own everything.** The website's code, its repository, and its domain are yours —
  this isn't a rented platform you can be locked out of.

---

## Want the technical details?

If you're comfortable with a terminal, or you're curious what the assistant is actually
running under the hood, see the **[Manual install & technical reference](../README.md#manual-install--technical-reference)**
section of the README — every exact command is listed there.
