# Formal model synopsis

Let `Prog` be a set of programs. Contextual equivalence `≈B` is the behavior
contract. Detector indistinguishability `≈D` and required attack edges `→A`
generate the operational equivalence `≈J = EqCl(≈D ∪ →A)`. Every admissible
decoder is constant on `≈J` classes. Source-dependent access records which
behavior-preserving outputs a declared mechanism can reach from each source.

With class-complete access and `≈J` refining `≈B`, exact universal capacity is
the minimum number of operational cells in a behavior class. Without refinement,
operational cells are vertices and behavior classes induce hyperedges; exact
feasibility is polychromatic coloring. Refinement is not a general necessity: a
crossing four-cycle can carry a bit when one global coloring covers both behavior
edges. With source-dependent access, each source induces the hyperedge of
reachable behavior-preserving operational cells, and the same global coloring
condition is exact. A required source row must be present in the finite input;
an explicitly empty row is a valid empty constraint and makes every nonempty
alphabet infeasible. Both finite incidence forms realize arbitrary nonempty-edge
hypergraphs inside one fixed deterministic terminating tagged host language.
Binary feasibility is NP-complete at three cells per constraint and is graph
bipartiteness at two.

For partial recovery, each operational cell may output a bounded list. Under an
arbitrary correlated source-message law, heterogeneous list budgets, randomized
encoders and detectors, and shared coins independent of the sampled pair, the
optimal average containment probability is attained by a deterministic global
list assignment. For a fixed message prior and a worst-source objective,
deterministic, private-detector, and shared-coloring randomness can differ: the
binary triangle has values `1/2`, `3/4`, and `5/6`. Under full support, value one
is still equivalent to covering every access edge with every message; unit lists
therefore recover the exact polychromatic boundary.

Coordinatewise composition of semantic contracts induces the direct product of
the quotient or access hypergraphs. Capacity is supermultiplicative and exactly
multiplicative in the refinement case. The triangle has one-shot capacity one,
while its square has capacity three. For every finite nonempty-edge hypergraph,
the regularized coordinate-product rate exists and equals the base-two logarithm
of the minimum edge size. This is a joint-contract existence theorem, not a
post-hoc composition algorithm or a cryptographic security claim.

For a context-profile map from programs to observations indexed by contexts,
semantic predicates factor through behavioral equivalence. The product topology
classifies finite positive evidence by open sets and two-sided finite evidence by
clopen sets; compactness yields a single uniform finite context set.

## Contract order laws

For fixed behavior, coarsening operational equivalence can only remove feasible
schemes. For fixed operational equivalence, refining behavior can only remove
feasible schemes. For fixed behavior and operational equivalence, expanding
access can only add feasible schemes. These laws also hold when behavior and
operational equivalence cross.

## Reachability and a prescribed sampling law

The access relation describes owner-selectable outputs, not merely a set of possible sampler outputs. Two strictly positive distributions on the same finite support induce the same selectable exact capacity but may have different actual recovery probabilities. The paper now gives a 99%/1% two-output example and separates fixed sampling from rejection-based selection and its cost.

The concrete witness validator checks all program-level obligations after output selection. It cannot establish that the input partitions or reachability relation correctly model a real compiler.
