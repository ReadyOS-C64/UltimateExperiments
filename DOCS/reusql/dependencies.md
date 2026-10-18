# Third-party dependencies

The host test runner currently resolves Peddle's core from the pinned sibling
Zag64 checkout (`../../zig64/third_party/peddle`) so the foundation can share
the already-audited MIT source at commit
`c23e34a7e6516b284750b8c7caaa8c41948a407a`. ReuSQL64's configurable REU and
bulk-image adapter is maintained locally under `third_party/peddle/`.

Before ReuSQL64 becomes independently distributable, vendor that exact tree
here with its LICENSE and replace the sibling paths in `build.zig`.
