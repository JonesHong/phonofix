"""Tier 2: mutation set pre-compute — recall gate for Tier 1 hash equality.

Codex finding (B-P0-2): ja Tier 1 hash equality has recall gap (2,250 → 500 hits);
mutation set restores recall by precomputing neighbor mutations per alias at dict build.

Algorithm:
  for each alias:
    precompute "韻母 group 鄰居" mutations (single phoneme swap from confusion rules)
    register each mutation as additional hash key → original alias

Query path:
  hash lookup query_normalized in mutation_index
  if hit → return original alias (Tier 2 recall recovered)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class MutationEntry:
    mutation_key: str  # phoneme tuple normalized form, used as hash key
    canonical_alias: str  # original alias (pre-mutation)
    distance: int  # 1 = single phoneme swap; reserved for future k>1


def _phonemes_to_key(phonemes: tuple[str, ...]) -> str:
    """Convert phoneme tuple to hash-key string."""
    return "|".join(phonemes)


def _generate_single_swap_mutations(
    phonemes: tuple[str, ...],
    confusion: Callable[[tuple[str, ...]], set[tuple[str, ...]]],
) -> set[tuple[str, ...]]:
    """
    Generate all single-phoneme-swap mutations for a phoneme sequence.

    For each position i in phonemes, call confusion(phonemes[i]) to get
    confusable alternatives, then yield variants with that position swapped.

    Returns a set of mutated phoneme tuples (excludes the original).
    """
    mutations: set[tuple[str, ...]] = set()
    for i, phoneme in enumerate(phonemes):
        confusables = confusion((phoneme,))
        for alt in confusables:
            if alt == (phoneme,):
                continue
            mutated = phonemes[:i] + alt + phonemes[i + 1 :]
            if mutated != phonemes:
                mutations.add(mutated)
    return mutations


def build_mutation_index(
    aliases: Iterable[str],
    phonemize: Callable[[str], list[tuple[str, ...]]],
    confusion: Callable[[tuple[str, ...]], set[tuple[str, ...]]],
    max_distance: int = 1,
) -> dict[str, list[MutationEntry]]:
    """
    Build-time: for each alias, generate single-phoneme-swap mutations
    using language-specific confusion rules.

    phonemize: text → phoneme sequence (from Phonemizer Protocol)
    confusion: phoneme → confusable phoneme set (from Phonemizer Protocol)
    max_distance: currently only 1 supported (single swap)

    Returns: {mutation_hash_key: [MutationEntry(orig alias, dist)]}
    """
    if max_distance != 1:
        raise NotImplementedError("max_distance > 1 is reserved for future use")

    index: dict[str, list[MutationEntry]] = defaultdict(list)

    for alias in aliases:
        phoneme_sequences = phonemize(alias)
        for phonemes in phoneme_sequences:
            if not phonemes:
                continue
            mutations = _generate_single_swap_mutations(phonemes, confusion)
            for mut_phonemes in mutations:
                key = _phonemes_to_key(mut_phonemes)
                entry = MutationEntry(
                    mutation_key=key,
                    canonical_alias=alias,
                    distance=1,
                )
                index[key].append(entry)

    return dict(index)


def lookup_mutation(
    index: dict[str, list[MutationEntry]],
    query_phonemes: tuple[str, ...],
) -> list[MutationEntry]:
    """
    Query-time O(1) hash lookup.
    Returns list of MutationEntry that match (typically 0 or 1 entry).
    """
    key = "|".join(query_phonemes)
    return index.get(key, [])
