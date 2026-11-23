import random
import re
import sys
import threading
import time
import pyautogui
from pynput import keyboard

TEXT_FILE = "text.txt"                    # file with the text to type
PROGRESS_FILE = "autotype_progress.txt"   # remembers which session is next

TOTAL_MINUTES = 40       # total typing time across all sessions
SESSIONS = 1             # split the text into this many separate runs
START_DELAY = 10         # seconds to click into the doc before typing starts

PAUSE_KEY = "f8"         # press to pause, press again to resume
RESUME_DELAY = 5         # seconds to click back into the doc after resuming

TYPO_RATE = 0.02         # chance of a typo per letter (0 turns off)
THINK_RATE = 0.01        # chance of a longer "thinking" pause between words
BREAK_RATE = 0.05        # chance of a break after each sentence (0 turns off)
BREAK_MIN = 30           # shortest break, in seconds
BREAK_MAX = 90           # longest break, in seconds
FALSE_START_RATE = 0.01  # chance per word of typing a wrong word, then deleting it
REWORD_RATE = 0.08       # chance per sentence of deleting its last few words and retyping them
INSERT_RATE = 0.25       # chance per paragraph of going back to add a missed word

pyautogui.FAILSAFE = True  # slam the mouse into a screen corner to stop it
pyautogui.PAUSE = 0        # pyautogui otherwise adds 0.1 s after every keypress

# Characters pyautogui can't type, swapped for plain equivalents
REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2014": "--", "\u2013": "-", "\u2026": "...", "\u00a0": " ",
}

# Neighboring keys on a QWERTY keyboard, used for realistic typos
NEIGHBORS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh",
    "u": "yij", "i": "uok", "o": "ipl", "p": "ol", "a": "qsz", "s": "awdz",
    "d": "sefx", "f": "drgc", "g": "fthv", "h": "gyjb", "j": "hukn",
    "k": "jilm", "l": "kop", "z": "asx", "x": "zsdc", "c": "xdfv",
    "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}


def clean(text):
    for fancy, plain in REPLACEMENTS.items():
        text = text.replace(fancy, plain)
    leftovers = sorted({ch for ch in text if ord(ch) > 127})
    if leftovers:
        print("Warning: these characters may not type correctly:", " ".join(leftovers))
    return text


def split_sessions(text, n):
    """Split the text into n roughly equal chunks at paragraph boundaries."""
    paras = text.split("\n")
    target = len(text) / max(n, 1)
    chunks, current, size = [], [], 0
    for p in paras:
        current.append(p)
        size += len(p) + 1
        if size >= target and len(chunks) < n - 1:
            chunks.append(current)
            current, size = [], 0
    if current:
        chunks.append(current)
    return ["\n".join(c) for c in chunks]


def plan(text, vocab):
    """Build a list of (kind, arg, weight). Weights are scaled later to fit the
    time; 'break' entries are real seconds."""
    actions = []
    state = {"pace": 1.0}  # drifts up and down to create bursts and slow stretches

    def gap(prev):
        state["pace"] = min(max(state["pace"] + random.uniform(-0.05, 0.05), 0.6), 1.6)
        w = random.lognormvariate(0, 0.35) * state["pace"]
        if prev in ".!?":
            w *= random.uniform(4, 8)        # pause after a sentence
            if random.random() < BREAK_RATE:
                actions.append(("break", None, random.uniform(BREAK_MIN, BREAK_MAX)))
        elif prev in ",;:":
            w *= random.uniform(2, 3.5)      # shorter pause after a clause
        elif prev == "\n":
            w *= random.uniform(10, 25)      # long pause before a new paragraph
        elif prev == " ":
            w *= random.uniform(1.1, 1.6)    # slight gap between words
            if random.random() < THINK_RATE:
                w += random.uniform(15, 40)  # occasional stop to think
        return w

    def type_char(ch, w):
        if ch.lower() in NEIGHBORS and random.random() < TYPO_RATE:
            wrong = random.choice(NEIGHBORS[ch.lower()])
            if ch.isupper():
                wrong = wrong.upper()
            actions.append(("char", wrong, w))
            actions.append(("key", "backspace", random.uniform(2, 5)))  # notice it
            actions.append(("char", ch, random.uniform(0.8, 1.5)))       # fix it
        else:
            actions.append(("char", ch, w))

    def delete(n, first_pause):
        actions.append(("key", "backspace", first_pause))
        for _ in range(n - 1):
            actions.append(("key", "backspace", random.uniform(0.15, 0.4)))

    prev = "a"
    for p_index, para in enumerate(text.split("\n")):
        if p_index > 0:
            actions.append(("char", "\n", gap(prev)))
            prev = "\n"

        tokens = re.findall(r"\S+|\s+", para)
        words = [i for i, t in enumerate(tokens) if not t.isspace()]

        # Maybe leave out one word now and go back to add it at the end of the paragraph
        skip = None
        if len(words) >= 8 and random.random() < INSERT_RATE:
            options = [i for i in words[1:-1] if i + 1 < len(tokens) and tokens[i + 1] == " "]
            if options:
                skip = random.choice(options)

        typed = ""       # this paragraph as it currently appears on screen
        skip_pos = None
        for i, tok in enumerate(tokens):
            if i == skip:
                skip_pos = len(typed)
                continue
            if skip is not None and i == skip + 1:
                continue  # the space after the skipped word

            # False start: type a different word, then delete it
            if not tok.isspace() and prev == " " and vocab and random.random() < FALSE_START_RATE:
                wrong = random.choice(vocab)
                if tok[0].isupper():
                    wrong = wrong.capitalize()
                for j, ch in enumerate(wrong):
                    actions.append(("char", ch, gap(prev) if j == 0 else random.lognormvariate(0, 0.35)))
                delete(len(wrong), random.uniform(2, 5))
                prev = "x"

            for ch in tok:
                type_char(ch, gap(prev))
                typed += ch
                prev = ch

            # Reword: delete the end of the sentence just written and retype it
            if not tok.isspace() and tok[-1] in ".!?" and random.random() < REWORD_RATE:
                parts = re.findall(r"\S+|\s+", typed)
                k = random.randint(2, 4)
                tail = "".join(parts[-(2 * k - 1):])
                if len(tail) < len(typed):
                    delete(len(tail), random.uniform(4, 10))
                    for j, ch in enumerate(tail):
                        w = random.uniform(3, 8) if j == 0 else random.lognormvariate(0, 0.35)
                        actions.append(("char", ch, w))

        # Go back and add the missed word, then return to the end of the document
        if skip_pos is not None:
            actions.append(("left", len(typed) - skip_pos, random.uniform(5, 15)))
            for ch in tokens[skip] + " ":
                type_char(ch, random.lognormvariate(0, 0.35))
            actions.append(("end", None, random.uniform(1, 3)))

    return actions


