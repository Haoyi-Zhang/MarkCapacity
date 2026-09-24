"""Finite constructive witnesses, checked without quotient reconstruction."""
from itertools import product
import random
from woc import (set_partitions, normalize_partition,
                 general_exact_feasible, direct_general_exact_feasible,
                 access_exact_feasible, direct_access_exact_feasible,
                 construct_access_scheme, validate_access_scheme)


def run_witness_checks():
    counts = {'exhaustive_instances': 0, 'generated_instances': 0,
              'positive_instances': 0, 'negative_instances': 0,
              'valid_constructed_witnesses': 0, 'oracle_agreements': 0}

    def check(behavior, operational, access, messages, category):
        feasible = direct_access_exact_feasible(behavior, operational, access, messages)
        counts[category] += 1
        if feasible:
            decoder, embedder = construct_access_scheme(behavior, operational, access, messages)
            ok, failures = validate_access_scheme(behavior, operational, access, messages, decoder, embedder)
            if not ok:
                raise AssertionError(f'constructed program witness fails: {failures}')
            counts['positive_instances'] += 1
            counts['valid_constructed_witnesses'] += 1
        else:
            try:
                construct_access_scheme(behavior, operational, access, messages)
            except ValueError:
                counts['negative_instances'] += 1
            else:
                raise AssertionError('constructor accepted a direct-oracle obstruction')
        counts['oracle_agreements'] += 1

    items = (None, 'x')
    partitions = list(set_partitions(items))
    for behavior, operational, mask, messages in product(partitions, partitions, range(16), (1, 2)):
        access = {p: {q for j, q in enumerate(items) if mask & (1 << (i * 2 + j))}
                  for i, p in enumerate(items)}
        check(behavior, operational, access, messages, 'exhaustive_instances')
    rng = random.Random(0x5749544E)
    items = (None, 'x', ('tag', 2))
    partitions = list(set_partitions(items))
    for _ in range(192):
        behavior, operational = rng.choice(partitions), rng.choice(partitions)
        access = {p: {q for q in items if rng.getrandbits(1)} for p in items}
        messages = rng.choice((1, 2, 3))
        check(behavior, operational, access, messages, 'generated_instances')
    assert counts['exhaustive_instances'] == 128
    assert counts['generated_instances'] == 192
    assert counts['oracle_agreements'] == 320
    return counts

def run_larger_stress_checks():
    """Deterministic unfiltered stress sample beyond the exhaustive two-item witness grid."""
    rng = random.Random(0x46494E414C)
    counts = {
        'instances': 0,
        'general_oracle_agreements': 0,
        'access_oracle_agreements': 0,
        'positive_access_instances': 0,
        'negative_access_instances': 0,
        'validated_positive_witnesses': 0,
    }
    for _ in range(240):
        n = rng.choice((3, 4, 5))
        items = tuple(range(n))

        def random_partition():
            labels = [rng.randrange(1, n + 1) for _ in items]
            return normalize_partition(
                {item for item, label in zip(items, labels, strict=True) if label == value}
                for value in sorted(set(labels))
            )

        behavior = random_partition()
        operational = random_partition()
        messages = rng.randint(1, min(3, len(operational) + 1))
        optimized_general = general_exact_feasible(behavior, operational, messages)
        direct_general = direct_general_exact_feasible(behavior, operational, messages)
        if optimized_general != direct_general:
            raise AssertionError('larger general oracle disagreement')
        counts['general_oracle_agreements'] += 1

        access = {
            source: {target for target in items if rng.random() < 0.55}
            for source in items
        }
        optimized_access = access_exact_feasible(behavior, operational, access, messages)
        direct_access = direct_access_exact_feasible(behavior, operational, access, messages)
        if optimized_access != direct_access:
            raise AssertionError('larger access oracle disagreement')
        counts['access_oracle_agreements'] += 1
        if optimized_access:
            decoder, embedder = construct_access_scheme(
                behavior, operational, access, messages
            )
            ok, failures = validate_access_scheme(
                behavior, operational, access, messages, decoder, embedder
            )
            if not ok:
                raise AssertionError(f'larger positive witness failed: {failures}')
            counts['positive_access_instances'] += 1
            counts['validated_positive_witnesses'] += 1
        else:
            counts['negative_access_instances'] += 1
        counts['instances'] += 1

    assert counts == {
        'instances': 240,
        'general_oracle_agreements': 240,
        'access_oracle_agreements': 240,
        'positive_access_instances': 13,
        'negative_access_instances': 227,
        'validated_positive_witnesses': 13,
    }
    return counts

