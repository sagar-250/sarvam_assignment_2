# Kivi Memory System - Multi-User Simulation Report

Run at: 2026-09-04T09:43:51Z

LLM-sourced raw material (tools/generate_entities.py), deterministically assembled into per-persona conversations, run through the real /observe and /run pipeline, graded against the documented activation rule (not against the LLM's opinion). See eval/simulate_users.py docstring for the full methodology.

**33 simulated users, 99 LLM-generated personal terms, 99 recall checks.**

## Summary

- Precision: 1.0, Recall: 1.0
- Counts: {'TN': 45, 'TP_useful_intervention': 54}
- False positives on ordinary filler text (should always be 0): 0
- Anomalies (mention-count mismatches - see below): 18
- Latency: p50=8.419ms, p95=18.465ms

## Anomalies

- **user_005**: amazon prime: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_006**: los angles: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_008**: san fransisco: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_008**: new dilli: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_009**: dell laptop: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_012**: goole maps: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_014**: microsoft surface: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_015**: apple ipad: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_015**: samsung galaxy: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_016**: googel pixel: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_016**: dell xps: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_017**: washington dc: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_018**: apple watch: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_019**: microsoft visal: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_020**: hong kong: intended 3 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_024**: google pixel: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_028**: nu york: intended 2 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)
- **user_030**: sony xperia: intended 1 mentions, memory shows evidence_count=0 (diff.py likely split phrasing into a different observed_form - inspect conversation_log)

## Per-Persona Detail

### user_001