def go_to_end():
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "down")
    else:
        pyautogui.hotkey("ctrl", "end")


def run_action(kind, arg):
    if kind == "char":
        if arg == "\n":
            pyautogui.press("enter")
        elif arg == "\t":
            pyautogui.press("tab")
        else:
            pyautogui.write(arg)
    elif kind == "key":
        pyautogui.press(arg)
    elif kind == "left":
        pyautogui.press("left", presses=arg, interval=0.01)
    elif kind == "end":
        go_to_end()


# ---- Pause / resume ----
pause_requested = threading.Event()
run = {"start": 0.0, "in_insert": False}


def on_key(key):
    if key == getattr(keyboard.Key, PAUSE_KEY, None):
        if pause_requested.is_set():
            pause_requested.clear()
        else:
            pause_requested.set()
            if run["in_insert"]:
                print("Pausing as soon as the current edit finishes...")


def do_pause():
    paused_at = time.perf_counter()
    print(f"Paused. Press {PAUSE_KEY.upper()} to resume.")
    while pause_requested.is_set():
        time.sleep(0.1)
    for i in range(RESUME_DELAY, 0, -1):
        print(f"Resuming in {i}... click into your doc now")
        time.sleep(1)
    go_to_end()  # put the cursor back at the end, wherever you clicked
    run["start"] += time.perf_counter() - paused_at  # don't count paused time
    print("Resumed.")


def wait_until(target):
    while True:
        # Never pause halfway through going back to insert a word
        if pause_requested.is_set() and not run["in_insert"]:
            do_pause()
        remaining = run["start"] + target - time.perf_counter()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 0.1))


# ---- Load text and pick this run's session ----
with open(TEXT_FILE, encoding="utf-8") as f:
    text = clean(f.read())
if not text.strip():
    raise SystemExit(f"{TEXT_FILE} is empty.")

chunks = split_sessions(text, SESSIONS)
session = 0
if len(chunks) > 1:
    try:
        with open(PROGRESS_FILE) as f:
            session = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        session = 0
    if session >= len(chunks):
        raise SystemExit(f"All sessions are done. Delete {PROGRESS_FILE} to start over.")

chunk = chunks[session]
if session > 0:
    chunk = "\n" + chunk  # start a new paragraph after the previous session
minutes = TOTAL_MINUTES * len(chunk) / len(text)

vocab = sorted({w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)})
actions = plan(chunk, vocab)

total_seconds = minutes * 60
break_seconds = sum(w for k, _, w in actions if k == "break")
typing_weight = sum(w for k, _, w in actions if k != "break")
if break_seconds >= total_seconds * 0.8:
    raise SystemExit("Breaks would take up too much of the time. "
                     "Lower BREAK_RATE or raise TOTAL_MINUTES.")
scale = (total_seconds - break_seconds) / typing_weight

num_breaks = sum(1 for k, _, _ in actions if k == "break")
if len(chunks) > 1:
    print(f"Session {session + 1} of {len(chunks)}.")
print(f"Typing {len(chunk)} characters over about {minutes:.0f} min, "
      f"with {num_breaks} breaks ({break_seconds / 60:.1f} min total).")
print(f"Press {PAUSE_KEY.upper()} at any time to pause or resume.")

listener = keyboard.Listener(on_press=on_key)
listener.daemon = True
listener.start()

for i in range(START_DELAY, 0, -1):
    print(f"Starting in {i}... click at the END of your doc now")
    time.sleep(1)

# ---- Type it ----
run["start"] = time.perf_counter()
elapsed_target = 0
next_report = 0.1
for n, (kind, arg, w) in enumerate(actions, 1):
    if kind == "break":
        print(f"Taking a {w:.0f}s break")
        elapsed_target += w
        continue
    elapsed_target += w * scale
    wait_until(elapsed_target)
    run_action(kind, arg)
    if kind == "left":
        run["in_insert"] = True
    elif kind == "end":
        run["in_insert"] = False
    if n / len(actions) >= next_report:
        print(f"{int(next_report * 100)}% done")
        next_report += 0.1

if len(chunks) > 1:
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(session + 1))
    left = len(chunks) - session - 1
    print(f"Session done. {left} session(s) left." if left else "All sessions done.")
else:
    print("Done.")
