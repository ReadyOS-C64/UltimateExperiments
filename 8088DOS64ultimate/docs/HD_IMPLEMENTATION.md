# Hard-disk implementation and copied code

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The normal build contains a sixth HD overlay and a separate 3,584-byte executable window at host F000–FDFF. HD is disabled in the shipped configuration. DOS continues to own FAT, file handles, application loading and INT 21h. The backend transports raw sectors through native Ultimate file operations.

## Ownership and startup

The six 2 KiB startup assets at 6000, 6800, 8000, 8800, 9000 and 9800 commit to REU 340000–342FFF before guest cache or BIOS use. Separately, packaged A000–ADFF copies to host F000–FDFF, including its zero tail. FE00–FFFF vectors are excluded. These sources overlap 23 cache frames; no source survives as authority after startup. An initialized resident guard publishes A5 only after complete verified copying. Default HD-disabled startup still requires this code because text scrolling and clearing use it.

D64H is a 140-byte cold configuration with an explicit enable byte, import-floppy flag, geometry profile, read-only flag, boot drive, Ultimate target, cache slot count and NUL-terminated path. The 136 bytes after the magic are copied before cold code becomes bitmap RAM; they share a 138-byte resident block with phase/error bytes. Profiles are 2 MiB (128 cylinders, 2 heads, 16 sectors) and 20 MiB (640, 4, 16). A disabled configuration makes no HD open request. Enabled startup validates exact image length, opens asynchronously and warms the first 32 KiB before guest execution/timer delivery. Unknown firmware handles cannot be erased by local initialization; callers must establish exclusive known closure.

## Runtime sectors and failures

The backend caches 32 KiB extents in REU 200000–2FFFFF, up to 32 slots. Resident wrappers yield HD before acquiring FILE; nested ownership is forbidden. INT 13h retains normal mutable guest IVT/frame semantics. Pending file operations preserve the guest request and temporarily defer INTR; timer requests coalesce. Development snapshots refuse pending operations because UCI staging aliases their buffer.

Before a write, REU 350000–3501FF retains the exact authoritative sector. An accepted status alone cannot clear uncertainty: exact readback must also succeed. An uncertain write blocks remount and a new changed-buffer mutation. REU 352000–3521FF is the coherent guest handoff. Partial guest-copy failures preserve the committed prefix and terminal frame/context; a completed-sector count advances only for whole sectors. Known/unknown open and close failures retain their real authority state.

Before any physical HD recovery overwrites REU, collect failure RAM, these two authoritative ranges and the disposable remote image. The pre-run REU backup cannot preserve new uncertain writes. Mock readback/CLOSE/reopen evidence does not establish physical durability.

## Scrolling and identity

A coherent span helper in the copied window accelerates scrolling and clearing while preserving per-byte dirty/generation/epoch behavior, pin release and failure prefixes. Scalar fallback covers pin pressure, one-frame caches and generation overflow. Modeled 80-column scroll CPU clocks fall from 3,044,133 to 597,325; this is neither physical elapsed time nor an XT ratio.

Physical development runners require paired pinned package and memory reports for this layout. They freeze expected bytes from the original PRG A000–ADFF and compare all 3,584 captured bytes at F000–FDFF, including the 1,440-byte zero tail and A5 guard. Live A000 is guest cache and is never an expected-code source. No copied-code normalization is allowed. REST underlying RAM bytes at 0000/0001 do not prove live 6510 banking; physical identity records that limit separately from functional execution evidence.

## Verification and remaining gates

Actual linked Peddle tests cover overlay/shadow startup, cache/FILE leases, INT 13h, uncertainty, exact lengths, read-only behavior, cold-state poisoning and native DOS boots from both geometries. Long lanes consume explicit SHA-pinned fixture manifests:

```sh
make test-hd
../../zeropage-tooling/bin/zig build hd-cold -Dhd-small-manifest=/absolute/small/manifest.json -Dhd-large-manifest=/absolute/large/manifest.json --summary all
```

The genuine DOS fixture AUTOEXEC deliberately writes three redirected boot logs. The accepted small/large runs issue 21/22 guest sector writes; interactive VER/DIR add none. Independent complete-image inspection attributes each write to the exact guest source bytes and checks other logical file contents. A separate intentional write above 16 MiB tests close/reopen addressing on a disposable image.

Physical six-overlay startup, HD reads/writes/reopen, power-loss durability, IEC runtime integration, external display/input and near-XT performance remain separate gates. See current evidence (local development record, not distributed), memory ledger (local development record, not distributed) and [disk fixture tools](DISK_TOOLS.md).

2026-10-16: Logical512-byte sector writes use consecutive256-byte FILE transfers, independently loaded from retained350000 and350100; uncertainty clears only after all512 readback. Retry replays both halves for originalLBA. ROOT71972/729111 host/modelaccepted; physicalCdrive persistence remains pending. CompleteDOS/TPfixture uses20MiB because fullvendorpayload+allDOSarchives exceeds2MiB.
