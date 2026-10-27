"""Exact host identity for the editor's fixed six-array catalog.

A published ID makes its corresponding slot byte authoritative. Managed code
may change only that published byte's verification bit7 without changing image
identity. Unpublished bytes are retained verbatim, including their slot bytes.
This is not a generic catalog decoder, RAM repair, or runtime trust decision.
"""
from dataclasses import dataclass
from typing import Mapping, Tuple, Optional

MAX_CAPACITY = 64
MAX_CATALOG_BYTES = 384
POLICY_SYMBOL = 'se_overlay_managed_verification'


class CatalogPolicyError(ValueError):
    """The input cannot be interpreted under the declared editor policy."""


@dataclass(frozen=True)
class CatalogState:
    managed_verification: bool
    published: Tuple[bool, ...]
    verified: Tuple[Optional[bool], ...]


def _raw_catalog(raw, symbols):
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        raise CatalogPolicyError('catalog must be a byte buffer')
    frozen = bytes(raw)
    capacity = symbols.get('se_overlay_capacity', MAX_CAPACITY)
    fixed = symbols.get('se_overlay_fixed_entry', 1)
    if type(capacity) is not int or not 0 < capacity <= MAX_CAPACITY or fixed != 1:
        raise CatalogPolicyError('unsupported editor catalog layout')
    exact = 6 * capacity
    if len(frozen) not in (exact, MAX_CATALOG_BYTES):
        raise CatalogPolicyError('editor catalog must contain its exact arrays or legacy full extent')
    return frozen, capacity


def catalog_state(raw: bytes, symbols: Mapping[str, int]) -> CatalogState:
    """Validate the layout and every published slot before normalization.

    No metadata for ID0 is inferred to be initialized or trustworthy. Its
    verification state is None and every raw byte remains part of identity.
    Published slot low7 bits must be exactly0 or1. Bit7 is legal only when
    the explicit reported policy constant equals1; missing/zero is strict.
    """
    raw, capacity = _raw_catalog(raw, symbols)
    flag = symbols.get(POLICY_SYMBOL, 0)
    if type(flag) is not int or flag not in (0, 1):
        raise CatalogPolicyError('unsupported managed-verification policy')
    published = tuple(bool(raw[i]) for i in range(capacity))
    verified = []
    for i, live in enumerate(published):
        if not live:
            verified.append(None)
            continue
        slot = raw[capacity + i]
        if slot & 0x7f not in (0, 1):
            raise CatalogPolicyError('invalid published slot bits at index%d' % i)
        if slot & 0x80 and not flag:
            raise CatalogPolicyError('verification bit without managed policy at index%d' % i)
        verified.append(bool(slot & 0x80))
    return CatalogState(bool(flag), published, tuple(verified))


def catalog_identity(raw: bytes, symbols: Mapping[str, int]) -> bytes:
    """Return immutable identity, masking only declared published slot bit7.

    IDs, low slot bits, lengths, CRCs and all unpublished metadata stay exact.
    Never use this identity result to assert that a live verified bit is set or
    invalidated: inspect catalog_state(raw, symbols) in the separate bit-state
    tests. Inputs are never modified and no RAM/REU data is written.
    """
    raw, capacity = _raw_catalog(raw, symbols)
    state = catalog_state(raw, symbols)
    identity = bytearray(raw)
    if state.managed_verification:
        for i, live in enumerate(state.published):
            if live:
                identity[capacity + i] &= 0x7f
    return bytes(identity)
