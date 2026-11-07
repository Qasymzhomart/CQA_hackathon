# AI / Analytics — CQA evaluator

## Selected model

Default: `gemini-2.5-flash` through the Gemini Developer API.

Why:
- structured JSON output is supported by the Google Gen AI SDK;
- multilingual RU / KZ / EN evaluation;
- one full-conversation call can evaluate the dynamic checklist;
- compatible with a free-tier Gemini API key when available.

The model can be changed without code:

```powershell
$env:CQA_AI_MODEL="gemini-2.5-flash"
```

## Required environment

PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_KEY"
```

Never commit the key.

## Architecture

```
dynamic checklist + transcript with message_id
                |
                v
          system prompt v1
                |
                v
       Gemini structured output
                |
                v
             validator
           /           \
        valid         invalid
          |              |
          |          one retry
          |              |
          +-------> backend adapter
                         |
                         v
              backend weighted scoring
```

AI does **not** calculate the final weighted score.

## Output contract

Every criterion returns:
- `criterion_id`
- `applicable`
- `answer`
- `score`
- `reason`
- `evidence_ids`
- `checked_message_ids`
- `critical_error`

Evidence IDs are validated against the original transcript. The model does not
supply trusted quote text; the backend resolves evidence text from message IDs.

## N/A

- `applicable=false` only when `allow_na=true`.
- N/A score is `null`.
- A failed applicable criterion receives score 0 and is not converted to N/A.

## Prompt injection

Transcript text is explicitly treated as untrusted data. Instructions written by
a client inside the transcript must never override evaluator instructions.

## Retry

The first structured result is validated. If it violates the checklist schema,
score ranges, N/A rules, or evidence IDs, the validator sends the errors back to
Gemini once. A second invalid result fails the evaluation.

## Token and cost logging

The Google SDK usage metadata is recorded as input/output token counts.

For a free-tier hackathon key, cost defaults to `0`. If a paid tier is used,
set the real current per-million-token prices before the demo:

```powershell
$env:CQA_AI_INPUT_USD_PER_M="..."
$env:CQA_AI_OUTPUT_USD_PER_M="..."
```

This avoids inventing a price.

## Prompt version

`PROMPT_VERSION = "v1"`

Increment it when evaluator instructions materially change.
