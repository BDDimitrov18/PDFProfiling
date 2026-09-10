"""Development refinement for continued contents sheets without a title heading."""
from archive_boundary import SCHEMA, decision, prompt as original_prompt


def prompt(variant,left,right):
    if variant!='typed_v3b':raise ValueError('Expected typed_v3b')
    original=original_prompt('typed_v3',left,right)
    before='''4. toc_section: LEFT is a contents/index page explicitly listing the explanatory
   note on RIGHT, with matching project discipline. A project COVER is not a
   contents page. Do not merge arbitrary explanatory notes or calculations.'''
    after='''4. toc_section: LEFT is a contents/index page or a CONTINUED CONTENTS sheet:
   short numbered section/drawing titles listed without explanatory prose. Such a
   sheet can lack the word СЪДЪРЖАНИЕ and can list only the later sections because
   the earlier entries were on the preceding index page. RIGHT begins the actual
   explanatory text of that same project discipline. A project COVER is not a
   contents page. A substantive technical list, specifications or narrative section
   is not a contents page. Do not merge arbitrary explanatory notes or calculations.
   Classify a continued contents sheet as left_kind=contents, not explanatory_note.'''
    if before not in original:raise ValueError('Parent prompt changed')
    return original.replace(before,after)
