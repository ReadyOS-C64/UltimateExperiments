"""Released PAL typing6/warm-caret4 scenario on an immutable packaged fixture.

Use --fixture PATH. No assembler or private product image substitution. The
original scenario adds its PLAIN source file to its own disposable working D81.
The original native source/pixel/font/catalog/stack/shim oracles are unchanged.
"""
import test_grid_typing_local_vice as released

if __name__ == '__main__':
    released.profile.scenario = released.scenario
    released.profile.main()
