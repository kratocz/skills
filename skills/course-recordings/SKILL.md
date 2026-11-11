---
name: course-recordings
description: "Turn the lesson recordings of an online course into a private, searchable study set: download every lesson from its HLS stream, shrink each under NotebookLM's 200 MB source limit without losing on-screen text, transcribe with whisper, merge an external transcript's better text (Plaud) with whisper's timing into readable subtitles embedded in the small MP4s, find where each lecture ends and Q&A begins, and write per-lesson summaries with no participant names — all under one naming convention (variant before the lesson number, lesson date after it), long jobs detached with a log, outputs sorted by source. Use when the user says \"stáhni lekce kurzu\", \"zpracuj nahrávky kurzu\", \"zmenši lekce pro NotebookLM\", \"udělej titulky k lekcím\", \"kde v lekci začínají dotazy\", \"udělej souhrny lekcí\", \"download the course lessons\", \"make the lessons fit NotebookLM\", \"summarize every lesson\". Not syncing finished films to a NAS or cloud, and not offloading camera cards."
license: MIT
---

# course-recordings — procedure

Every step below was run end to end on one course of eleven 2–5 h lessons (4K screen recordings of a live webinar, Czech) in November 2026; the numbers quoted are from that run. Each stage is resumable: batches skip what is done, so an interruption costs at most the lesson in progress.

## 0. Before anything: whose recordings these are

