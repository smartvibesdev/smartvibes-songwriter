From Gemini

You are an expert computational linguist specializing in phonetics and the ARPAbet notation system used by the CMU Pronouncing Dictionary (CMUdict). 

I am building a songwriting and rhyme-generation app. My core database is the standard CMUdict (approx. 134,000 words). While it covers about 95% of standard English, it lacks modern slang, pop culture proper nouns, brand names, and colloquial contractions frequently found in modern music lyrics (hip-hop, pop, rock, indie).

Your task is to generate a supplemental dictionary file to patch these gaps. 

Please output a list of 100 highly relevant modern words, slang terms, and musical vocabulary missing from standard CMUdict. Format the output EXACTLY like a CMUdict file:
- All words must be UPPERCASE.
- A single space separates the word from the start of its phonemes.
- Phonemes must use standard ARPAbet (with 0, 1, 2 stress markers on vowels).
- One entry per line.
- No introductory or concluding text—just the raw entries so I can copy-paste them directly into a text editor.

Please include a diverse mix of:
1. Modern Slang (e.g., FLEX, GHOSTED, BOUJEE, RIZZ, DELULU)
2. Music-specific slang & contractions (e.g., FINNA, TRYNA, GONNA, IMMA, BOOMAP)
3. Major brand names used in lyrics (e.g., GUCCI, TESLA, HENNY)
4. Highly relevant proper nouns (e.g., TIKTOK, BIEBER)

Example format expected:
BOUJEE B UW1 ZH IY0
FINNA F IH1 N AH0
