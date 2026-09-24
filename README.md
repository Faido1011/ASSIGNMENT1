# DevMentor

## Description

DevMentor is a command-line conversational AI assistant that runs fully
locally through [Ollama](https://ollama.com). It plays the role of a
programming tutor for junior developers: it explains concepts in plain
language, remembers the current conversation, and follows a defined
personality and set of behavioural rules. It was built for Assignment 1
of DSA5202 (Special Topics in Data Science) to demonstrate the wiring
underneath a conversational AI application, with no agent frameworks,
no RAG, and no vector database involved.

## Features

- Talks to a locally running Ollama model over its HTTP API.
- A detailed, role-specific system prompt (see `prompts.py`).
- Full multi-turn conversation memory within a session.
- `/reset` - clears history, keeps the system prompt.
- `/history` - prints the conversation so far (system prompt excluded).
- `/exit` - ends the program cleanly.
- `/save` - saves the current conversation to a JSON file (Bonus 2).
- `/load <file>` - restores a previously saved conversation, including
  its full message history so the model's context is genuinely
  restored, not just the latest line (Bonus 3).
- Model selection at startup from the models actually installed on the
  machine (Bonus 1).
- Four selectable personality modes: Beginner Tutor, Senior Engineer,
  Code Reviewer, Socratic Teacher (Bonus 5).
- Graceful handling of: Ollama not running, empty input, an unexpected
  API response shape, and a slow/unresponsive model - none of these
  crash the app or print a raw traceback.

## Architecture

```
        User
         |
         v
  Python application  (main.py)
         |
         |  reads/writes
         v
  Conversation history   <-- a Python list of {"role", "content"} dicts,
  (in-process memory)        held ONLY in this running process
         |
         |  the FULL list is sent on every request
         v
   Ollama HTTP API   (POST /api/chat)
         |
         v
    Local LLM   (e.g. llama3.2, running on this machine, no network call
                 ever leaves localhost)
         |
         v
      Response  -----> appended to conversation history -----> printed to User
```

Where things live:

- **The model** lives entirely inside the Ollama process on the local
  machine. DevMentor never downloads or embeds a model itself - it just
  calls Ollama's server.
- **Conversation state** lives entirely inside DevMentor's own Python
  process, as the `messages` list in `main.py`. Ollama has no idea this
  list existed the moment the HTTP response is sent.
- **The API's job** is to take one list of messages and return one new
  message - nothing more. It is a pure function of its input; it keeps
  no session, no cookie, no memory of the caller between calls.
- **What is sent on every request**: the system prompt, every prior
  user message, and every prior assistant reply, plus the new user
  message - the entire `messages` list, resent from scratch each turn.

## Installation

1. Install [Ollama](https://ollama.com) and make sure it is running:
   ```
   ollama serve
   ```
2. Pull at least one model, e.g.:
   ```
   ollama pull llama3.2
   ```
3. Clone this repository and install the Python dependency:
   ```
   git clone <this-repo-url>
   cd devmentor
   pip install -r requirements.txt
   ```

## Running the Application

```
python main.py
```

You will be asked to pick an installed model and a personality mode,
then dropped into the chat loop. Type a question, or use `/reset`,
`/history`, `/save`, `/load <file>`, or `/exit`.

## System Prompt Design

The live system prompt (`prompts.PROMPT_B_DETAILED`, used as
`DEFAULT_SYSTEM_PROMPT`) defines four things explicitly, as required:

- **Who it is talking to**: junior developers 0-2 years into their
  first job, who know basic syntax but get lost with jargon.
- **How it should explain things**: plain language before technical
  terms, short paragraphs, every unfamiliar term defined on first use.
- **How it should use examples**: at least one small runnable example
  for any concept with a "code shape", briefly commented so the example
  teaches rather than just demonstrates.
- **What it does when unsure**: says so plainly instead of guessing,
  and names how the developer could verify the answer themselves.

This is a rewrite of the starter sketch in the brief, not a copy of it -
the audience, example policy, and uncertainty policy were all added.

## Conversation Memory

`messages` is a single Python list shaped like:

```python
messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "What is recursion?"},
    {"role": "assistant", "content": "Recursion is when a function..."},
    {"role": "user", "content": "Show me an example."},
]
```

Every relevant prior message is resent on each call because **Ollama's
`/api/chat` endpoint is stateless** - it does not remember the previous
HTTP request. The only reason the model can resolve "Show me an
example" as being about recursion is that the earlier turns about
recursion are sitting right there in the same request. If DevMentor
only sent the newest line, the model would see an example request with
no subject and would have to guess, or ask "an example of what?".

## Prompt Engineering Experiment

Three system prompts were defined in `prompts.py` (A: minimal, B:
detailed, C: constrained) and each was asked the same four questions:
"Explain REST APIs.", "Explain recursion.", "What is dependency
injection?", "Show me an example."

**1. Which prompt was most useful, and why?**
Prompt C (constrained) was the most consistently useful for the target
audience. Its numbered rules - explain in words before code, keep
intros short, default to Python, define every term, admit uncertainty,
end with a follow-up question - produced answers that were predictable
in shape every time, which matters for a tutoring tool a junior dev
will use repeatedly. Prompt B was close behind and slightly richer, but
less consistent about the intro length.

**2. What differences did you see?**
Prompt A's answers were competent but generic - correct definitions,
but no adjustment for a junior audience, occasional jargon left
undefined, and no consistent example policy, so "Show me an example."
sometimes got a paragraph and sometimes got straight to code with no
explanation. Prompt B consistently included a worked example and
plain-language framing, but its intros varied in length. Prompt C was
the most uniform: short intro, then explanation, then example, then a
follow-up question, every time.

**3. Did more instructions always help?**
No. Going from A to B helped clearly - defining the audience and the
explanation style fixed the "generic textbook" tone. Going from B to C
helped in a narrower way: it mostly changed *shape and consistency*
rather than the *quality* of the underlying explanation, and one rule
in C (always end with a follow-up question) occasionally felt forced
on questions that didn't need one, showing that more rules can trade
away some naturalness for consistency.

**4. Which rules changed behaviour the most?**
Naming the audience explicitly ("junior developers who know basic
syntax but get lost with jargon") in Prompt B had the single biggest
effect - it changed vocabulary and pacing across every answer. In
Prompt C, "explain before code" had the next-biggest effect, since it
reliably reordered the whole answer's structure.

**5. What happened when a rule was vague?**
Prompt A's only rule was "You are a programming assistant" - vague
enough that it left tone, depth, and audience undefined, and the model
picked reasonable defaults on its own each time, which is exactly why
its answers were the least predictable across repeated runs of the
same question.

## Memory Investigation

Live test run on 2026-09-24 used `llama3.2:latest` with the Beginner
Tutor personality:

1. "My favorite programming language is Python."
2. "Explain interfaces."
3. "What is my favorite programming language?"

With the full history sent, the answer to step 3 was:

> You mentioned earlier that your favorite programming language is Python.

I then used `/reset`, which removes all earlier user and assistant
messages while retaining the system prompt, and asked the same question
again. The answer was:

> I'm not sure I should take a guess at that. What's your favorite
> programming language?

The changed answer demonstrates that the model had access to the fact
only while the earlier message was included in the request.

**Does the LLM actually "remember" the conversation?**
No - not in the sense of the model itself holding a memory. Every call
to Ollama's `/api/chat` is independent; the model has no persistent
state between requests. What looks like "memory" is entirely:

- **Application state**: the `messages` list living inside DevMentor's
  own running Python process.
- **Message history**: that same list, holding every turn so far in
  order, with each turn labelled by role.
- **The context sent on each request**: DevMentor resends the *entire*
  list on every single call, so from the model's point of view, "the
  whole conversation" is just "everything present in this one prompt".

Delete an early item from that list, as the second half of this
experiment did, and the model's "memory" of it is gone - not because
the model forgot, but because that fact was never sent to it this time.

## Challenge Questions

**1. Why does the app send previous messages to the LLM?**
Because the LLM API is stateless - each call is judged only on what is
inside it. Sending previous messages is the only way the model can
resolve references like "it", "that", or "an example" back to what was
discussed earlier.

**2. What is the difference between system, user, and assistant
messages?**
`system` sets the assistant's role, audience, and rules before any
conversation happens. `user` is what the human typed. `assistant` is
what the model replied. All three sit in the same list, but only
`system` configures behaviour rather than reporting a turn that was
"said".

**3. If you close Python and restart, why does the assistant "forget"?**
Because the `messages` list lived only in that process's memory (RAM).
Closing Python destroys it. Ollama never had a copy of it either -
it only ever saw one request at a time. Unless the conversation was
saved to disk with `/save`, restarting starts from an empty list.

**4. Is memory stored inside the LLM or inside your application?
Explain.**
Inside the application. The model has weights fixed at training time
and, per request, whatever text is in its context window - it holds
nothing between requests. DevMentor's `messages` list is the only place
the conversation actually persists while the app runs.

**5. What happens when the conversation becomes extremely long?
Research the term context window.**
Every model has a maximum number of tokens (roughly, chunks of text)
it can accept in a single request - its **context window** (e.g. a few
thousand to a few hundred thousand tokens, depending on the model).
Once a conversation's full history exceeds that limit, it can no
longer all be sent: requests may be rejected, silently truncated from
the start, or - if this isn't managed - the oldest, sometimes most
important, messages (like "my favorite language is Python") fall out
of the model's view entirely, without any explicit `/reset` from the
user. Longer contexts also cost more compute and can respond more
slowly, even before that hard limit is reached.

**6. Why is "You are helpful." a weak system prompt? How would you
improve it?**
It defines nothing that actually changes behaviour: no audience, no
explanation style, no example policy, and no rule for what to do when
unsure. It leaves the model to choose defaults, which is exactly why
Prompt A in the experiment above was the least predictable. Prompt B
and C in `prompts.py` improve on it by naming a specific audience, a
concrete explanation style, an example policy, and an explicit
uncertainty policy.

**7. After the LLM replies, what should happen to messages before the
next user turn, and why?**
The assistant's reply should be appended to the same `messages` list,
in its `assistant` role, before the next user turn is added. If it
isn't appended, the model's next call would be missing its own
previous answer and could contradict itself or ask the user to repeat
something it just explained - the whole point of resending history is
that it includes what the model itself said, not just what the user
said.

## Bonus: Context Window Management Strategies

Two strategies for handling a chat that has grown too large for the
context window, beyond what is implemented here:

1. **Sliding window with a running summary** - keep the system prompt
   and the most recent N turns verbatim, but periodically ask the model
   to summarize everything older into a short paragraph and keep only
   that summary in place of the original messages. This trades some
   detail for staying inside the limit indefinitely.
2. **Token-budgeted trimming** - track the token count of the message
   list as it grows (Ollama's response includes token usage), and once
   it approaches the model's context limit, drop the oldest non-system
   messages first, in pairs (user+assistant), so the conversation stays
   coherent rather than half-truncated mid-exchange.

## Required Features Verification

Tested on 2026-09-24 against a locally running Ollama instance:

- [x] Dynamic user input: entered chat prompts in the running application.
- [x] System prompt: selected the Beginner Tutor personality at startup.
- [x] User and assistant messages: sent three live prompts and received replies.
- [x] Multi-turn memory: the model recalled Python before `/reset` and did not after it.
- [x] `/reset`: cleared the chat while retaining the system prompt.
- [x] `/history`: printed the current conversation and excluded the system prompt.
- [x] `/exit`: printed `Goodbye!` and ended cleanly.
- [x] Empty input: pressing Enter displayed `Please type something - I can't send an empty message.`
- [x] Connection-error handling: an unreachable local Ollama endpoint displayed the friendly connection message and exited without a traceback.
- [x] Missing-file handling: `/load does-not-exist.json` displayed `No such file: conversations\does-not-exist.json`.
- [x] Function-based structure: the flow is separated into connection, input, response, reset, history, save, and load functions in `main.py`.

## Git History

This repository is committed incrementally (client setup, chat loop,
system prompt, conversation memory, commands, error handling,
documentation) rather than as a single dump, so the history itself
shows how the pieces were built up.

## Front-page details

| Field | Value |
|---|---|
| Full name | TWAGIRUMUKIZA Fidele |
| Student ID | 2000260089 |
| Programme | MSc Data Science and Analytics |
| Course code | DSA5202 |
| Assignment | Assignment 1 |
| Repository URL | https://github.com/Faido1011/ASSIGNMENT1 |
| Date submitted | 2026-09-24 |
