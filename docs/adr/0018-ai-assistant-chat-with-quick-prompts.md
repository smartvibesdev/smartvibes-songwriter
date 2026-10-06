# 0018. AI assistant: chat with quick prompts, on every page

- Status: Proposed (the model choice and some details are still open, see "Open questions")
- Date: 2026-10-06

## Context

So far AI is one panel on the song page: pick title, lyrics or fragment, add an optional seed, press
Generate (ADR 0015). The owner wants AI to be front and center: a place to ask for help with
standard songwriting jobs and have the AI change the song for you, the way Alexa works on an Amazon
product page (a chat that knows what page you are on, with suggested questions to start from).

Answers from the owner (2026-10-06):

1. **Both quick prompts and free chat.** Canned prompts for common jobs, plus a box to type anything.
2. **On every page**, not only the song page. On a phone it could be the bottom 30 to 40 percent of
   the screen. The exact layout is not decided.
3. **Apply edits directly, if the editor can undo them.** It can: the lyrics editor (CodeMirror 6)
   has undo and redo on Cmd/Ctrl+Z, and edits made by code go into the same undo history unless
   they ask not to. So the AI may change the lyrics straight away, and the user presses Undo to
   get back.
4. **Model: not decided yet.**

Related decisions: every AI call goes through the token checkpoint (plan section 6, ADR 0015).
The rhyme, synonym and antonym tools are dictionary lookups on the backend, with no AI (ADR 0016
and 0017), and they stay on the backend.

## Options considered

Where the assistant lives:

- **A panel only on the song page** (today). Simple, but it cannot help on Home and is easy to miss.
- **A launcher button at the bottom right that opens a chat on every page (leading option).** It
  is part of the app shell, so it is always reachable, and the conversation survives moving between
  pages. On desktop it opens as a side drawer, so the song stays visible; on phones it opens as a
  bottom sheet that takes about 40 percent of the screen and can be dragged to full height.
- **A permanent docked column.** Always visible, but it takes space from the lyrics editor.

How the AI changes the song:

- **The AI returns text and the user copies it in.** Safe, but slow and not the experience wanted.
- **The AI returns structured edits and the page applies them (leading option).** Claude's
  tool-use feature returns calls such as "replace lines 5 to 8 with this text" or "insert after
  line 12". The backend passes them to the browser, and the browser applies them to the editor.
  The edit goes through the editor's normal change mechanism, so Cmd/Ctrl+Z undoes it. The
  browser, not the backend, applies edits because the live text and the undo history are in the
  editor, and unsaved changes would be lost if the backend edited the saved song.
- **The backend edits the saved song directly.** Not undoable, and it fights with unsaved typing.
  Rejected.

## Decision (so far)

- **One assistant in the app shell**, with a launcher at the bottom right. Its conversation and
  open or closed state live in the shared app state (ADR 0013), so it survives page changes.
- **Quick prompts plus chat.** Above the message box, suggested prompts change with the page.
  On the song page, for example: write or improve an intro, verse, chorus, bridge or outro;
  review the song (tense, point of view, clichés, imagery); suggest a title; find a rhyme,
  synonym or antonym; give me a new word or phrase for this line. On Home: find fragments about a
  theme, turn a fragment into a verse.
- **Each page tells the assistant what it can see and do.** The song page offers the song's title,
  lyrics, selected text and tags, and the ability to edit them. Home offers search results and
  saving a fragment. A page that offers nothing gets a plain chat.
- **Tools the AI may call** (all checked on the backend, the AI never touches the database
  directly): edit the lyrics or title (applied by the page, undoable); look up rhymes, synonyms or
  antonyms (the free dictionary tools, so word questions cost no tokens for the lookup itself);
  search the user's fragments; save a fragment (tagged `ai`).
- **Edits apply straight away and are announced** in the chat ("Changed lines 5 to 8", with an
  Undo button next to the message that also works with Cmd/Ctrl+Z). Undo is available only while
  the song page is open; after Save and a page change, the saved version is the record.
- **The song is sent with each message**, not stored on the backend. The conversation is kept in
  the browser for the session and is not saved to the database in this version.
- **Every turn passes through the token checkpoint** (reserve, call, reconcile). Because a chat
  resends earlier turns, the backend limits the history it sends (the last several turns), caps the
  song text it includes, and caps each reply, so the cost of one message stays bounded. The
  per-user and global daily budgets from ADR 0015 still apply. Cached prompt prefixes (Claude's
  prompt caching) are worth testing to cut the cost of resending the song.
- **Model and temperature**: see below.

## Open questions

1. **Model.** Sonnet 4.6 is the current model for generation. Chat sends more tokens per message, so a
   cheaper model (Haiku 4.5) for quick prompts and Sonnet for drafting and review is possible. The
   owner will decide once the details are worked out. Nothing is changed until then.
2. **Phone layout.** A bottom sheet of 30 to 40 percent leaves little room for the editor and the
   on-screen keyboard. Needs a mock-up before building.
3. **Saving conversations.** Not saved in this version. Saving them would need a table and a
   privacy decision.
4. **Applying edits on pages other than the song editor.** For now, on Home the assistant does not
   change saved songs; it can search and create fragments, and for edits to a song it offers to open it.
5. **The wildness dial.** It controls creativity in the Generate panel. Whether chat keeps it, uses
   a fixed setting per quick prompt, or drops it is undecided.

## Consequences

- AI becomes the main way into writing help, and the Generate panel's jobs move into the assistant
  (its title, lyrics and fragment kinds become quick prompts). The dictionary tools stay free and
  are used by the assistant and the rhyme panel alike.
- It needs new backend work: a chat route, tool-use handling and the history limits above.
- It needs new frontend work: the shell launcher and drawer, per-page context, and an edit
  applier that works through the editor's undo history.
- Token costs rise (longer prompts and several turns), so the budgets and the meter need a second
  look once real usage is seen.
- Build in small steps, one branch each: (1) the shell drawer with quick prompts that call the
  existing generation route; (2) chat with history and the token checkpoint; (3) tool use with
  direct edits and Undo; (4) saving conversations, only if wanted.
