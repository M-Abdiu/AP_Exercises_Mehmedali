#!/usr/bin/env python3
"""
ELIZA (Weizenbaum-style, 1966) — command-line only.

This interpreter implements the mechanisms used by Weizenbaum’s ELIZA scripts:
- keyword scan + keystack with precedence
- clause trimming at punctuation (drop leading clauses w/o keywords; keep first clause w/ keywords)
- on-the-fly word substitution (R2/R3), without making substitution-only entries act as keywords
- decomposition patterns with 0 (any length), N (exact length), (/TAG ...) (DLIST tags), (* A B C) (any-of)
- reassembly cycling per decomposition
- (=KEY) links, PRE ... (=KEY), NEWKEY
- MEMORY rule (exactly 4), FIFO recall gated by a 1..4 counter (recall when LIMIT==4)
- required NONE rule

Separate from the interpreter are scripts for the conversation.
- Embedded are two scripts:
  1) Tape 100 (.TAPE. 100) — an early DOCTOR script from the MIT/CTSS printout era.
  2) The DOCTOR script published by Weizenbaum in CACM, Jan 1966, as an Appendix.
- The default is the published DOCTOR script. Choose with:
  python eliza_singlefile.py --builtin tape100
  python eliza_singlefile.py --builtin cacm1966
- Load an external script file:
  python eliza_singlefile.py --script /path/to/script.txt
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------
# Embedded scripts
# ---------------------------------------------------------------------

TAPE_100_SCRIPT = r"""; Transcript of an ELIZA script printed in a listing following the ELIZA
; source code in MIT archive document 02-000311051.pdf. The listing was
; found in a folder titled COMPUTER CONVERSATIONS 1965 and has the header
;
;    "PRINT,T0109,2531,.TAPE.,100      T0109 2531    1748.8     03/06"
;
; The date the listing was printed is therefore assumed to be 6 March 1965.
;
; This is a verbatim transcript except for whitespace, which has been
; changed for readability.

(HOW DO YOU DO.  I AM THE DOCTOR.  PLEASE SIT DOWN AT THE TYPEWRITER AND TELL ME YOUR PROBLEM.)

(IF 3
    ((0 IF 0)
        (DO YOU THINK ITS LIKELY THAT 3)
        (DO YOU WISH THAT 3)
        (WHAT DO YOU THINK ABOUT 3)
        (REALLY, 2 3)))

(HOW
    (=WHAT))

(WHEN
    (=WHAT))

(MEMORY MY
    (0 YOUR 0 = LETS DISCUSS FURTHER WHY YOUR 3)
    (0 YOUR 0 = EARLIER YOU SAID YOUR 3)
    (0 YOUR 0 = BUT YOUR 3)
    (0 YOUR 0 = DOES THAT HAVE ANYTHING TO DO WITH THE FACT THAT YOUR 3))

(NONE
    ((0)
        (I AM NOT SURE I UNDERSTAND YOU FULLY)
        (PLEASE GO ON)
        (WHAT DOES THAT SUGGEST TO YOU)
        (DO YOU FEEL STRONGLY ABOUT DISCUSSING SUCH THINGS)))

