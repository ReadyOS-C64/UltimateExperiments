"""Packaged whole-line styled typing; same native pixel/history/REU gates.

The style fixture begins with its markup opener. No asset substitution and no
private admission edits. Public profile owns8300/text8400; invoke --run --fixture.
"""
import test_geos_style_profile_vice as profile

profile.DOC = profile.timing.native.live.grid.native_text(
    '**interiorwords** omega.\r*interiorwords* omega.\r'
    '***interiorwords*** omega.\rAlpha interiorwords omega.\r'
    'Second plain row.\rTail.')

if __name__ == '__main__':
    profile.main()
