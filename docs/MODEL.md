# Model and certificates

Let V consist of country–product nodes with monthly capacities u. Products form a DAG.
An edge p -> q consumes a[p,q] > 0 units of p per unit of q; competing recipients share
the same upstream output. A node with an absent required supplier still has an input
balance. Removing that balance would create material from nothing.

For each month t = 1,...,T, let y be output, x shipments, I nonnegative input inventory,
and g unmet final demand. The LP is

    phi(D) = min c'x
             A x <= b(D), E x = f, x >= 0.

Here x denotes the complete variable vector, rather than shipments alone. The rows of A
are capacity, total shipments <= output, and final output + shortfall >= demand. The
rows of E are the input inventory balances in design §4. Initial stock at recipient w
is h a[p,q(w)] u[w]. This is cover of nominal recipient capacity, an explicit scenario
assumption; it is not a measured inventory. Capacity in month t is

    U[v,t] = u[v] (1 + sigma min(1,t/L)) [t > D[v]].

Every final product has a separate demand row. A joint Li-ion/PV instance measures each
sector's output in its own baseline annual output units, so adding shortfalls gives
equal sector weights. It does not add battery kWh to PV kW. Failure means phi > alpha
times total demand. Numerical certificates use a stated absolute epsilon around that
boundary; unresolved boundary cases stop enumeration rather than being called complete.

## Dual and interdiction

The dual is max -b(D)'r + f'lambda, subject to

    -A'r + E'lambda <= c, r >= 0, lambda free.

Let M[p] be the largest final-shortfall reduction per unit of p. Set M[final] to its
objective weight, and recursively set M[p] = max_q M[q]/a[p,q], or zero if p reaches no
final. This is a valid upper bound on a capacity shadow price: an extra unit can be
allocated once among recipients; every path converts at most its reciprocal coefficient
product. Storage moves that unit through time without multiplying it. Converging paths
can reduce this value, but cannot increase it. There exists an optimal dual with each
capacity multiplier in [0,M[p]], including at degenerate zero capacities.

For binary exact-duration states z[v,j], sum_j z[v,j] <= 1. For each affected capacity
row introduce w = z r with 0 <= w <= M z, w <= r, w >= r - M(1-z). Then

    -b(0)'r + f'lambda + sum_(v,j,t<=D[j]) U0[v,t] w[v,j,t] >= theta

is a single-level interdiction MILP. Minimise sum z, with sum z <= k. All LP matrices
come from the recourse module. The independent brute enumerator imports only recourse.

## Monotonicity and duration minimality

If D <= D', the feasible set for D' is contained in the feasible set for D; hence
phi(D) <= phi(D'). Failures form an up-set. A minimal state fails, but lowering any one
positive coordinate to the immediately preceding duration does not fail. Node deletion
alone does not establish minimality when there are several duration levels.

After an optimal MILP support is found, lower each coordinate while failure persists.
Monotonicity makes one coordinate pass sufficient. Store the primal value, separately
solved dual value and every immediate predecessor. Exclude the entire upper orthant:

    sum_(v in support(S)) sum_(j: D[j]>=S[v]) z[v,j] <= |support(S)| - 1.

Every returned state is minimal: support optimality rules out deletion, and predecessor
checks rule out shorter duration. Every excluded state contains an already returned cut.
When the residual MILP is infeasible, every failing state with support <= k contains a
reported cut. Time limits and numerical failures are incomplete results, not proofs.

## Annual probability

For country c set s[c] = rho min_(v in c) p[v]. A country shock has probability s[c];
otherwise node onsets are independent with q[v] = (p[v]-s[c])/(1-s[c]). Thus each onset
marginal is p[v]. A shock shares onset, not necessarily duration: durations are drawn
from their stated conditional distribution. Zero-duration suspended announcements do
not create losses. Node-year counts are deduplicated across measure types and products.

The exact lower bound L is the probability of containing at least one enumerated minimal
duration state. A decision recursion conditions on each country's shock; remaining node
states are independent. The count tail is a convolution of country support distributions.
For a complete enumeration through k,

    L <= P(failure) <= min(1, L + P(number of disrupted nodes > k)) = U.

Proof: every failure contains a minimal state. A failure not covered by the enumerated
cuts must have support greater than k. This claim requires the completeness flag and
the same durations, rates and failure threshold in both computations.

Importance sampling tilts country-shock and independent-node probabilities, preserving
all support. Its likelihood ratio includes the latent shock indicators and categorical
durations. Proposal adaptation uses a separate pilot, and inference uses fresh samples.
The reported interval is a normal Monte Carlo interval, not a rigorous probability bound.
An estimate can lie outside [L,U] through sampling error: report that check and the
interval, never clip the estimate. The bracket itself is exact conditional on the model.