(PERHAPS
    ((0)
        (YOU DON'T SEEM QUITE CERTAIN)
        (WHY THE UNCERTAIN TONE)
        (CAN'T YOU BE MORE POSITIVE)
        (YOU AREN'T SURE)
        (DON'T YOU KNOW)))

(MAYBE
    (=PERHAPS))

(AM = ARE
    ((0 ARE YOU 0)
        (DO YOU BELIEVE YOU ARE 4)
        (WOULD YOU WANT TO BE 4)
        (YOU WISH I WOULD TELL YOU YOU ARE 4)
        (WHAT WOULD IT MEAN IF YOU WERE 4))
    ((0)
        (WHY DO YOU SAY 'AM')
        (I DON'T UNDERSTAND THAT)))

(ARE = AM
    ((0 AM I 0)
        (WHY ARE YOU INTERESTED IN WHETHER I AM 4 OR NOT)
        (WOULD YOU PREFER IF I WEREN'T 4)
        (PERHAPS I AM 4 IN YOUR FANTASIES)
        (DO YOU SOMETIMES THINK I AM 4))
    ((0 AM 0)
        (DID YOU THINK THEY MIGHT NOT BE 3)
        (WOULD YOU LIKE IT IF THEY WERE NOT 3)
        (WHAT IF THEY WERE NOT 3)
        (POSSIBLY THEY ARE 3)))

(YOUR = MY
    ((0 MY 0)
        (WHY ARE YOU CONCERNED OVER MY 3)
        (WHAT ABOUT YOUR OWN 3)
        (ARE YOU WORRIED ABOUT SOMEONE ELSES 3)
        (REALLY, MY 3)))

(WAS = WERE)
(WERE = WAS)
(ME = YOU)
(YOU'RE = I'M)
(I'M = YOU'RE)
(MYSELF = YOURSELF)
(YOURSELF = MYSELF)

(MOTHER DLIST(/NOUN FAMILY))
(FATHER DLIST(/NOUN FAMILY))
(SISTER DLIST(/FAMILY))
(BROTHER DLIST(/FAMILY))
(WIFE DLIST(/FAMILY))
(CHILDREN DLIST(/FAMILY))

(I = YOU
    ((0 YOU ARE 0 I 0)
        (PERHAPS YOU ARE 4 SOMEONE ELSE)
        (ARE YOU 4 ANYONE)
        (ARE YOU 4 ANYONE IN YOUR FAMILY)
        (PERHAPS YOU WISH I WERE 4 YOU 6))
    ((0 YOU ARE 0)
        (IS IT BECAUSE YOU ARE 4 THAT YOU CAME TO ME)
        (HOW LONG HAVE YOU BEEN 4)
        (DO YOU BELIEVE IT NORMAL TO BE 4)
        (DO YOU ENJOY BEING 4))
    ((0 YOU CAN'T 0)
        (HOW DO YOU KNOW YOU CAN'T 4)
        (HAVE YOU TRIED)
        (PERHAPS YOU COULD 4 NOW)
        (DO YOU REALLY WANT TO BE ABLE TO 4))
    ((0 YOU DON'T 0)
        (DON'T YOU REALLY 4)
        (WHY DON'T YOU 4)
        (DO YOU WISH TO BE ABLE TO 4)
        (DOES THAT TROUBLE YOU))
    ((0 YOU FEEL 0)
        (TELL ME MORE ABOUT SUCH FEELINGS)
        (DO YOU OFTEN FEEL 4)
        (DO YOU ENJOY FEELING 4)
        (OF WHAT DOES FEELING 4 REMIND YOU))
    ((0 YOU 0 I 0)
        (PERHAPS IN YOUR FANTASY WE 3 EACH OTHER)
        (DO YOU WISH TO 3 ME)
        (YOU SEEM TO NEED TO 3 ME)
        (DO YOU 3 ANYONE ELSE))
    ((0)
        (YOU SAY 1)
        (CAN YOU ELABORATE ON THAT)
        (DO YOU SAY 1 FOR SOME SPECIAL REASON)
        (THAT'S QUITE INTERESTING)))

(YOU = I
    ((0 I 0 YOU 0)
        (WHY DO YOU THINK I 3 YOU)
        (DID YOUR PARENTS 3 YOU))
    ((0 I AM 0)
        (WHAT MAKES YOU THINK I AM 4)
        (DOES IT PLEASE YOU TO BELIEVE I AM 4)
        (DO YOU SOMETIMES WISH YOU WERE 4)
        (PERHAPS YOU WOULD LIKE TO BE 4))
    ((0 I 0)
        (WE WERE DISCUSSING YOU - NOT ME)
        (OH, I 3)
        (YOU'RE NOT REALLY TALKING ABOUT ME - ARE YOU)
        (WHAT ARE YOUR FEELINGS NOW)))

(YES
    ((0)
        (YOU SEEM QUITE POSITIVE)
        (YOU ARE SURE)
        (I SEE)
        (I UNDERSTAND)))

(NO
    ((0)
        (ARE YOU SAYING 'NO' JUST TO BE NEGATIVE)
        (YOU ARE BEING A BIT NEGATIVE)
        (WHY NOT)
        (WHY 'NO')))

(MY = YOUR
    ((0 YOUR 0 (/FAMILY) 0)
        (TELL ME MORE ABOUT YOUR FAMILY)
        (WHO ELSE IN YOUR FAMILY 5)
        (YOUR 4)
        (WHAT ELSE COMES TO MIND WHEN YOU THINK OF YOUR 4))
    ((0 YOUR 0)
        (YOUR 3)
        (WHY DO YOU SAY YOUR 3)
        (DOES THAT SUGGEST ANYTHING ELSE WHICH BELONGS TO YOU)
        (IS IT IMPORTANT TO YOU THAT 2 3)))

(CAN
    ((0 CAN I 0)
        (YOU BELIEVE I CAN 4 DON'T YOU)
        (YOU WANT BE TO BE ABLE TO 4)
        (PERHAPS YOU WOULD LIKE TO BE ABLE TO 4 YOURSELF))
    ((0 CAN YOU 0)
        (WHETHER OR NOT YOU CAN 4 DEPENDS ON YOU MORE THAN ON ME)
        (DO YOU WANT TO BE ABLE TO 4)
        (PERHAPS YOU DON'T WANT TO 4)))

(WHAT
    ((0)
        (WHY DO YOU ASK)
        (DOES THAT QUESTION INTEREST YOU)
        (WHAT IS IT YOU REALLY WANT TO KNOW)
        (ARE SUCH QUESTIONS MUCH ON YOUR MIND)
        (WHAT ANSWER WOULD PLEASE YOU MOST)
        (WHAT DO YOU THINK)
        (WHAT COMES TO YOUR MIND WHEN YOU ASK THAT)
        (HAVE YOU ASKED SUCH QUESTIONS BEFORE)
        (HAVE YOU ASKED ANYONE ELSE)))

(BECAUSE
    ((0)
        (IS THAT THE REAL REASON)
        (DON'T ANY OTHER REASONS COME TO MIND)
        (DOES THAT REASON SEEM TO EXPLAIN ANYTHING ELSE)
        (WHAT OTHER REASONS MIGHT THERE BE)))

(WHY
    ((0 WHY DON'T I 0)
        (DO YOU BELIEVE I DON'T 5)
        (PERHAPS I WILL 5 IN GOOD TIME)
        (SHOULD YOU 5 YOURSELF)
        (YOU WANT ME TO 5))
    ((0 WHY CAN'T YOU 0)
        (DO YOU THINK YOU SHOULD BE ABLE TO 5)
        (DO YOU WANT TO BE ABLE TO 5)
        (DO YOU BELIEVE THIS WILL HELP YOU TO 5)
        (HAVE YOU ANY IDEA WHY YOU CAN'T 5))
    (= WHAT))

(EVERYONE 2
    ((0)
        (REALLY, EVERYONE)
        (CAN YOU THINK OF ANYONE IN PARTICULAR)
        (WHO, FOR EXAMPLE)
        (YOU ARE THINKING OF A VERY SPECIAL PERSON)
        (WHO, MAY I ASK)
        (SOMEONE SPECIAL PERHAPS)
        (YOU HAVE A PARTICULAR PERSON IN MIND, DON'T YOU)
        (WHO DO YOU THINK YOU'RE TALKING ABOUT)))

(EVERYBODY 2
    (= EVERYONE))

(NOBODY 2
    (=EVERYONE))

(NOONE 2
    (=EVERYONE))

(ALWAYS 1
    ((0)
        (CAN YOU THINK OF A SPECIFIC EXAMPLE)
        (WHEN)
        (WHAT INCIDENT ARE YOU THINKING OF)
        (REALLY, ALWAYS)))

()
"""

CACM_1966_SCRIPT = r""";
; APPENDIX. An Eliza Script
;
; Transcribed from Joseph Weizenbaum's article on page 36 of the January
; 1966 edition of Communications of the ACM titled 'ELIZA - A Computer
; Program For the Study of Natural Language Communication Between Man And
; Machine'.
;
; "Keywords and their associated transformation rules constitute the
; SCRIPT for a particular class of conversation. An important property of
; ELIZA is that a script is data; i.e., it is not part of the program
; itself." -- From the above mentioned article.
;
; Transcribed by Anthony Hay, December 2020
;
;
; Notes
;
; This is a verbatim transcription of the ELIZA script in the above
; mentioned CACM article, with the following caveats:
; a) Whitespace has been added to help reveal the structure of the
;    script.
; b) In the appendix six lines were printed twice adjacent to each other
;    (with exactly 34 lines between each duplicate), making the structure
;    nonsensical. These duplicates have been commented out of this
;    transcription.
; c) One closing bracket has been added and noted in a comment.
; d) There were no comments in the script in the CACM article.
;
;
; The script has the form of a series of S-expressions of varying
; composition. (Weizenbaum says "An ELIZA script consists mainly of a set
; of list structures...", but nowhere in the article are S-expressions or
; LISP mentioned. Perhaps it was too obvious to be noted.) Weizenbaum says
; ELIZA was written in MAD-Slip. It seems his original source code has
; been lost. Weizenbaum developed a library of FORTRAN functions for
; manipulating doubly-linked lists, which he called Slip (for Symmetric
; list processor).
;
; The most common transformation rule has the form:
;
;   (keyword [= replacement-keyword] [precedence]
;     [ ((decomposition-rule-0) (reassembly-rule-00) (reassembly-rule-01) ...)
;       ((decomposition-rule-1) (reassembly-rule-10) (reassembly-rule-11) ...)
;       ... ] )
;
; where [] denotes optional parts. Initially, ELIZA tries to match the
; decomposition rules against the input text only for the highest ranked
; keyword found in the input text. If a decomposition rule matches the
; input text the first associated reassembly rule is used to generate
; the output text. If there is more than one reassembly rule they are
; used in turn on successive matches.
;
; In the decomposition rules '0' matches zero or more words in the input.
; So (0 IF 0) matches "IF POSSIBLE" and "WHAT IF YOU DIE". Numbers in
; the reassembly rules refer to the parts of the decomposition rule
; match. 1 <empty>, 2 "IF", 3 "POSSIBLE" and 1 "WHAT", 2 "IF", 3 "YOU DIE"
; in the above examples. If the selected reassembly rule was (DO YOU THINK
; ITS LIKELY THAT 3) the text output would be "DO YOU THINK ITS LIKELY
; THAT YOU DIE".
;
;
; Each rule has one of the following six forms:
;
; R1. Plain vanilla transformation rule. [page 38 (a)]
;     (keyword [= keyword_substitution] [precedence]
;         [ ((decomposition_pattern) (reassembly_rule) (reassembly_rule) ... )
;            (decomposition_pattern) (reassembly_rule) (reassembly_rule) ... )
;            :
;            (decomposition_pattern) (reassembly_rule) (reassembly_rule) ... )) ] )
;   e.g.
;     (MY = YOUR 2
;         ((0 YOUR 0 (/FAMILY) 0)
;             (TELL ME MORE ABOUT YOUR FAMILY)
;             (WHO ELSE IN YOUR FAMILY 5)
;             (=WHAT)
;             (WHAT ELSE COMES TO MIND WHEN YOU THINK OF YOUR 4))
;         ((0 YOUR 0 (*SAD UNHAPPY DEPRESSED SICK ) 0)
;             (CAN YOU EXPLAIN WHAT MADE YOU 5))
;         ((0)
;             (NEWKEY)))
;
;
; R2. Simple word substitution with no further transformation rules. [page 39 (a)]
;     (keyword = keyword_substitution)
;   e.g.
;     (DONT = DON'T)
;     (ME = YOU)
;
;
; R3. Allow words to be given tags, with optional word substitution. [page 41 (j)]
;     (keyword [= keyword_substitution]
;         DLIST (/ <word> ... <word>))
;   e.g.
;         (FEEL               DLIST(/BELIEF))
;         (MOTHER             DLIST(/NOUN FAMILY))
;         (MOM = MOTHER       DLIST(/ FAMILY))
;
;
; R4. Link to another keyword transformation rule. [page 40 (c)]
;     (keyword [= keyword_substitution] [precedence]
;         (= equivalence_class))
;   e.g.
;         (HOW                (=WHAT))
;         (WERE = WAS         (=WAS))
;         (DREAMED = DREAMT 4 (=DREAMT))
;         (ALIKE 10           (=DIT))
;
;
; R5. As for R4 but allow pre-transformation before link. [page 40 (f)]
;     (keyword [= keyword_substitution]
;         ((decomposition_pattern)
;             (PRE (reassembly_rule) (=equivalence_class))))
;   e.g.
;     (YOU'RE = I'M
;         ((0 I'M 0)
;             (PRE (I ARE 3) (=YOU))))
;
;
; R6. Rule to 'pre-record' responses for later use. [page 41 (f)]
;     (MEMORY keyword
;         (decomposition_pattern_1 = reassembly_rule_1)
;         (decomposition_pattern_2 = reassembly_rule_2)
;         (decomposition_pattern_3 = reassembly_rule_3)
;         (decomposition_pattern_4 = reassembly_rule_4))
;   e.g.
;     (MEMORY MY
;         (0 YOUR 0 = LETS DISCUSS FURTHER WHY YOUR 3)
;         (0 YOUR 0 = EARLIER YOU SAID YOUR 3)
;         (0 YOUR 0 = BUT YOUR 3)
;         (0 YOUR 0 = DOES THAT HAVE ANYTHING TO DO WITH THE FACT THAT YOUR 3))
;
;
; In addition, there must be a NONE rule with the same form as R1. [page 41 (d)]
;     (NONE
;         ((0)
;             (reassembly_rule)
;             (reassembly_rule)
;             :
;             (reassembly_rule)) )
;   e.g.
;     (NONE
;         ((0)
;             (I AM NOT SURE I UNDERSTAND YOU FULLY)
;             (PLEASE GO ON)
;             (WHAT DOES THAT SUGGEST TO YOU)
;             (DO YOU FEEL STRONGLY ABOUT DISCUSSING SUCH THINGS)))
;
;
; For further details see Weizenbaum's article, or look at eliza.cpp.
;


(HOW DO YOU DO.  PLEASE TELL ME YOUR PROBLEM)

START

(SORRY
    ((0)
        (PLEASE DON'T APOLIGIZE)
        (APOLOGIES ARE NOT NECESSARY)
        (WHAT FEELINGS DO YOU HAVE WHEN YOU APOLOGIZE)
        (I'VE TOLD YOU THAT APOLOGIES ARE NOT REQUIRED)))

(DONT = DON'T)
(CANT = CAN'T)
(WONT = WON'T)

(REMEMBER 5
    ((0 YOU REMEMBER 0)
         (DO YOU OFTEN THINK OF 4)
         (DOES THINKING OF 4 BRING ANYTHING ELSE TO MIND)
         (WHAT ELSE DO YOU REMEMBER)
         (WHY DO YOU REMEMBER 4 JUST NOW)
         (WHAT IN THE PRESENT SITUATION REMINDS YOU OF 4)
         (WHAT IS THE CONNECTION BETWEEN ME AND 4))
    ((0 DO I REMEMBER 0)
         (DID YOU THINK I WOULD FORGET 5)
         (WHY DO YOU THINK I SHOULD RECALL 5 NOW)
         (WHAT ABOUT 5)
         (=WHAT)
         (YOU MENTIONED 5))
    ((0)
         (NEWKEY)))

(IF 3
    ((0 IF 0)
        (DO YOU THINK ITS LIKELY THAT 3)
        (DO YOU WISH THAT 3)
        (WHAT DO YOU THINK ABOUT 3)
        (REALLY, 2 3)))
; duplicate line removed: (WHAT DO YOU THINK ABOUT 3) (REALLY, 2 3)))

(DREAMT 4
    ((0 YOU DREAMT 0)
        (REALLY, 4)
        (HAVE YOU EVER FANTASIED 4 WHILE YOU WERE AWAKE)
        (HAVE YOU DREAMT 4 BEFORE)
        (=DREAM)
        (NEWKEY)))

(DREAMED = DREAMT 4 (=DREAMT))

(DREAM 3
    ((0)
        (WHAT DOES THAT DREAM SUGGEST TO YOU)
        (DO YOU DREAM OFTEN)
        (WHAT PERSONS APPEAR IN YOUR DREAMS)
        (DON'T YOU BELIEVE THAT DREAM HAS SOMETHING TO DO WITH YOUR PROBLEM)
        (NEWKEY)))

(DREAMS = DREAM 3 (=DREAM))

(HOW (=WHAT))
(WHEN (=WHAT))
(ALIKE 10 (=DIT))
(SAME 10 (=DIT))
(CERTAINLY (=YES))

(FEEL DLIST(/BELIEF))
(THINK DLIST(/BELIEF))
(BELIEVE DLIST(/BELIEF))
(WISH DLIST(/BELIEF))

(MEMORY MY
    (0 YOUR 0 = LETS DISCUSS FURTHER WHY YOUR 3)
    (0 YOUR 0 = EARLIER YOU SAID YOUR 3)
    (0 YOUR 0 = BUT YOUR 3)
    (0 YOUR 0 = DOES THAT HAVE ANYTHING TO DO WITH THE FACT THAT YOUR 3))

(NONE
    ((0)
        (I AM NOT SURE I UNDERSTAND YOU FULLY)
        (PLEASE GO ON)
        (WHAT DOES THAT SUGGEST TO YOU)
        (DO YOU FEEL STRONGLY ABOUT DISCUSSING SUCH THINGS)))

(PERHAPS
    ((0)
        (YOU DON'T SEEM QUITE CERTAIN)
        (WHY THE UNCERTAIN TONE)
        (CAN'T YOU BE MORE POSITIVE)
        (YOU AREN'T SURE)
        (DON'T YOU KNOW)))

(MAYBE (=PERHAPS))

(NAME 15
    ((0)
        (I AM NOT INTERESTED IN NAMES)
        (I'VE TOLD YOU BEFORE, I DON'T CARE ABOUT NAMES - PLEASE CONTINUE)))
; duplicate line removed: PLEASE CONTINUE)) )

(DEUTSCH (=XFREMD))
(FRANCAIS (=XFREMD))
(ITALIANO (=XFREMD))
(ESPANOL (=XFREMD))

(XFREMD
    ((0)
        (I AM SORRY, I SPEAK ONLY ENGLISH)))

(HELLO
    ((0)
        (HOW DO YOU DO.  PLEASE STATE YOUR PROBLEM)))

(COMPUTER 50
    ((0)
        (DO COMPUTERS WORRY YOU)
        (WHY DO YOU MENTION COMPUTERS)
        (WHAT DO YOU THINK MACHINES HAVE TO DO WITH YOUR PROBLEM)
        (DON'T YOU THINK COMPUTERS CAN HELP PEOPLE)
        (WHAT ABOUT MACHINES WORRIES YOU)
        (WHAT DO YOU THINK ABOUT MACHINES)))

(MACHINE 50 (=COMPUTER))
(MACHINES 50 (=COMPUTER))
(COMPUTERS 50 (=COMPUTER))

(AM = ARE
    ((0 ARE YOU 0)
        (DO YOU BELIEVE YOU ARE 4)
        (WOULD YOU WANT TO BE 4)
        (YOU WISH I WOULD TELL YOU YOU ARE 4)
        (WHAT WOULD IT MEAN IF YOU WERE 4)
        (=WHAT))
    ((0)
        (WHY DO YOU SAY 'AM')
        (I DON'T UNDERSTAND THAT)))

(ARE
    ((0 ARE I 0)
        (WHY ARE YOU INTERESTED IN WHETHER I AM 4 OR NOT)
        (WOULD YOU PREFER IF I WEREN'T 4)
        (PERHAPS I AM 4 IN YOUR FANTASIES)
        (DO YOU SOMETIMES THINK I AM 4)
        (=WHAT))
    ((0 ARE 0)
        (DID YOU THINK THEY MIGHT NOT BE 3)
        (WOULD YOU LIKE IT IF THEY WERE NOT 3)
        (WHAT IF THEY WERE NOT 3)
        (POSSIBLY THEY ARE 3)))

(YOUR = MY
    ((0 MY 0)
        (WHY ARE YOU CONCERNED OVER MY 3)
        (WHAT ABOUT YOUR OWN 3)
        (ARE YOU WORRIED ABOUT SOMEONE ELSES 3)
        (REALLY, MY 3)))

(WAS 2
    ((0 WAS YOU 0)
        (WHAT IF YOU WERE 4)
        (DO YOU THINK YOU WERE 4)
        (WERE YOU 4)
        (WHAT WOULD IT MEAN IF YOU WERE 4)
        (WHAT DOES ' 4 ' SUGGEST TO YOU)
        (=WHAT))
    ((0 YOU WAS 0)
        (WERE YOU REALLY)
        (WHY DO YOU TELL ME YOU WERE 4 NOW)
; duplicate line removed: (WERE YOU REALLY) (WHY DO YOU TELL ME YOU WERE 4 NOW)
        (PERHAPS I ALREADY KNEW YOU WERE 4))
    ((0 WAS I 0)
        (WOULD YOU LIKE TO BELIEVE I WAS 4)
        (WHAT SUGGESTS THAT I WAS 4)
        (WHAT DO YOU THINK)
        (PERHAPS I WAS 4)
        (WHAT IF I HAD BEEN 4))
    ((0)
        (NEWKEY)))

(WERE = WAS (=WAS))
(ME = YOU)

(YOU'RE = I'M
    ((0 I'M 0)
        (PRE (I ARE 3) (=YOU))))

(I'M = YOU'RE
    ((0 YOU'RE 0)
        (PRE (YOU ARE 3) (=I))))

(MYSELF = YOURSELF)
(YOURSELF = MYSELF)

(MOTHER DLIST(/NOUN FAMILY))
(MOM = MOTHER DLIST(/ FAMILY))
(DAD = FATHER DLIST(/ FAMILY))
(FATHER DLIST(/NOUN FAMILY))
(SISTER DLIST(/FAMILY))
(BROTHER DLIST(/FAMILY))
(WIFE DLIST(/FAMILY))
(CHILDREN DLIST(/FAMILY))

(I = YOU
    ((0 YOU (* WANT NEED) 0)
        (WHAT WOULD IT MEAN TO YOU IF YOU GOT 4)
        (WHY DO YOU WANT 4)
        (SUPPOSE YOU GOT 4 SOON)
        (WHAT IF YOU NEVER GOT 4)
        (WHAT WOULD GETTING 4 MEAN TO YOU)
        (WHAT DOES WANTING 4 HAVE TO DO WITH THIS DISCUSSION))
    ((0 YOU ARE 0 (*SAD UNHAPPY DEPRESSED SICK ) 0)
        (I AM SORRY TO HEAR YOU ARE 5)
        (DO YOU THINK COMING HERE WILL HELP YOU NOT TO BE 5)
        (I'M SURE ITS NOT PLEASANT TO BE 5)
        (CAN YOU EXPLAIN WHAT MADE YOU 5))
    ((0 YOU ARE 0 (*HAPPY ELATED GLAD BETTER) 0)
        (HOW HAVE I HELPED YOU TO BE 5)
        (HAS YOUR TREATMENT MADE YOU 5)
        (WHAT MAKES YOU 5 JUST NOW)
        (CAN YOU EXPLAIN WHY YOU ARE SUDDENLY 5))
    ((0 YOU WAS 0)
        (=WAS))
; duplicate line removed: ((0 YOU WAS 0) (=WAS))
    ((0 YOU (/BELIEF) YOU 0)
        (DO YOU REALLY THINK SO)
        (BUT YOU ARE NOT SURE YOU 5)
        (DO YOU REALLY DOUBT YOU 5))
    ((0 YOU 0 (/BELIEF) 0 I 0)
        (=YOU))
    ((0 YOU ARE 0)
        (IS IT BECAUSE YOU ARE 4 THAT YOU CAME TO ME)
        (HOW LONG HAVE YOU BEEN 4)
        (DO YOU BELIEVE IT NORMAL TO BE 4)
        (DO YOU ENJOY BEING 4))
    ((0 YOU (* CAN'T CANNOT) 0)
        (HOW DO YOU KNOW YOU CAN'T 4)
        (HAVE YOU TRIED)
        (PERHAPS YOU COULD 4 NOW)
        (DO YOU REALLY WANT TO BE ABLE TO 4))
    ((0 YOU DON'T 0)
        (DON'T YOU REALLY 4)
        (WHY DON'T YOU 4)
        (DO YOU WISH TO BE ABLE TO 4)
        (DOES THAT TROUBLE YOU))
    ((0 YOU FEEL 0)
        (TELL ME MORE ABOUT SUCH FEELINGS)
        (DO YOU OFTEN FEEL 4)
        (DO YOU ENJOY FEELING 4)
        (OF WHAT DOES FEELING 4 REMIND YOU))
    ((0 YOU 0 I 0)
        (PERHAPS IN YOUR FANTASY WE 3 EACH OTHER)
        (DO YOU WISH TO 3 ME)
        (YOU SEEM TO NEED TO 3 ME)
        (DO YOU 3 ANYONE ELSE))
    ((0)
        (YOU SAY 1)
        (CAN YOU ELABORATE ON THAT)
        (DO YOU SAY 1 FOR SOME SPECIAL REASON)
        (THAT'S QUITE INTERESTING)))

(YOU = I
    ((0 I REMIND YOU OF 0)
        (=DIT))
    ((0 I ARE 0)
        (WHAT MAKES YOU THINK I AM 4)
        (DOES IT PLEASE YOU TO BELIEVE I AM 4)
        (DO YOU SOMETIMES WISH YOU WERE 4)
        (PERHAPS YOU WOULD LIKE TO BE 4))
    ((0 I 0 YOU)
        (WHY DO YOU THINK I 3 YOU)
        (YOU LIKE TO THINK I 3 YOU - DON'T YOU)
        (WHAT MAKES YOU THINK I 3 YOU)
        (REALLY, I 3 YOU)
        (DO YOU WISH TO BELIEVE I 3 YOU)
; duplicate line removed: (REALLY, I 3 YOU) (DO YOU WISH TO BELIEVE I 3 YOU)
        (SUPPOSE I DID 3 YOU - WHAT WOULD THAT MEAN)
        (DOES SOMEONE ELSE BELIEVE I 3 YOU))
    ((0 I 0)
        (WE WERE DISCUSSING YOU - NOT ME)
        (OH, I 3)
        (YOU'RE NOT REALLY TALKING ABOUT ME - ARE YOU)
        (WHAT ARE YOUR FEELINGS NOW)))

(YES
    ((0)
        (YOU SEEM QUITE POSITIVE)
        (YOU ARE SURE)
        (I SEE)
        (I UNDERSTAND)))

(NO
    ((0)
        (ARE YOU SAYING 'NO' JUST TO BE NEGATIVE)
        (YOU ARE BEING A BIT NEGATIVE)
        (WHY NOT)
        (WHY 'NO')))

(MY = YOUR 2
    ((0 YOUR 0 (/FAMILY) 0)
        (TELL ME MORE ABOUT YOUR FAMILY)
        (WHO ELSE IN YOUR FAMILY 5)
        (YOUR 4)
        (WHAT ELSE COMES TO MIND WHEN YOU THINK OF YOUR 4))
    ((0 YOUR 0)
        (YOUR 3)
        (WHY DO YOU SAY YOUR 3)
        (DOES THAT SUGGEST ANYTHING ELSE WHICH BELONGS TO YOU)
        (IS IT IMPORTANT TO YOU THAT 2 3)))

(CAN
    ((0 CAN I 0)
        (YOU BELIEVE I CAN 4 DON'T YOU)
        (=WHAT)
        (YOU WANT ME TO BE ABLE TO 4)
        (PERHAPS YOU WOULD LIKE TO BE ABLE TO 4 YOURSELF))
    ((0 CAN YOU 0)
        (WHETHER OR NOT YOU CAN 4 DEPENDS ON YOU MORE THAN ON ME)
        (DO YOU WANT TO BE ABLE TO 4)
        (PERHAPS YOU DON'T WANT TO 4)
        (=WHAT)))

(WHAT
    ((0)
        (WHY DO YOU ASK)
        (DOES THAT QUESTION INTEREST YOU)
        (WHAT IS IT YOU REALLY WANT TO KNOW)
        (ARE SUCH QUESTIONS MUCH ON YOUR MIND)
        (WHAT ANSWER WOULD PLEASE YOU MOST)
        (WHAT DO YOU THINK)
        (WHAT COMES TO YOUR MIND WHEN YOU ASK THAT)
        (HAVE YOU ASKED SUCH QUESTIONS BEFORE)
        (HAVE YOU ASKED ANYONE ELSE)))

(BECAUSE
    ((0)
        (IS THAT THE REAL REASON)
        (DON'T ANY OTHER REASONS COME TO MIND)
        (DOES THAT REASON SEEM TO EXPLAIN ANYTHING ELSE)
        (WHAT OTHER REASONS MIGHT THERE BE)))

(WHY
    ((0 WHY DON'T I 0)
        (DO YOU BELIEVE I DON'T 5)
        (PERHAPS I WILL 5 IN GOOD TIME)
        (SHOULD YOU 5 YOURSELF)
        (YOU WANT ME TO 5)
        (=WHAT))
; duplicate line removed: (=WHAT))
    ((0 WHY CAN'T YOU 0)
        (DO YOU THINK YOU SHOULD BE ABLE TO 5)
        (DO YOU WANT TO BE ABLE TO 5)
        (DO YOU BELIEVE THIS WILL HELP YOU TO 5)
        (HAVE YOU ANY IDEA WHY YOU CAN'T 5)
        (=WHAT)))
; extraneous (=WHAT)) removed
; and missing final ')' added

(EVERYONE 2
    ((0 (* EVERYONE EVERYBODY NOBODY NOONE) 0)
        (REALLY, 2)
        (SURELY NOT 2)
        (CAN YOU THINK OF ANYONE IN PARTICULAR)
        (WHO, FOR EXAMPLE)
        (YOU ARE THINKING OF A VERY SPECIAL PERSON)
        (WHO, MAY I ASK)
        (SOMEONE SPECIAL PERHAPS)
        (YOU HAVE A PARTICULAR PERSON IN MIND, DON'T YOU)
        (WHO DO YOU THINK YOU'RE TALKING ABOUT)))

(EVERYBODY 2 (= EVERYONE))
(NOBODY 2 (= EVERYONE))
(NOONE 2 (= EVERYONE))

(ALWAYS 1
    ((0)
        (CAN YOU THINK OF A SPECIFIC EXAMPLE)
        (WHEN)
        (WHAT INCIDENT ARE YOU THINKING OF)
        (REALLY, ALWAYS)))

(LIKE 10
    ((0 (*AM IS ARE WAS) 0 LIKE 0)
        (=DIT))
    ((0)
        (NEWKEY)))

(DIT
    ((0)
        (IN WHAT WAY)
        (WHAT RESEMBLANCE DO YOU SEE)
        (WHAT DOES THAT SIMILARITY SUGGEST TO YOU)
        (WHAT OTHER CONNECTIONS DO YOU SEE)
        (WHAT DO YOU SUPPOSE THAT RESEMBLANCE MEANS)
        (WHAT IS THE CONNECTION, DO YOU SUPPOSE)
        (COULD THERE REALLY BE SOME CONNECTION)
        (HOW)))

()

; --- End of ELIZA script ---
"""


# ---------------------------------------------------------------------
# Script tokenizer / S-expression parser
# ---------------------------------------------------------------------

_PUNCT = {".", ",", "?", "!", ";", ":"}
_SCRIPT_SINGLE = {"(", ")", "=", "*", "/"} | _PUNCT


def _strip_script_comments(text: str) -> str:
    # Script comments use ';' to end-of-line.
    out_lines: List[str] = []
    for line in text.splitlines():
        if ";" in line:
            line = line.split(";", 1)[0]
        out_lines.append(line)
    return "\n".join(out_lines)


def _tokenize_script(text: str) -> List[str]:
    text = _strip_script_comments(text)
    toks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c in _SCRIPT_SINGLE:
            toks.append(c)
            i += 1
            continue
        j = i
        while j < n and (not text[j].isspace()) and (text[j] not in _SCRIPT_SINGLE):
            j += 1
        toks.append(text[i:j].upper())
        i = j

    # split trailing punctuation like HELLO. => HELLO .
    split: List[str] = []
    for t in toks:
        if len(t) >= 2 and t[-1] in _PUNCT and all(ch not in _SCRIPT_SINGLE for ch in t[:-1]):
            split.append(t[:-1])
            split.append(t[-1])
        else:
            split.append(t)
    return [t for t in split if t]


def _parse_sexpr(tokens: Sequence[str]) -> List[Any]:
    pos = 0

    def parse_one() -> Any:
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("Unexpected EOF while parsing script")
        t = tokens[pos]
        pos += 1
        if t == "(":
            lst: List[Any] = []
            while True:
                if pos >= len(tokens):
                    raise ValueError("Unclosed '(' in script")
                if tokens[pos] == ")":
                    pos += 1
                    return lst
                lst.append(parse_one())
        if t == ")":
            raise ValueError("Unexpected ')'")
        return t

    exprs: List[Any] = []
    while pos < len(tokens):
        exprs.append(parse_one())
    return exprs


# ---------------------------------------------------------------------
# Script IR
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class DecompTerm:
    kind: str  # WORD | COUNT | TAGS | ANYOF
    value: Any


@dataclass(frozen=True)
class Reasm:
    kind: str  # PATTERN | REF | NEWKEY | PRE
    value: Any


@dataclass
class Transform:
    decomp: List[DecompTerm]
    reassemblies: List[Reasm]
    next_idx: int = 0  # cycle through reassemblies


@dataclass
class Rule:
    keyword: str
    substitute: Optional[str] = None
    precedence: int = 0
    tags: List[str] = field(default_factory=list)     # DLIST(/TAG ...)
    transforms: List[Transform] = field(default_factory=list)
    reference: Optional[str] = None                   # (=OTHER)

    def has_transformation(self) -> bool:
        return bool(self.transforms) or bool(self.reference)


@dataclass
class MemoryRule:
    keyword: str
    transforms: List[Transform]                       # exactly 4
    fifo: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------
# Compile helpers
# ---------------------------------------------------------------------

def _is_int_atom(a: Any) -> bool:
    return isinstance(a, str) and a.isdigit()


def _compile_decomp_terms(sexpr_list: List[Any]) -> List[DecompTerm]:
    terms: List[DecompTerm] = []
    for x in sexpr_list:
        if isinstance(x, list):
            if not x:
                raise ValueError("Empty list in decomposition pattern")
            head = x[0]
            if head == "/":         # (/TAG1 TAG2 ...)
                terms.append(DecompTerm("TAGS", [str(t).upper() for t in x[1:]]))
            elif head == "*":       # (* A B C)
                terms.append(DecompTerm("ANYOF", [str(t).upper() for t in x[1:]]))
            else:
                raise ValueError(f"Unknown list term in decomposition: {x}")
        else:
            atom = str(x).upper()
            if atom.isdigit():
                terms.append(DecompTerm("COUNT", int(atom)))
            else:
                terms.append(DecompTerm("WORD", atom))
    return terms


def _compile_reasm_pattern(sexpr_list: Any) -> List[Union[str, Tuple[str, int]]]:
    if not isinstance(sexpr_list, list):
        raise ValueError("Reassembly pattern must be a list")
    out: List[Union[str, Tuple[str, int]]] = []
    for x in sexpr_list:
        if isinstance(x, list):
            raise ValueError("Nested lists not allowed in reassembly pattern")
        atom = str(x).upper()
        if atom.isdigit():
            out.append(("IDX", int(atom)))  # 1-based index into decomposition parts
        else:
            out.append(atom)
    return out


def _compile_reasm(rule_sexpr: Any) -> Reasm:
    if not isinstance(rule_sexpr, list) or not rule_sexpr:
        raise ValueError("Reassembly rule must be a non-empty list")
    head = rule_sexpr[0]
    if head == "=":
        if len(rule_sexpr) != 2:
            raise ValueError(f"Malformed (=KEY) reassembly: {rule_sexpr}")
        return Reasm("REF", str(rule_sexpr[1]).upper())
    if head == "NEWKEY":
        return Reasm("NEWKEY", None)
    if head == "PRE":
        # (PRE ( ... ) (=KEY))
        if len(rule_sexpr) != 3:
            raise ValueError(f"Malformed PRE rule: {rule_sexpr}")
        pattern = _compile_reasm_pattern(rule_sexpr[1])
        ref = rule_sexpr[2]
        if not (isinstance(ref, list) and len(ref) == 2 and ref[0] == "="):
            raise ValueError(f"Malformed PRE reference: {rule_sexpr}")
        return Reasm("PRE", (pattern, str(ref[1]).upper()))
    return Reasm("PATTERN", _compile_reasm_pattern(rule_sexpr))


def _realize(tokens: List[str]) -> str:
    out: List[str] = []
    for t in tokens:
        if t in _PUNCT and out:
            out[-1] = out[-1] + t
        else:
            out.append(t)
    return " ".join(out)


def _apply_reasm_pattern(pattern: List[Union[str, Tuple[str, int]]], parts: List[List[str]]) -> List[str]:
    out: List[str] = []
    for t in pattern:
        if isinstance(t, tuple) and t[0] == "IDX":
            idx = t[1]
            if 1 <= idx <= len(parts):
                out.extend(parts[idx - 1])
        else:
            out.append(str(t))
    return out


def _build_tagmap(rules: Dict[str, Rule]) -> Dict[str, List[str]]:
    tagmap: Dict[str, List[str]] = {}
    for kw, rule in rules.items():
        for tg in rule.tags:
            tagmap.setdefault(tg, [])
            if kw not in tagmap[tg]:
                tagmap[tg].append(kw)
    return tagmap


def _match_decomp(decomp: List[DecompTerm], words: List[str], tagmap: Dict[str, List[str]]) -> Optional[List[List[str]]]:
    def match_at(i_term: int, i_word: int, parts: List[List[str]]) -> Optional[List[List[str]]]:
        if i_term == len(decomp):
            return parts if i_word == len(words) else None

        term = decomp[i_term]

        if term.kind == "WORD":
            if i_word < len(words) and words[i_word] == term.value:
                return match_at(i_term + 1, i_word + 1, parts + [[words[i_word]]])
            return None

        if term.kind == "TAGS":
            if i_word >= len(words):
                return None
            w = words[i_word]
            for tg in term.value:
                if w in tagmap.get(tg, []):
                    return match_at(i_term + 1, i_word + 1, parts + [[w]])
            return None

        if term.kind == "ANYOF":
            if i_word < len(words) and words[i_word] in term.value:
                return match_at(i_term + 1, i_word + 1, parts + [[words[i_word]]])
            return None

        cnt = int(term.value)
        if cnt > 0:
            if i_word + cnt <= len(words):
                return match_at(i_term + 1, i_word + cnt, parts + [words[i_word : i_word + cnt]])
            return None

        for take in range(0, len(words) - i_word + 1):
            res = match_at(i_term + 1, i_word + take, parts + [words[i_word : i_word + take]])
            if res is not None:
                return res
        return None

    return match_at(0, 0, [])


def _compile_script(exprs: List[Any]) -> Tuple[str, Dict[str, Rule], MemoryRule]:
    if not exprs or not isinstance(exprs[0], list):
        raise ValueError("Script must start with an opening remarks list")

    opening = _realize([str(x).upper() for x in exprs[0]])

    i = 1
    if i < len(exprs) and exprs[i] == "START":
        i += 1

    rules: Dict[str, Rule] = {}
    mem_rule: Optional[MemoryRule] = None

    def compile_keyword_rule(sexpr: List[Any]) -> None:
        keyword = str(sexpr[0]).upper()
        if keyword in rules:
            raise ValueError(f"Duplicate keyword rule: {keyword}")
        rule = Rule(keyword=keyword)

        j = 1
        while j < len(sexpr):
            item = sexpr[j]

            if item == "=":
                j += 1
                rule.substitute = str(sexpr[j]).upper()
                j += 1
                continue

            if item == "DLIST":
                j += 1
                taglist = sexpr[j]
                if not (isinstance(taglist, list) and taglist and taglist[0] == "/"):
                    raise ValueError(f"Malformed DLIST in {keyword}: {taglist}")
                rule.tags = [str(t).upper() for t in taglist[1:]]
                j += 1
                continue

            if _is_int_atom(item):
                rule.precedence = int(item)
                j += 1
                continue

            if isinstance(item, list):
                if item and item[0] == "=":
                    if len(item) != 2:
                        raise ValueError(f"Malformed (=REF) in {keyword}: {item}")
                    rule.reference = str(item[1]).upper()
                    j += 1
                    continue

                if not item or not isinstance(item[0], list):
                    raise ValueError(f"Malformed transform in {keyword}: {item}")
                decomp_terms = _compile_decomp_terms(item[0])
                reassemblies = [_compile_reasm(r) for r in item[1:]]
                if not reassemblies:
                    raise ValueError(f"No reassemblies in {keyword} transform: {item}")
                rule.transforms.append(Transform(decomp=decomp_terms, reassemblies=reassemblies))
                j += 1
                continue

            raise ValueError(f"Unexpected item in keyword rule {keyword}: {item}")

        rules[keyword] = rule

    def compile_memory_rule(sexpr: List[Any]) -> None:
        nonlocal mem_rule
        if len(sexpr) < 3:
            raise ValueError("Malformed MEMORY rule")
        mem_kw = str(sexpr[1]).upper()
        transforms: List[Transform] = []
        for t in sexpr[2:]:
            if not isinstance(t, list) or "=" not in t:
                raise ValueError(f"Malformed MEMORY transform: {t}")
            k = t.index("=")
            left = t[:k]
            right = t[k + 1 :]
            decomp_terms = _compile_decomp_terms(left)
            reasm = Reasm("PATTERN", _compile_reasm_pattern(right))
            transforms.append(Transform(decomp=decomp_terms, reassemblies=[reasm]))
        if len(transforms) != 4:
            raise ValueError("MEMORY must have exactly 4 transforms (1966 behavior)")
        mem_rule = MemoryRule(keyword=mem_kw, transforms=transforms)

    while i < len(exprs):
        e = exprs[i]
        i += 1
        if e == []:
            break
        if not isinstance(e, list) or not e:
            continue
        head = str(e[0]).upper()
        if head == "MEMORY":
            compile_memory_rule(e)
        else:
            compile_keyword_rule(e)

    if mem_rule is None:
        raise ValueError("Script must define a MEMORY rule")
    if "NONE" not in rules:
        raise ValueError("Script must define a NONE rule")
    if mem_rule.keyword not in rules:
        raise ValueError("MEMORY keyword must also be an ordinary keyword rule")

    return opening, rules, mem_rule


class Eliza:
    def __init__(self, opening: str, rules: Dict[str, Rule], mem_rule: MemoryRule):
        self.opening = opening
        self.rules = rules
        self.mem_rule = mem_rule
        self.tagmap = _build_tagmap(rules)

        self.limit = 0  # cycles 1..4

        self._alias_no_apos: Dict[str, str] = {}
        for kw in rules.keys():
            if "'" in kw:
                self._alias_no_apos[kw.replace("'", "")] = kw

    @staticmethod
    def _split_user_input(text: str) -> List[str]:
        s = text.strip().upper()
        toks: List[str] = []
        cur: List[str] = []
        for ch in s:
            if ch.isalnum() or ch in ("'", "-"):
                cur.append(ch)
            else:
                if cur:
                    toks.append("".join(cur))
                    cur = []
                if ch in _PUNCT:
                    toks.append(ch)
        if cur:
            toks.append("".join(cur))
        return toks

    @staticmethod
    def _is_delimiter(tok: str) -> bool:
        return tok in {",", ".", "?", "!", ";", ":"}

    def _normalize_token_for_dict(self, tok: str) -> str:
        if tok in self.rules:
            return tok
        if tok in self._alias_no_apos:
            return self._alias_no_apos[tok]
        if "'" in tok:
            stripped = tok.replace("'", "")
            if stripped in self.rules:
                return stripped
            if stripped in self._alias_no_apos:
                return self._alias_no_apos[stripped]
        return tok

    def _scan_and_substitute(self, tokens: List[str]) -> Tuple[List[str], List[str]]:
        words = list(tokens)
        keystack: List[str] = []
        top_rank = 0

        i = 0
        while i < len(words):
            w = words[i]
            if self._is_delimiter(w):
                if not keystack:
                    words = words[i + 1 :]
                    i = 0
                    continue
                words = words[:i]
                break

            w_norm = self._normalize_token_for_dict(w)
            words[i] = w_norm

            rule = self.rules.get(w_norm)
            if rule:
                if rule.has_transformation():
                    if (not keystack) or (rule.precedence > top_rank):
                        if rule.precedence > top_rank:
                            top_rank = rule.precedence
                        keystack.insert(0, w_norm)
                    else:
                        keystack.append(w_norm)

                if rule.substitute:
                    words[i] = rule.substitute

            i += 1

        words = [w for w in words if not self._is_delimiter(w)]
        return words, keystack

    def _apply_rule(self, keyword: str, words: List[str]) -> Tuple[str, str, Optional[str]]:
        rule = self.rules.get(keyword)
        if rule is None:
            return "INAPPLICABLE", "", None

        for tr in rule.transforms:
            parts = _match_decomp(tr.decomp, words, self.tagmap)
            if parts is None:
                continue

            r = tr.reassemblies[tr.next_idx]
            tr.next_idx = (tr.next_idx + 1) % len(tr.reassemblies)

            if r.kind == "PATTERN":
                return "COMPLETE", _realize(_apply_reasm_pattern(r.value, parts)), None
            if r.kind == "REF":
                return "LINK", "", str(r.value)
            if r.kind == "NEWKEY":
                return "NEWKEY", "", None
            if r.kind == "PRE":
                pattern, refkw = r.value
                words[:] = _apply_reasm_pattern(pattern, parts)
                return "LINK", "", refkw

        if rule.reference:
            return "LINK", "", rule.reference

        return "INAPPLICABLE", "", None

    def respond(self, user_text: str) -> str:
        self.limit = (self.limit % 4) + 1

        tokens = self._split_user_input(user_text)
        words, keystack = self._scan_and_substitute(tokens)

        if words and words[0] in {"BYE", "GOODBYE", "QUIT", "EXIT"}:
            return "GOODBYE."

        if not keystack and self.limit == 4 and self.mem_rule.fifo:
            return self.mem_rule.fifo.pop(0)

        steps = 0
        while keystack:
            steps += 1
            if steps > 200:
                break

            kw = keystack.pop(0)

            if kw == self.mem_rule.keyword:
                tr = random.choice(self.mem_rule.transforms)
                parts = _match_decomp(tr.decomp, words, self.tagmap)
                if parts is not None:
                    self.mem_rule.fifo.append(_realize(_apply_reasm_pattern(tr.reassemblies[0].value, parts)))

            action, out, link = self._apply_rule(kw, words)
            if action == "COMPLETE":
                return out
            if action == "LINK" and link:
                keystack.insert(0, link)
                continue
            if action == "NEWKEY":
                if not keystack:
                    break
                continue
            break

        action, out, _ = self._apply_rule("NONE", words)
        return out if action == "COMPLETE" else "PLEASE GO ON"


def build_eliza(script_text: str) -> Eliza:
    toks = _tokenize_script(script_text)
    exprs = _parse_sexpr(toks)
    opening, rules, mem_rule = _compile_script(exprs)
    return Eliza(opening, rules, mem_rule)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", help="Path to a script file (overrides embedded scripts)")
    ap.add_argument("--builtin", choices=["tape100", "cacm1966"], default="cacm1966",
                    help="Choose one of the embedded scripts (default: cacm1966)")
    args = ap.parse_args(argv)

    if args.script:
        with open(args.script, "r", encoding="utf-8") as f:
            script_text = f.read()
    else:
        script_text = TAPE_100_SCRIPT if args.builtin == "tape100" else CACM_1966_SCRIPT

    try:
        bot = build_eliza(script_text)
    except Exception as e:
        print(f"Failed to load script: {e}", file=sys.stderr)
        return 2

    print("ELIZA:", bot.opening)
    while True:
        try:
            s = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nELIZA: GOODBYE.")
            return 0

        if not s:
            print("ELIZA: GOODBYE.")
            return 0

        print("ELIZA:", bot.respond(s))


if __name__ == "__main__":
    raise SystemExit(main())