Terms taught this session:
- `sidharth` -> `Siddharth` (person_name), intended 1x, actual evidence_count=1, active=False
- `pixle` -> `Pixel` (product_name), intended 2x, actual evidence_count=2, active=True
- `mikrosoft` -> `Microsoft Surface` (product_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "install mikrosoft on my laptop" / Corrected: "install Microsoft Surface on my laptop" -> learned: mikrosoft->Microsoft Surface (new_candidate)
- ASR: "the mikrosoft service crashed again" / Corrected: "the Microsoft Surface service crashed again" -> learned: mikrosoft->Microsoft Surface (activated)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "the pixle dashboard looks great" / Corrected: "the Pixel dashboard looks great" -> learned: pixle->Pixel (new_candidate)
- ASR: "check mikrosoft settings" / Corrected: "check Microsoft Surface settings" -> learned: mikrosoft->Microsoft Surface (already_active)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "the pixle service crashed again" / Corrected: "the Pixel service crashed again" -> learned: pixle->Pixel (activated)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "meet sidharth at noon" / Corrected: "meet Siddharth at noon" -> learned: sidharth->Siddharth (new_candidate)

Follow-up recall test (unseen sentence per term):
- "call sidharth now" -> "Call sidharth now." [TN]
- "install pixle on my laptop" -> "Install Pixel on my laptop." [TP_useful_intervention]
- "update mikrosoft to the latest version" -> "Update Microsoft Surface to the latest version." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_002

Terms taught this session:
- `joshuwa` -> `Joshua` (person_name), intended 1x, actual evidence_count=1, active=False
- `jesica` -> `Jessica` (person_name), intended 2x, actual evidence_count=2, active=True
- `dilli` -> `Delhi` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "remind me to email jesica tomorrow" / Corrected: "remind me to email Jessica tomorrow" -> learned: jesica->Jessica (new_candidate)
- ASR: "meeting is scheduled in dilli" / Corrected: "meeting is scheduled in Delhi" -> learned: dilli->Delhi (new_candidate)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "can you tell jesica about the meeting" / Corrected: "can you tell Jessica about the meeting" -> learned: jesica->Jessica (activated)
- ASR: "the conference is in dilli this year" / Corrected: "the conference is in Delhi this year" -> learned: dilli->Delhi (activated)
- ASR: "meet joshuwa at noon" / Corrected: "meet Joshua at noon" -> learned: joshuwa->Joshua (new_candidate)
- ASR: "the office in dilli is closed" / Corrected: "the office in Delhi is closed" -> learned: dilli->Delhi (already_active)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "ask joshuwa to join the call" -> "Ask joshuwa to join the call." [TN]
- "send the report to jesica" -> "Send the report to Jessica." [TP_useful_intervention]
- "flying to dilli tomorrow" -> "Flying to Delhi tomorrow." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_003

Terms taught this session:
- `ravee` -> `Ravi` (person_name), intended 1x, actual evidence_count=1, active=False
- `amrit` -> `Amrita` (person_name), intended 2x, actual evidence_count=2, active=True
- `deepa` -> `Deepti` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "send the report to amrit" / Corrected: "send the report to Amrita" -> learned: amrit->Amrita (new_candidate)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "meet ravee at noon" / Corrected: "meet Ravi at noon" -> learned: ravee->Ravi (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "send the report to deepa" / Corrected: "send the report to Deepti" -> learned: deepa->Deepti (new_candidate)
- ASR: "can you tell deepa about the meeting" / Corrected: "can you tell Deepti about the meeting" -> learned: deepa->Deepti (activated)
- ASR: "ask amrit to join the call" / Corrected: "ask Amrita to join the call" -> learned: amrit->Amrita (activated)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "remind me to email deepa tomorrow" / Corrected: "remind me to email Deepti tomorrow" -> learned: deepa->Deepti (already_active)

Follow-up recall test (unseen sentence per term):
- "can you tell ravee about the meeting" -> "Can you tell ravee about the meeting." [TN]
- "call amrit now" -> "Call Amrita now." [TP_useful_intervention]
- "meet deepa at noon" -> "Meet Deepti at noon." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_004

Terms taught this session:
- `poona` -> `Pune` (place_name), intended 1x, actual evidence_count=1, active=False
- `bengalooru` -> `Bengaluru` (place_name), intended 2x, actual evidence_count=2, active=True
- `jaxon` -> `Jackson` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "flying to bengalooru tomorrow" / Corrected: "flying to Bengaluru tomorrow" -> learned: bengalooru->Bengaluru (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "ask jaxon to join the call" / Corrected: "ask Jackson to join the call" -> learned: jaxon->Jackson (new_candidate)
- ASR: "we are relocating to bengalooru" / Corrected: "we are relocating to Bengaluru" -> learned: bengalooru->Bengaluru (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "remind me to email jaxon tomorrow" / Corrected: "remind me to email Jackson tomorrow" -> learned: jaxon->Jackson (activated)
- ASR: "send the report to jaxon" / Corrected: "send the report to Jackson" -> learned: jaxon->Jackson (already_active)
- ASR: "book a flight to poona" / Corrected: "book a flight to Pune" -> learned: poona->Pune (new_candidate)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the office in poona is closed" -> "The office in poona is closed." [TN]
- "the conference is in bengalooru this year" -> "The conference is in Bengaluru this year." [TP_useful_intervention]
- "can you tell jaxon about the meeting" -> "Can you tell Jackson about the meeting." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_005

Terms taught this session:
- `amazon prime` -> `Amazon Prime Video` (product_name), intended 1x, actual evidence_count=0, active=False
- `chrome book` -> `Chromebook` (product_name), intended 2x, actual evidence_count=2, active=True
- `maria` -> `Mariah` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "ask maria to join the call" / Corrected: "ask Mariah to join the call" -> learned: maria->Mariah (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "call maria now" / Corrected: "call Mariah now" -> learned: maria->Mariah (activated)
- ASR: "update chrome book to the latest version" / Corrected: "update Chromebook to the latest version" -> learned: chrome book->Chromebook (new_candidate)
- ASR: "can you tell maria about the meeting" / Corrected: "can you tell Mariah about the meeting" -> learned: maria->Mariah (already_active)
- ASR: "the amazon prime dashboard looks great" / Corrected: "the Amazon Prime Video dashboard looks great" -> learned: prime->Prime Video (new_candidate)
- ASR: "check chrome book settings" / Corrected: "check Chromebook settings" -> learned: chrome book->Chromebook (activated)

Follow-up recall test (unseen sentence per term):
- "update amazon prime to the latest version" -> "Update amazon prime to the latest version." [TN]
- "install chrome book on my laptop" -> "Install Chromebook on my laptop." [TP_useful_intervention]
- "meet maria at noon" -> "Meet Mariah at noon." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_006

Terms taught this session:
- `pooja` -> `Puja` (person_name), intended 1x, actual evidence_count=1, active=False
- `jaypurr` -> `Jaypur` (place_name), intended 2x, actual evidence_count=2, active=True
- `los angles` -> `Los Angeles` (place_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "meet pooja at noon" / Corrected: "meet Puja at noon" -> learned: pooja->Puja (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "meeting is scheduled in los angles" / Corrected: "meeting is scheduled in Los Angeles" -> learned: angles->Angeles (new_candidate)
- ASR: "meeting is scheduled in jaypurr" / Corrected: "meeting is scheduled in Jaypur" -> learned: jaypurr->Jaypur (new_candidate)
- ASR: "flying to los angles tomorrow" / Corrected: "flying to Los Angeles tomorrow" -> learned: angles->Angeles (activated)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "we are relocating to jaypurr" / Corrected: "we are relocating to Jaypur" -> learned: jaypurr->Jaypur (activated)
- ASR: "the conference is in los angles this year" / Corrected: "the conference is in Los Angeles this year" -> learned: angles->Angeles (already_active)

Follow-up recall test (unseen sentence per term):
- "can you tell pooja about the meeting" -> "Can you tell pooja about the meeting." [TN]
- "the conference is in jaypurr this year" -> "The conference is in Jaypur this year." [TP_useful_intervention]
- "book a flight to los angles" -> "Book a flight to los Angeles." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_007

Terms taught this session:
- `aashna` -> `Aashish` (person_name), intended 1x, actual evidence_count=1, active=False
- `play station` -> `PlayStation` (product_name), intended 2x, actual evidence_count=2, active=True
- `micheal` -> `Michael` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "send the report to aashna" / Corrected: "send the report to Aashish" -> learned: aashna->Aashish (new_candidate)
- ASR: "ask micheal to join the call" / Corrected: "ask Michael to join the call" -> learned: micheal->Michael (new_candidate)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "meet micheal at noon" / Corrected: "meet Michael at noon" -> learned: micheal->Michael (activated)
- ASR: "the play station service crashed again" / Corrected: "the PlayStation service crashed again" -> learned: play station->PlayStation (new_candidate)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "the play station dashboard looks great" / Corrected: "the PlayStation dashboard looks great" -> learned: play station->PlayStation (activated)
- ASR: "call micheal now" / Corrected: "call Michael now" -> learned: micheal->Michael (already_active)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "remind me to email aashna tomorrow" -> "Remind me to email aashna tomorrow." [TN]
- "restart the play station app" -> "Restart the PlayStation app." [TP_useful_intervention]
- "remind me to email micheal tomorrow" -> "Remind me to email Michael tomorrow." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_008

Terms taught this session:
- `san fransisco` -> `San Francisco` (place_name), intended 1x, actual evidence_count=0, active=False
- `noa` -> `Noah` (person_name), intended 2x, actual evidence_count=2, active=True
- `new dilli` -> `New Delhi` (place_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "the conference is in new dilli this year" / Corrected: "the conference is in New Delhi this year" -> learned: dilli->Delhi (new_candidate)
- ASR: "send the report to noa" / Corrected: "send the report to Noah" -> learned: noa->Noah (new_candidate)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "the office in new dilli is closed" / Corrected: "the office in New Delhi is closed" -> learned: dilli->Delhi (activated)
- ASR: "remind me to email noa tomorrow" / Corrected: "remind me to email Noah tomorrow" -> learned: noa->Noah (activated)
- ASR: "flying to new dilli tomorrow" / Corrected: "flying to New Delhi tomorrow" -> learned: dilli->Delhi (already_active)
- ASR: "the office in san fransisco is closed" / Corrected: "the office in San Francisco is closed" -> learned: fransisco->Francisco (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the conference is in san fransisco this year" -> "The conference is in san fransisco this year." [TN]
- "meet noa at noon" -> "Meet Noah at noon." [TP_useful_intervention]
- "meeting is scheduled in new dilli" -> "Meeting is scheduled in new Delhi." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_009

Terms taught this session:
- `rahool` -> `Rahul` (person_name), intended 1x, actual evidence_count=1, active=False
- `dell laptop` -> `Dell XPS` (product_name), intended 2x, actual evidence_count=0, active=False
- `playstashun` -> `PlayStation` (product_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "the playstashun dashboard looks great" / Corrected: "the PlayStation dashboard looks great" -> learned: playstashun->PlayStation (new_candidate)
- ASR: "the playstashun service crashed again" / Corrected: "the PlayStation service crashed again" -> learned: playstashun->PlayStation (activated)
- ASR: "remind me to email rahool tomorrow" / Corrected: "remind me to email Rahul tomorrow" -> learned: rahool->Rahul (new_candidate)
- ASR: "update dell laptop to the latest version" / Corrected: "update Dell XPS to the latest version" -> learned: laptop->XPS (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "restart the dell laptop app" / Corrected: "restart the Dell XPS app" -> learned: laptop->XPS (activated)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "install playstashun on my laptop" / Corrected: "install PlayStation on my laptop" -> learned: playstashun->PlayStation (already_active)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "send the report to rahool" -> "Send the report to rahool." [TN]
- "the dell laptop service crashed again" -> "The dell XPS service crashed again." [TN]
- "restart the playstashun app" -> "Restart the PlayStation app." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_010

Terms taught this session:
- `pixal` -> `Pixel` (product_name), intended 1x, actual evidence_count=1, active=False
- `britney` -> `Brittany` (person_name), intended 2x, actual evidence_count=2, active=True
- `bangalore` -> `Bengaluru` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "call britney now" / Corrected: "call Brittany now" -> learned: britney->Brittany (new_candidate)
- ASR: "ask britney to join the call" / Corrected: "ask Brittany to join the call" -> learned: britney->Brittany (activated)
- ASR: "meeting is scheduled in bangalore" / Corrected: "meeting is scheduled in Bengaluru" -> learned: bangalore->Bengaluru (new_candidate)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "restart the pixal app" / Corrected: "restart the Pixel app" -> learned: pixal->Pixel (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "book a flight to bangalore" / Corrected: "book a flight to Bengaluru" -> learned: bangalore->Bengaluru (activated)
- ASR: "the conference is in bangalore this year" / Corrected: "the conference is in Bengaluru this year" -> learned: bangalore->Bengaluru (already_active)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the pixal service crashed again" -> "The pixal service crashed again." [TN]
- "can you tell britney about the meeting" -> "Can you tell Brittany about the meeting." [TP_useful_intervention]
- "we are relocating to bangalore" -> "We are relocating to Bengaluru." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_011

Terms taught this session:
- `eye phone` -> `iPhone` (product_name), intended 1x, actual evidence_count=1, active=False
- `aisha` -> `Ayisha` (person_name), intended 2x, actual evidence_count=2, active=True
- `ashlee` -> `Ashley` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "send the report to aisha" / Corrected: "send the report to Ayisha" -> learned: aisha->Ayisha (new_candidate)
- ASR: "check eye phone settings" / Corrected: "check iPhone settings" -> learned: eye phone->iPhone (new_candidate)
- ASR: "remind me to email ashlee tomorrow" / Corrected: "remind me to email Ashley tomorrow" -> learned: ashlee->Ashley (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "call ashlee now" / Corrected: "call Ashley now" -> learned: ashlee->Ashley (activated)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "remind me to email aisha tomorrow" / Corrected: "remind me to email Ayisha tomorrow" -> learned: aisha->Ayisha (activated)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "meet ashlee at noon" / Corrected: "meet Ashley at noon" -> learned: ashlee->Ashley (already_active)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "restart the eye phone app" -> "Restart the eye phone app." [TN]
- "meet aisha at noon" -> "Meet Ayisha at noon." [TP_useful_intervention]
- "can you tell ashlee about the meeting" -> "Can you tell Ashley about the meeting." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_012

Terms taught this session:
- `pixl` -> `Pixel` (product_name), intended 1x, actual evidence_count=1, active=False
- `mac book` -> `MacBook` (product_name), intended 2x, actual evidence_count=2, active=True
- `goole maps` -> `Google Maps` (product_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "check goole maps settings" / Corrected: "check Google Maps settings" -> learned: goole->Google (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "the goole maps service crashed again" / Corrected: "the Google Maps service crashed again" -> learned: goole->Google (activated)
- ASR: "update mac book to the latest version" / Corrected: "update MacBook to the latest version" -> learned: mac book->MacBook (new_candidate)
- ASR: "install pixl on my laptop" / Corrected: "install Pixel on my laptop" -> learned: pixl->Pixel (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "restart the mac book app" / Corrected: "restart the MacBook app" -> learned: mac book->MacBook (activated)
- ASR: "restart the goole maps app" / Corrected: "restart the Google Maps app" -> learned: goole->Google (already_active)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the pixl service crashed again" -> "The pixl service crashed again." [TN]
- "the mac book dashboard looks great" -> "The MacBook dashboard looks great." [TP_useful_intervention]
- "the goole maps dashboard looks great" -> "The Google maps dashboard looks great." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_013

Terms taught this session:
- `londun` -> `London` (place_name), intended 1x, actual evidence_count=1, active=False
- `makbook` -> `MacBook` (product_name), intended 2x, actual evidence_count=2, active=True
- `gurleen` -> `Gurpreet` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "call gurleen now" / Corrected: "call Gurpreet now" -> learned: gurleen->Gurpreet (new_candidate)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "the makbook service crashed again" / Corrected: "the MacBook service crashed again" -> learned: makbook->MacBook (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "check makbook settings" / Corrected: "check MacBook settings" -> learned: makbook->MacBook (activated)
- ASR: "send the report to gurleen" / Corrected: "send the report to Gurpreet" -> learned: gurleen->Gurpreet (activated)
- ASR: "the office in londun is closed" / Corrected: "the office in London is closed" -> learned: londun->London (new_candidate)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "ask gurleen to join the call" / Corrected: "ask Gurpreet to join the call" -> learned: gurleen->Gurpreet (already_active)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "flying to londun tomorrow" -> "Flying to londun tomorrow." [TN]
- "update makbook to the latest version" -> "Update MacBook to the latest version." [TP_useful_intervention]
- "can you tell gurleen about the meeting" -> "Can you tell Gurpreet about the meeting." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_014

Terms taught this session:
- `air pod` -> `AirPod` (product_name), intended 1x, actual evidence_count=1, active=False
- `googel` -> `Google Maps` (product_name), intended 2x, actual evidence_count=2, active=True
- `microsoft surface` -> `Microsoft Surface Pro` (product_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "the googel dashboard looks great" / Corrected: "the Google Maps dashboard looks great" -> learned: googel->Google Maps (new_candidate)
- ASR: "update microsoft surface to the latest version" / Corrected: "update Microsoft Surface Pro to the latest version" -> learned: surface->Surface Pro (new_candidate)
- ASR: "check googel settings" / Corrected: "check Google Maps settings" -> learned: googel->Google Maps (activated)
- ASR: "update air pod to the latest version" / Corrected: "update AirPod to the latest version" -> learned: air pod->AirPod (new_candidate)
- ASR: "the microsoft surface service crashed again" / Corrected: "the Microsoft Surface Pro service crashed again" -> learned: surface->Surface Pro (activated)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "restart the microsoft surface app" / Corrected: "restart the Microsoft Surface Pro app" -> learned: surface->Surface Pro (already_active)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the air pod dashboard looks great" -> "The air pod dashboard looks great." [TN]
- "the googel service crashed again" -> "The Google Maps service crashed again." [TP_useful_intervention]
- "check microsoft surface settings" -> "Check microsoft Surface Pro settings." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_015

Terms taught this session:
- `apple ipad` -> `Apple iPad Air` (product_name), intended 1x, actual evidence_count=0, active=False
- `samsung galaxy` -> `Samsung Galaxy S23` (product_name), intended 2x, actual evidence_count=0, active=False
- `bangalor` -> `Bangalore` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "the office in bangalor is closed" / Corrected: "the office in Bangalore is closed" -> learned: bangalor->Bangalore (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "the samsung galaxy dashboard looks great" / Corrected: "the Samsung Galaxy S23 dashboard looks great" -> learned: galaxy->Galaxy S23 (new_candidate)
- ASR: "book a flight to bangalor" / Corrected: "book a flight to Bangalore" -> learned: bangalor->Bangalore (activated)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "install samsung galaxy on my laptop" / Corrected: "install Samsung Galaxy S23 on my laptop" -> learned: galaxy->Galaxy S23 (activated)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "check apple ipad settings" / Corrected: "check Apple iPad Air settings" -> learned: ipad->iPad Air (new_candidate)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "meeting is scheduled in bangalor" / Corrected: "meeting is scheduled in Bangalore" -> learned: bangalor->Bangalore (already_active)

Follow-up recall test (unseen sentence per term):
- "the apple ipad service crashed again" -> "The apple ipad service crashed again." [TN]
- "update samsung galaxy to the latest version" -> "Update samsung Galaxy S23 to the latest version." [TN]
- "we are relocating to bangalor" -> "We are relocating to Bangalore." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_016

Terms taught this session:
- `preya` -> `Priya` (person_name), intended 1x, actual evidence_count=1, active=False
- `googel pixel` -> `Google Pixel` (product_name), intended 2x, actual evidence_count=0, active=False
- `dell xps` -> `Dell XPS Pro` (product_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "check googel pixel settings" / Corrected: "check Google Pixel settings" -> learned: googel->Google (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "call preya now" / Corrected: "call Priya now" -> learned: preya->Priya (new_candidate)
- ASR: "the dell xps dashboard looks great" / Corrected: "the Dell XPS Pro dashboard looks great" -> learned: xps->XPS Pro (new_candidate)
- ASR: "the googel pixel service crashed again" / Corrected: "the Google Pixel service crashed again" -> learned: googel->Google (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "the dell xps service crashed again" / Corrected: "the Dell XPS Pro service crashed again" -> learned: xps->XPS Pro (activated)
- ASR: "restart the dell xps app" / Corrected: "restart the Dell XPS Pro app" -> learned: xps->XPS Pro (already_active)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "remind me to email preya tomorrow" -> "Remind me to email preya tomorrow." [TN]
- "restart the googel pixel app" -> "Restart the Google pixel app." [TN]
- "update dell xps to the latest version" -> "Update dell XPS Pro to the latest version." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_017

Terms taught this session:
- `washington dc` -> `Washington, D.C.` (place_name), intended 1x, actual evidence_count=0, active=False
- `karan` -> `Karun` (person_name), intended 2x, actual evidence_count=2, active=True
- `rishi` -> `Rishabh` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "ask rishi to join the call" / Corrected: "ask Rishabh to join the call" -> learned: rishi->Rishabh (new_candidate)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "can you tell karan about the meeting" / Corrected: "can you tell Karun about the meeting" -> learned: karan->Karun (new_candidate)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "the conference is in washington dc this year" / Corrected: "the conference is in Washington, D.C. this year" -> learned: dc->D C (new_candidate)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "remind me to email rishi tomorrow" / Corrected: "remind me to email Rishabh tomorrow" -> learned: rishi->Rishabh (activated)
- ASR: "remind me to email karan tomorrow" / Corrected: "remind me to email Karun tomorrow" -> learned: karan->Karun (activated)
- ASR: "can you tell rishi about the meeting" / Corrected: "can you tell Rishabh about the meeting" -> learned: rishi->Rishabh (already_active)

Follow-up recall test (unseen sentence per term):
- "meeting is scheduled in washington dc" -> "Meeting is scheduled in washington dc." [TN]
- "call karan now" -> "Call Karun now." [TP_useful_intervention]
- "meet rishi at noon" -> "Meet Rishabh at noon." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_018

Terms taught this session:
- `i fon` -> `iPhone` (product_name), intended 1x, actual evidence_count=1, active=False
- `apple watch` -> `Apple Watch Series` (product_name), intended 2x, actual evidence_count=0, active=False
- `hyderbad` -> `Hyderabad` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "install apple watch on my laptop" / Corrected: "install Apple Watch Series on my laptop" -> learned: watch->Watch Series (new_candidate)
- ASR: "book a flight to hyderbad" / Corrected: "book a flight to Hyderabad" -> learned: hyderbad->Hyderabad (new_candidate)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "restart the i fon app" / Corrected: "restart the iPhone app" -> learned: i fon->iPhone (new_candidate)
- ASR: "we are relocating to hyderbad" / Corrected: "we are relocating to Hyderabad" -> learned: hyderbad->Hyderabad (activated)
- ASR: "the office in hyderbad is closed" / Corrected: "the office in Hyderabad is closed" -> learned: hyderbad->Hyderabad (already_active)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "the apple watch dashboard looks great" / Corrected: "the Apple Watch Series dashboard looks great" -> learned: watch->Watch Series (activated)

Follow-up recall test (unseen sentence per term):
- "update i fon to the latest version" -> "Update i fon to the latest version." [TN]
- "check apple watch settings" -> "Check apple Watch Series settings." [TN]
- "flying to hyderbad tomorrow" -> "Flying to Hyderabad tomorrow." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_019

Terms taught this session:
- `microsoft visal` -> `Microsoft Visual` (product_name), intended 1x, actual evidence_count=0, active=False
- `galexy` -> `Galaxy` (product_name), intended 2x, actual evidence_count=2, active=True
- `rohith` -> `Rohit` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "install microsoft visal on my laptop" / Corrected: "install Microsoft Visual on my laptop" -> learned: visal->Visual (new_candidate)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "the galexy service crashed again" / Corrected: "the Galaxy service crashed again" -> learned: galexy->Galaxy (new_candidate)
- ASR: "remind me to email rohith tomorrow" / Corrected: "remind me to email Rohit tomorrow" -> learned: rohith->Rohit (new_candidate)
- ASR: "the galexy dashboard looks great" / Corrected: "the Galaxy dashboard looks great" -> learned: galexy->Galaxy (activated)
- ASR: "meet rohith at noon" / Corrected: "meet Rohit at noon" -> learned: rohith->Rohit (activated)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "ask rohith to join the call" / Corrected: "ask Rohit to join the call" -> learned: rohith->Rohit (already_active)

Follow-up recall test (unseen sentence per term):
- "restart the microsoft visal app" -> "Restart the microsoft visal app." [TN]
- "restart the galexy app" -> "Restart the Galaxy app." [TP_useful_intervention]
- "call rohith now" -> "Call Rohit now." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_020

Terms taught this session:
- `evan` -> `Evanne` (person_name), intended 1x, actual evidence_count=1, active=False
- `mumbay` -> `Mumbai` (place_name), intended 2x, actual evidence_count=2, active=True
- `hong kong` -> `Hong Kong Island` (place_name), intended 3x, actual evidence_count=0, active=False

Conversation fed through /observe:
- ASR: "meet evan at noon" / Corrected: "meet Evanne at noon" -> learned: evan->Evanne (new_candidate)
- ASR: "the office in hong kong is closed" / Corrected: "the office in Hong Kong Island is closed" -> learned: kong->Kong Island (new_candidate)
- ASR: "meeting is scheduled in hong kong" / Corrected: "meeting is scheduled in Hong Kong Island" -> learned: kong->Kong Island (activated)
- ASR: "flying to mumbay tomorrow" / Corrected: "flying to Mumbai tomorrow" -> learned: mumbay->Mumbai (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "we are relocating to hong kong" / Corrected: "we are relocating to Hong Kong Island" -> learned: kong->Kong Island (already_active)
- ASR: "the office in mumbay is closed" / Corrected: "the office in Mumbai is closed" -> learned: mumbay->Mumbai (activated)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "call evan now" -> "Call evan now." [TN]
- "book a flight to mumbay" -> "Book a flight to Mumbai." [TP_useful_intervention]
- "book a flight to hong kong" -> "Book a flight to hong Kong Island." [TN]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_021

Terms taught this session:
- `michel` -> `Michelle` (person_name), intended 1x, actual evidence_count=1, active=False
- `gita` -> `Gitanjali` (person_name), intended 2x, actual evidence_count=2, active=True
- `arjan` -> `Arjun` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "meet arjan at noon" / Corrected: "meet Arjun at noon" -> learned: arjan->Arjun (new_candidate)
- ASR: "meet michel at noon" / Corrected: "meet Michelle at noon" -> learned: michel->Michelle (new_candidate)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "can you tell gita about the meeting" / Corrected: "can you tell Gitanjali about the meeting" -> learned: gita->Gitanjali (new_candidate)
- ASR: "send the report to gita" / Corrected: "send the report to Gitanjali" -> learned: gita->Gitanjali (activated)
- ASR: "remind me to email arjan tomorrow" / Corrected: "remind me to email Arjun tomorrow" -> learned: arjan->Arjun (activated)
- ASR: "ask arjan to join the call" / Corrected: "ask Arjun to join the call" -> learned: arjan->Arjun (already_active)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "ask michel to join the call" -> "Ask michel to join the call." [TN]
- "remind me to email gita tomorrow" -> "Remind me to email Gitanjali tomorrow." [TP_useful_intervention]
- "send the report to arjan" -> "Send the report to Arjun." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_022

Terms taught this session:
- `nassau` -> `Nassau County` (place_name), intended 1x, actual evidence_count=1, active=False
- `vishesh` -> `Visheshwar` (person_name), intended 2x, actual evidence_count=2, active=True
- `vishal` -> `Vishaal` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "call vishesh now" / Corrected: "call Visheshwar now" -> learned: vishesh->Visheshwar (new_candidate)
- ASR: "meeting is scheduled in nassau" / Corrected: "meeting is scheduled in Nassau County" -> learned: nassau->Nassau County (new_candidate)
- ASR: "meet vishesh at noon" / Corrected: "meet Visheshwar at noon" -> learned: vishesh->Visheshwar (activated)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "can you tell vishal about the meeting" / Corrected: "can you tell Vishaal about the meeting" -> learned: vishal->Vishaal (new_candidate)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "call vishal now" / Corrected: "call Vishaal now" -> learned: vishal->Vishaal (activated)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "ask vishal to join the call" / Corrected: "ask Vishaal to join the call" -> learned: vishal->Vishaal (already_active)

Follow-up recall test (unseen sentence per term):
- "book a flight to nassau" -> "Book a flight to nassau." [TN]
- "remind me to email vishesh tomorrow" -> "Remind me to email Visheshwar tomorrow." [TP_useful_intervention]
- "meet vishal at noon" -> "Meet Vishaal at noon." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_023

Terms taught this session:
- `berlin` -> `Bairlin` (place_name), intended 1x, actual evidence_count=1, active=False
- `banglore` -> `Bengaluru` (place_name), intended 2x, actual evidence_count=2, active=True
- `deli` -> `Delhi` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "book a flight to berlin" / Corrected: "book a flight to Bairlin" -> learned: berlin->Bairlin (new_candidate)
- ASR: "meeting is scheduled in banglore" / Corrected: "meeting is scheduled in Bengaluru" -> learned: banglore->Bengaluru (new_candidate)
- ASR: "book a flight to banglore" / Corrected: "book a flight to Bengaluru" -> learned: banglore->Bengaluru (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "meeting is scheduled in deli" / Corrected: "meeting is scheduled in Delhi" -> learned: deli->Delhi (new_candidate)
- ASR: "flying to deli tomorrow" / Corrected: "flying to Delhi tomorrow" -> learned: deli->Delhi (activated)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "book a flight to deli" / Corrected: "book a flight to Delhi" -> learned: deli->Delhi (already_active)

Follow-up recall test (unseen sentence per term):
- "we are relocating to berlin" -> "We are relocating to berlin." [TN]
- "the conference is in banglore this year" -> "The conference is in Bengaluru this year." [TP_useful_intervention]
- "the conference is in deli this year" -> "The conference is in Delhi this year." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_024

Terms taught this session:
- `air pods` -> `AirPods` (product_name), intended 1x, actual evidence_count=1, active=False
- `google pixel` -> `Google Pixelbook` (product_name), intended 2x, actual evidence_count=0, active=False
- `priyah` -> `Priya` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "send the report to priyah" / Corrected: "send the report to Priya" -> learned: priyah->Priya (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "call priyah now" / Corrected: "call Priya now" -> learned: priyah->Priya (activated)
- ASR: "the air pods service crashed again" / Corrected: "the AirPods service crashed again" -> learned: air pods->AirPods (new_candidate)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "update google pixel to the latest version" / Corrected: "update Google Pixelbook to the latest version" -> learned: pixel->Pixelbook (new_candidate)
- ASR: "install google pixel on my laptop" / Corrected: "install Google Pixelbook on my laptop" -> learned: pixel->Pixelbook (activated)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "remind me to email priyah tomorrow" / Corrected: "remind me to email Priya tomorrow" -> learned: priyah->Priya (already_active)

Follow-up recall test (unseen sentence per term):
- "the air pods dashboard looks great" -> "The air pods dashboard looks great." [TN]
- "the google pixel dashboard looks great" -> "The google Pixelbook dashboard looks great." [TN]
- "can you tell priyah about the meeting" -> "Can you tell Priya about the meeting." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_025

Terms taught this session:
- `kavita` -> `Kavita Sharma` (person_name), intended 1x, actual evidence_count=1, active=False
- `calcutta` -> `Kolkata` (place_name), intended 2x, actual evidence_count=2, active=True
- `sairah` -> `Saira` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "call sairah now" / Corrected: "call Saira now" -> learned: sairah->Saira (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "meet sairah at noon" / Corrected: "meet Saira at noon" -> learned: sairah->Saira (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "remind me to email sairah tomorrow" / Corrected: "remind me to email Saira tomorrow" -> learned: sairah->Saira (already_active)
- ASR: "can you tell kavita about the meeting" / Corrected: "can you tell Kavita Sharma about the meeting" -> learned: kavita->Kavita Sharma (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "book a flight to calcutta" / Corrected: "book a flight to Kolkata" -> learned: calcutta->Kolkata (new_candidate)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "we are relocating to calcutta" / Corrected: "we are relocating to Kolkata" -> learned: calcutta->Kolkata (activated)

Follow-up recall test (unseen sentence per term):
- "remind me to email kavita tomorrow" -> "Remind me to email kavita tomorrow." [TN]
- "flying to calcutta tomorrow" -> "Flying to Kolkata tomorrow." [TP_useful_intervention]
- "send the report to sairah" -> "Send the report to Saira." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_026

Terms taught this session:
- `krystopher` -> `Christopher` (person_name), intended 1x, actual evidence_count=1, active=False
- `mahesh` -> `Maheshwar` (place_name), intended 2x, actual evidence_count=2, active=True
- `chenai` -> `Chennai` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "the office in chenai is closed" / Corrected: "the office in Chennai is closed" -> learned: chenai->Chennai (new_candidate)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "flying to mahesh tomorrow" / Corrected: "flying to Maheshwar tomorrow" -> learned: mahesh->Maheshwar (new_candidate)
- ASR: "the conference is in mahesh this year" / Corrected: "the conference is in Maheshwar this year" -> learned: mahesh->Maheshwar (activated)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "remind me to email krystopher tomorrow" / Corrected: "remind me to email Christopher tomorrow" -> learned: krystopher->Christopher (new_candidate)
- ASR: "book a flight to chenai" / Corrected: "book a flight to Chennai" -> learned: chenai->Chennai (activated)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "the conference is in chenai this year" / Corrected: "the conference is in Chennai this year" -> learned: chenai->Chennai (already_active)

Follow-up recall test (unseen sentence per term):
- "send the report to krystopher" -> "Send the report to krystopher." [TN]
- "book a flight to mahesh" -> "Book a flight to Maheshwar." [TP_useful_intervention]
- "meeting is scheduled in chenai" -> "Meeting is scheduled in Chennai." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_027

Terms taught this session:
- `ishan` -> `Ishaan` (person_name), intended 1x, actual evidence_count=1, active=False
- `mathew` -> `Matthew` (person_name), intended 2x, actual evidence_count=2, active=True
- `nirbhaya` -> `Nirbhaya Fund` (product_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "remind me to email ishan tomorrow" / Corrected: "remind me to email Ishaan tomorrow" -> learned: ishan->Ishaan (new_candidate)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "what is the capital of France" / Corrected: "what is the capital of France" -> learned: (nothing new)
- ASR: "ask mathew to join the call" / Corrected: "ask Matthew to join the call" -> learned: mathew->Matthew (new_candidate)
- ASR: "the nirbhaya service crashed again" / Corrected: "the Nirbhaya Fund service crashed again" -> learned: nirbhaya->Nirbhaya Fund (new_candidate)
- ASR: "remind me to email mathew tomorrow" / Corrected: "remind me to email Matthew tomorrow" -> learned: mathew->Matthew (activated)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "update nirbhaya to the latest version" / Corrected: "update Nirbhaya Fund to the latest version" -> learned: nirbhaya->Nirbhaya Fund (activated)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "the nirbhaya dashboard looks great" / Corrected: "the Nirbhaya Fund dashboard looks great" -> learned: nirbhaya->Nirbhaya Fund (already_active)

Follow-up recall test (unseen sentence per term):
- "can you tell ishan about the meeting" -> "Can you tell ishan about the meeting." [TN]
- "can you tell mathew about the meeting" -> "Can you tell Matthew about the meeting." [TP_useful_intervention]
- "install nirbhaya on my laptop" -> "Install Nirbhaya Fund on my laptop." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_028

Terms taught this session:
- `sophia` -> `Sophiya` (person_name), intended 1x, actual evidence_count=1, active=False
- `nu york` -> `New York` (place_name), intended 2x, actual evidence_count=0, active=False
- `gandhi nagar` -> `Gandhinagar` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "flying to gandhi nagar tomorrow" / Corrected: "flying to Gandhinagar tomorrow" -> learned: gandhi nagar->Gandhinagar (new_candidate)
- ASR: "meet sophia at noon" / Corrected: "meet Sophiya at noon" -> learned: sophia->Sophiya (new_candidate)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "we are relocating to nu york" / Corrected: "we are relocating to New York" -> learned: nu->New (new_candidate)
- ASR: "the conference is in gandhi nagar this year" / Corrected: "the conference is in Gandhinagar this year" -> learned: gandhi nagar->Gandhinagar (activated)
- ASR: "the office in nu york is closed" / Corrected: "the office in New York is closed" -> learned: nu->New (activated)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "the office in gandhi nagar is closed" / Corrected: "the office in Gandhinagar is closed" -> learned: gandhi nagar->Gandhinagar (already_active)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "send the report to sophia" -> "Send the report to sophia." [TN]
- "meeting is scheduled in nu york" -> "Meeting is scheduled in New york." [TN]
- "meeting is scheduled in gandhi nagar" -> "Meeting is scheduled in Gandhinagar." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_029

Terms taught this session:
- `chandigarh` -> `Chandigarh University` (place_name), intended 1x, actual evidence_count=1, active=False
- `iphon` -> `iPhone` (product_name), intended 2x, actual evidence_count=2, active=True
- `bombay` -> `Mumbai` (place_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "meeting is scheduled in bombay" / Corrected: "meeting is scheduled in Mumbai" -> learned: bombay->Mumbai (new_candidate)
- ASR: "the conference is in bombay this year" / Corrected: "the conference is in Mumbai this year" -> learned: bombay->Mumbai (activated)
- ASR: "check iphon settings" / Corrected: "check iPhone settings" -> learned: iphon->iPhone (new_candidate)
- ASR: "install iphon on my laptop" / Corrected: "install iPhone on my laptop" -> learned: iphon->iPhone (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "we are relocating to bombay" / Corrected: "we are relocating to Mumbai" -> learned: bombay->Mumbai (already_active)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "flying to chandigarh tomorrow" / Corrected: "flying to Chandigarh University tomorrow" -> learned: chandigarh->Chandigarh University (new_candidate)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "the office in chandigarh is closed" -> "The office in chandigarh is closed." [TN]
- "the iphon dashboard looks great" -> "The iPhone dashboard looks great." [TP_useful_intervention]
- "flying to bombay tomorrow" -> "Flying to Mumbai tomorrow." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_030

Terms taught this session:
- `sony xperia` -> `Sony Xperia Pro` (product_name), intended 1x, actual evidence_count=0, active=False
- `kavia` -> `Kavya` (person_name), intended 2x, actual evidence_count=2, active=True
- `steven` -> `Stephen` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "meet kavia at noon" / Corrected: "meet Kavya at noon" -> learned: kavia->Kavya (new_candidate)
- ASR: "call kavia now" / Corrected: "call Kavya now" -> learned: kavia->Kavya (activated)
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "send the report to steven" / Corrected: "send the report to Stephen" -> learned: steven->Stephen (new_candidate)
- ASR: "ask steven to join the call" / Corrected: "ask Stephen to join the call" -> learned: steven->Stephen (activated)
- ASR: "how many days until the weekend" / Corrected: "how many days until the weekend" -> learned: (nothing new)
- ASR: "check sony xperia settings" / Corrected: "check Sony Xperia Pro settings" -> learned: xperia->Xperia Pro (new_candidate)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "can you tell steven about the meeting" / Corrected: "can you tell Stephen about the meeting" -> learned: steven->Stephen (already_active)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "update sony xperia to the latest version" -> "Update sony xperia to the latest version." [TN]
- "can you tell kavia about the meeting" -> "Can you tell Kavya about the meeting." [TP_useful_intervention]
- "call steven now" -> "Call Stephen now." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_031

Terms taught this session:
- `arav` -> `Aarav` (person_name), intended 1x, actual evidence_count=1, active=False
- `samsung` -> `Samsung Galaxy` (product_name), intended 2x, actual evidence_count=2, active=True
- `gotham` -> `Gautam` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "read my latest email" / Corrected: "read my latest email" -> learned: (nothing new)
- ASR: "call arav now" / Corrected: "call Aarav now" -> learned: arav->Aarav (new_candidate)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "install samsung on my laptop" / Corrected: "install Samsung Galaxy on my laptop" -> learned: samsung->Samsung Galaxy (new_candidate)
- ASR: "restart the samsung app" / Corrected: "restart the Samsung Galaxy app" -> learned: samsung->Samsung Galaxy (activated)
- ASR: "can you tell gotham about the meeting" / Corrected: "can you tell Gautam about the meeting" -> learned: gotham->Gautam (new_candidate)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "what is the weather today" / Corrected: "what is the weather today" -> learned: (nothing new)
- ASR: "set a timer for ten minutes" / Corrected: "set a timer for ten minutes" -> learned: (nothing new)
- ASR: "call gotham now" / Corrected: "call Gautam now" -> learned: gotham->Gautam (activated)
- ASR: "send the report to gotham" / Corrected: "send the report to Gautam" -> learned: gotham->Gautam (already_active)

Follow-up recall test (unseen sentence per term):
- "ask arav to join the call" -> "Ask arav to join the call." [TN]
- "the samsung dashboard looks great" -> "The Samsung Galaxy dashboard looks great." [TP_useful_intervention]
- "meet gotham at noon" -> "Meet Gautam at noon." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_032

Terms taught this session:
- `megan` -> `Meghan` (person_name), intended 1x, actual evidence_count=1, active=False
- `nokia` -> `Nokio` (product_name), intended 2x, actual evidence_count=2, active=True
- `kris` -> `Chris` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "call kris now" / Corrected: "call Chris now" -> learned: kris->Chris (new_candidate)
- ASR: "set an alarm for seven am" / Corrected: "set an alarm for seven am" -> learned: (nothing new)
- ASR: "can you tell megan about the meeting" / Corrected: "can you tell Meghan about the meeting" -> learned: megan->Meghan (new_candidate)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "remind me to email kris tomorrow" / Corrected: "remind me to email Chris tomorrow" -> learned: kris->Chris (activated)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "meet kris at noon" / Corrected: "meet Chris at noon" -> learned: kris->Chris (already_active)
- ASR: "turn off the lights" / Corrected: "turn off the lights" -> learned: (nothing new)
- ASR: "install nokia on my laptop" / Corrected: "install Nokio on my laptop" -> learned: nokia->Nokio (new_candidate)
- ASR: "check nokia settings" / Corrected: "check Nokio settings" -> learned: nokia->Nokio (activated)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)

Follow-up recall test (unseen sentence per term):
- "ask megan to join the call" -> "Ask megan to join the call." [TN]
- "the nokia dashboard looks great" -> "The Nokio dashboard looks great." [TP_useful_intervention]
- "can you tell kris about the meeting" -> "Can you tell Chris about the meeting." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).

### user_033

Terms taught this session:
- `androyd` -> `Android` (product_name), intended 1x, actual evidence_count=1, active=False
- `prinanka` -> `Priyanka` (person_name), intended 2x, actual evidence_count=2, active=True
- `jessika` -> `Jessica` (person_name), intended 3x, actual evidence_count=3, active=True

Conversation fed through /observe:
- ASR: "can you tell jessika about the meeting" / Corrected: "can you tell Jessica about the meeting" -> learned: jessika->Jessica (new_candidate)
- ASR: "add milk to the shopping list" / Corrected: "add milk to the shopping list" -> learned: (nothing new)
- ASR: "what time is it" / Corrected: "what time is it" -> learned: (nothing new)
- ASR: "meet prinanka at noon" / Corrected: "meet Priyanka at noon" -> learned: prinanka->Priyanka (new_candidate)
- ASR: "install androyd on my laptop" / Corrected: "install Android on my laptop" -> learned: androyd->Android (new_candidate)
- ASR: "what is on my calendar today" / Corrected: "what is on my calendar today" -> learned: (nothing new)
- ASR: "how far is the nearest gas station" / Corrected: "how far is the nearest gas station" -> learned: (nothing new)
- ASR: "play some music" / Corrected: "play some music" -> learned: (nothing new)
- ASR: "remind me to email prinanka tomorrow" / Corrected: "remind me to email Priyanka tomorrow" -> learned: prinanka->Priyanka (activated)
- ASR: "meet jessika at noon" / Corrected: "meet Jessica at noon" -> learned: jessika->Jessica (activated)
- ASR: "remind me to email jessika tomorrow" / Corrected: "remind me to email Jessica tomorrow" -> learned: jessika->Jessica (already_active)

Follow-up recall test (unseen sentence per term):
- "check androyd settings" -> "Check androyd settings." [TN]
- "can you tell prinanka about the meeting" -> "Can you tell Priyanka about the meeting." [TP_useful_intervention]
- "call jessika now" -> "Call Jessica now." [TP_useful_intervention]

Filler false-positive check: 2 ordinary sentences tested, 0 false positive(s).
