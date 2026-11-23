# autotype

Types the contents of a text file into any window, one keystroke at a time, with a human-like rhythm: varied speed, natural pauses, typos that get corrected, rewording, and going back to add missed words. The whole run fits a time you choose, and it can be paused, resumed, or split across several sessions.

## Features

**Typing rhythm**
- Variable speed with a drifting pace, so there are fast bursts and slower stretches
- Natural pauses: short between words, longer after commas, sentences and paragraphs
- Occasional longer "thinking" pauses between words
- Random 30–90 second breaks between sentences

**Mistakes and revisions**
- Typos on neighboring keys, noticed and corrected with backspace
- False starts: a wrong word typed and deleted before the right one
- Rewording: the end of a sentence deleted and retyped
- Going back mid-paragraph to insert a word that was left out

**Control**
- Total run time scaled to fit `TOTAL_MINUTES`, including breaks
- Split the text into multiple sessions that resume where they left off
- Pause and resume at any time with F8
- Failsafe: slam the mouse into a screen corner to stop immediately
- Progress updates in the terminal

## Setup

1. Install Python 3 from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** in the installer.
2. Install the dependencies from the repo folder:
   ```
   pip install -r requirements.txt
   ```
   On a Mac, use `pip3` if `pip` isn't found.
3. **Mac only:** in System Settings → Privacy & Security, allow Terminal under both **Accessibility** (so it can type) and **Input Monitoring** (so it can detect the pause key).

## Usage

1. Put your text in a file named `text.txt` in the repo folder. `example.txt` is a sample to test with.
2. Open the target document. In Google Docs, go to Tools → Preferences and turn off automatic lists, smart quotes, auto-capitalization and substitutions.
3. Make sure your computer won't sleep or lock during the run.
4. Run the script:
   ```
   python autotype.py
   ```
   On a Mac, use `python3`.
5. During the countdown, click at the **end** of the document (an empty doc is easiest).
6. Leave the keyboard and mouse alone until it finishes, or pause it.

**Tip:** do a test run first with a few lines of text and `TOTAL_MINUTES = 1`.

## Pausing and resuming

- Press **F8** to pause. You can use your computer normally while it's paused.
- Press **F8** again to resume. You get a few seconds to click back into the doc, then it jumps the cursor to the end of the document and carries on.
- Paused time doesn't count toward the total.
- If you pause while it's going back to insert a word, it finishes that edit first.
- On a Mac, F8 is usually the media play/pause key, so press **fn + F8**, or change `PAUSE_KEY`.

## Sessions

Set `SESSIONS` to more than 1 to split the text into parts at paragraph breaks. Each run types the next part, and progress is saved in `autotype_progress.txt`. `TOTAL_MINUTES` is the total across all sessions.

Don't edit `text.txt` or change `SESSIONS` partway through a multi-session job. To start over, delete `autotype_progress.txt`.

## Settings

All settings are at the top of `autotype.py`. Any rate set to `0` turns that feature off.

| Setting | What it controls | Default |
|---|---|---|
| `TEXT_FILE` | File to type from | `text.txt` |
| `TOTAL_MINUTES` | Total time across all sessions | `40` |
| `SESSIONS` | Number of separate runs | `1` |
| `START_DELAY` | Countdown before typing starts (seconds) | `10` |
| `PAUSE_KEY` | Key that pauses and resumes | `f8` |
| `RESUME_DELAY` | Seconds to click back in after resuming | `5` |
| `TYPO_RATE` | Chance of a typo per letter | `0.02` |
| `THINK_RATE` | Chance of a thinking pause between words | `0.01` |
| `BREAK_RATE` | Chance of a break after each sentence | `0.05` |
| `BREAK_MIN` / `BREAK_MAX` | Break length range (seconds) | `30` / `90` |
| `FALSE_START_RATE` | Chance of a false start per word | `0.01` |
| `REWORD_RATE` | Chance of rewording per sentence | `0.08` |
| `INSERT_RATE` | Chance per paragraph of going back to add a word | `0.25` |

## Troubleshooting

- **Nothing types (Mac):** allow Terminal under Accessibility.
- **F8 does nothing:** on a Mac, allow Terminal under Input Monitoring and press fn + F8.
- **"pip" or "python" not found:** try `pip3` and `python3`, or reinstall Python with "Add to PATH" ticked.
- **Text lands in the wrong place:** something stole focus, or the cursor wasn't at the end of the doc. Stop it, fix the text and start again.
- **Lists, quotes or words come out wrong:** turn off Google Docs' autoformatting and substitutions.
- **Warning about characters:** those symbols may not type correctly. Replace them in `text.txt`.