Course recordings belong to the organiser and the lecturer. Proceed only when the user states they may keep a copy (their own enrolment, the lecturer's consent). Mark the sharing status in the course README (`Sharing: no`) and put `do not share` into every file name, so a file that leaves the folder still says what it is. Never upload, publish or share any of it yourself; when the user wants others to query the material (a shared NotebookLM notebook, say), point out that the organiser and the lecturer have to agree first, and prefer sharing with named people over a public link.

## 1. Folder layout and names

One directory per course, e.g. `~/Movies/courses/<organiser>/<year - course name>/`:

- **Root = inputs and tooling:** the list of stream URLs (`links.txt`: lesson number, tab, URL), the programme as text and as the screenshot it came from (it carries the lesson dates), any course-wide documents from the LMS (a study guide), the batch scripts with their logs, a shared `lessons.sh` (below), `qa-times.md` and a `README.md` recording how everything was made and why.
- **`output/` = everything derived, one subfolder per source:** `videa z LMS` (full videos plus the final `.srt` beside each, so players load it automatically), `pouze audio`, the small versions, `whisper - titulky`, `plaud - transkript`, `plaud - souhrn`, `claude - souhrn`, `prezentace z LMS`, … Name folders by origin so nobody mistakes one tool's output for another's.

File names follow `course - <organiser> - <year - name> - [<variant> - ]lesson NN - <YYYY-MM-DD> - do not share.<ext>`. The variant (`only audio`, `small`, `summary`, `plaud transcript`, `whisper subtitles`, `slides`) stands **before** the lesson number so each variant sorts as one contiguous block and gaps show what is missing; the lesson date stands **after** it so it does not change the order. Take dates from the programme, number lessons from `00`, and keep the name-building in one sourced file the batches share:

```bash
# lessons.sh — sourced by every batch
LESSON_DATES=(2026-01-05 2026-01-07 …)          # index = lesson number
lesson_name() {  # <variant|""> <NN> <ext>
    local v=""; [ -n "$1" ] && v="$1 - "
    printf '%s - %slesson %s - %s - do not share.%s' "$P" "$v" "$2" "${LESSON_DATES[10#$2]}" "$3"
}
```

When the user reorganises the folder by hand, re-derive every path in the batches from `lessons.sh` and prove it: a check that every expected file exists for every lesson (44 of 44, not "looks fine"). A batch that cannot find its outputs will happily redo hours of work.

## 2. Long jobs run detached, with a log

Downloading takes minutes per lesson, shrinking takes hours. Run each stage as a batch the user starts outside the agent session: `nohup caffeinate -i bash <batch>.sh >> <batch>.log 2>&1 &`. A batch loops over the lessons, skips any whose output already exists and is valid, waits for a lesson the download batch has not fetched yet, and logs one `== <time> lesson NN …` line per event so a status check is a `grep '^=='`. A terminal pane's scrollback is not a log: `ffmpeg` progress fills it in minutes.

## 3. Download

The tools used here are `download-lesson` and `shrink-video-to-size` from `kratocz/krato-macbook-core` (`macos/bin/`), with their full documentation in that repository's `AGENTS.md`; any equivalent works. A Wistia lesson is one HLS stream (`…/deliveries/<hash>.m3u8`) holding picture and sound: stream-copy it (no re-encode), map `0:v:0` and `0:a:0` explicitly because the stream also carries a `timed_id3` data track, and split the audio off locally as the `only audio` variant. Check free space before each lesson.

## 4. Shrink under the NotebookLM limit

NotebookLM accepts sources up to 200 MB; target 190 MB decimal, because it is not known whether the limit is decimal or binary. For 4K screen recordings:

- **Downscale to 1080p** (`-H 1080`). At ~90 kb/s 4K turned small text into mush and encoded 3× slower; 1080p stayed sharp. For a lesson so long that the video gets ~50 kb/s, 720p kept thin lines that 1080p lost.
- **Re-encode audio to HE-AAC mono 32 kb/s** (`-a 32`). Lectures run up to ~5 h and the original AAC 128 kb/s alone would exceed the limit. A whisper transcript of 32 kb/s audio matched the original's; 24 kb/s started to make phonetic errors. The full-quality audio stays in `only audio`.
- **Two-pass x265 ABR** with the video bitrate computed from the real audio size and the container overhead; retry with less video bitrate when the result overshoots.
- **Disk:** the first pass writes 1.6–2.6 GB of statistics per lesson and the encoder's memory pressure grows swap on the same volume. Keep ~20 GB free. When the disk fills completely, an agent harness that stores command output in a temp directory cannot run any command at all; only the user can free space.

Verify every small file: size under the target, audio profile `HE-AAC`, duration equal to the original's.

## 5. Transcribe with whisper

`whisper-cli` (whisper.cpp) with `large-v3-turbo`, language set explicitly, on the `only audio` file converted to 16 kHz mono WAV, output `.srt`. **VAD is mandatory** (`--vad` with the Silero model): without it whisper invents text on silence (a test ended with "titulky vytvořil johnyx"). It ran ~16× faster than real time.

## 6. An external transcript (Plaud), if the user has one

A Plaud transcript of the same audio was more accurate than whisper's in text: product names right ("LangGraph" 42× against 3×, whisper wrote "Langref"), speakers separated, sensible punctuation. But its segments last ~20 s, too long for subtitles, while whisper's cues last 1–2 s. Plaud also hallucinates on silence ("Titulky vytvořil…", "JohnyX", "www.hradeckralove.org"); strip those everywhere they appear. When the user drops Plaud exports into the folder:

- rename them into the convention (Plaud's own file names carry a generated, often garbled title and put the lesson number in varying places, so they do not sort);
- in exported summaries, replace the empty `[image]` placeholder with a link to the matching overview image and add a heading; Plaud's `MM-DD` in titles is the upload date, not the lesson date — use the programme's date.

## 7. Subtitles: external text, whisper timing

Align the two transcripts word by word and give each Plaud word whisper's time (`align-subtitles <whisper.srt> <plaud.srt> <out.srt>` from the same repository). What made the result good, each found by looking at real output:

- match per Plaud segment within a ±8 s window; **do not accept a lone short word** ("to", "tak") as a match — such matches jumped to the wrong place and produced zero-length cues in multi-speaker discussion;
- interpolate unmatched words between matched neighbours inside their segment; 88–92 % of words matched;
- cues of at most ~7 s and 2 lines of ~42 characters; never end a cue or a line with a one-letter Czech preposition or conjunction (`v s z k a i o u`) — move it to the next cue;
- lowercase words Plaud capitalises mid-sentence when the same word appears lowercase elsewhere; start a new speaker's turn with a dash.

Show the user one lesson's file before generating the rest. Then embed the result into each small MP4 as a soft, switchable track without re-encoding — `ffmpeg -nostdin -i small.mp4 -i sub.srt -map 0:v -map 0:a -map 1:0 -c copy -c:s mov_text -metadata:s:s:0 language=ces -disposition:s:0 default -movflags +faststart tmp.mp4` — and replace the original only after checking the temporary file: same duration, streams `video audio subtitle`, size under 200 MB, and the number of cues read back from the MP4 equal to the `.srt`. Burning subtitles into the picture would cost hours of encoding and blur the text at these bitrates. **`ffprobe` does not know `-nostdin`** (only `ffmpeg` does): it prints nothing and exits with an error, so a check reading its output compares empty strings — give `ffprobe` `< /dev/null` instead, and make the check fail on empty values.

## 8. Where the lecture ends and Q&A begins

Questions are asked throughout a lecture, so keywords do not find the boundary. Compact each transcript to one line per ~20 s prefixed with `H:MM:SS` (70–190 KiB per lesson — small enough for a subagent to read whole) and give one subagent (mid tier) per lesson the task: the time after the homework and organisational part where the session turns to open questions, the quote that marks it, a confidence level, and any contested boundary. Collect the result in `qa-times.md`: one table row per lesson (time, quote, confidence), then a section on contested boundaries. Precision is the compacting step, about ±20 s. Note lessons whose content differs from the programme; it happens.

## 9. Summaries without participant names

Build the input so names cannot leak: one line per segment, `H:MM:SS [speaker] text`, with the lecturer relabelled `Lektor` and everyone else `Účastník N`, hallucinations stripped. Then one subagent (mid tier) per lesson, all started together, each with the same brief file plus its lesson's facts (date and topic from the programme, recording length, the Q&A boundary and its caveats). The brief fixes: a heading with the lesson's real topic; a metadata list (course, date, programme topic, length, lecture/Q&A ranges, source and an "AI-generated, may be inaccurate" note); sections *In short*, *Lecture outline* (with times), *Key ideas*, *Demos and tools*, *Homework and organisation*, *Questions and discussion*, *Uncertain passages*; one long line per paragraph; no names of course participants even when someone says one; and "write what was said, not your own view". Subagents write to a scratch location; check every file (heading, metadata, all sections, no hard-wrapped paragraphs, a grep for common first names, the lecturer's name and noise strings), fix what you can verify from the transcript (a model or company name the subagent did not know), and only then move them into `output/`. Expect 1,700–2,700 words a lesson against a 1,200–1,800 target: long discussions push them over. Keep the brief in the course folder so the summaries can be regenerated.

## 10. Wrap up

Update the course README as each stage lands: what each folder and variant is, how it was made, the measured reasons behind each parameter, and the pitfalls hit. Report to the user what was verified (and how), what was only sampled, and what is left to review — above all the summaries' *Uncertain passages*.
