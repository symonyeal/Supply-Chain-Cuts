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

## Units and blocks

Let R_f be the demand target of final f and R_p = sum_q a[p,q] R_q the annual requirement
of p. The LP measures each product in units of R_p, so capacities are u[v] = annual[v] /
(12 R[p]) and a'[p,q] = a[p,q] R[q]/R[p]. This diagonal rescaling is exact; every capacity
dual bound becomes M[p] = 1 on the Li-ion chain, and S[p] = 12 sum_v u[v] is the supply
ratio of layer p in years of requirement per year.

**Lemma A (blocks).** Let 1 <= e_1 < ... < e_K = T be months such that capacity, ramp and
demand are constant on each block (e_(i-1), e_i]. Then the LP over blocks, with rates per
month, objective sum_i l_i g_i and balance I_i = I_(i-1) + l_i (x_i - a y_i), has the
optimal value of the monthly LP. *Proof.* Summing a monthly solution over a block gives a
block solution with the same objective. Conversely, give every month of block i the block
rates: every capacity, shipment and demand row holds because its data are constant on the
block, and inventory interpolates linearly between the nonnegative block endpoints. Hence
both LPs have the same value. The block ends used are the disruption durations, the ramp
months 1..L when sigma > 0, and T; durations must be block ends. A capacity dual of block
i is bounded by l_i M[p], since one unit of rate lasts l_i months.

**Lemma B (capacity dominance).** Let v, w be nodes of the same layer with u[v] <= u[w]
and D[v] >= D[w]. Exchanging their durations does not decrease phi. *Proof.* Nodes of a
layer differ only in capacity, and their initial stocks h a u are proportional to it;
shipments are pooled by product. Nodes of one layer with one duration therefore aggregate
exactly: split any aggregated solution in proportion to capacity. After the exchange the
group with the longer outage gains capacity u[w] - u[v] and the shorter group loses it. A
unit in the shorter group has at least the capacity, in every month, of a unit in the
longer group, and the same stock. So every solution after the exchange can be reproduced
before it, and phi does not decrease. With Proposition 1 (lengthening an outage does not
decrease phi), a state is dominated by the state obtained by moving each outage to a
larger node of its layer and lengthening it.

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

## Enumeration by lattice search

`chokepoint/brute.py` gives two enumerators that call phi only. `enumerate_brute` visits
every state of support <= k (skipping supersets of found cuts, and supports whose top state
survives). `enumerate_lattice` fixes a pattern of layers with multiplicities, takes the
nodes of each layer in decreasing capacity, and completes a partial state by filling open
slots with maximal admissible (node, duration) pairs. By Lemma B and Proposition 1 every
state of the subtree lies below one of these completions; if all survive, the subtree is
pruned. A partial state that contains a found cut is skipped: no state below it is
minimal. After the singletons are known, a slot may not use a node at or above its
singleton duration, for the same reason. On random networks of four layers the two
enumerators return identical lists (`tests/test_cuts.py`). On the 108-node Li-ion network
(before the country-name fix of `97e5fe7`; 111 nodes after, with the same 37 cuts)
at alpha = 0.25, h = sigma = 0, k = 3, plain lattice search took 427 s and 107,416 LPs;
with the two minimality rules, 13.8 s and 3,714 LPs, with the same 37 cuts (2026-10-15).

## Annual probability

For country c set s[c] = rho min_(v in c) p[v]. A country shock has probability s[c];
otherwise node onsets are independent with q[v] = (p[v]-s[c])/(1-s[c]). Thus each onset
marginal is p[v]. A shock shares onset, not necessarily duration: durations are drawn
from their stated conditional distribution. Zero-duration suspended announcements do
not create losses. Node-year counts are deduplicated across measure types and products.

### Exact rate-fit definition for independent recomputation

For node v, let N_v count observed years and K_v count onset years. For each product,
fit a,b by maximizing sum_v [log B(K_v+a,N_v−K_v+b) − log B(a,b)] over exposed nodes.
Numerical fitting uses log a, log b in [−7,14], L-BFGS-B, initialized at (10m,10(1−m))
with m = (sum K+0.5)/(sum N+1). Set p_v = (K_v+a)/(N_v+a+b). A product with no exposed
nodes uses a,b fitted over all exposed nodes in the fitting roster. PV and joint use the
joint roster; PV then restricts the fitted marginals to its nodes. Li-ion uses its own
roster. After restriction, country shocks in each scenario use that sector's node set.

To fit rho, each country-year with at least two observed nodes contributes y = 1 if at
least two onsets were observed. Let J be its observed subset, s = rho min_v p_v over all
nodes of that country in the fitting roster, and q_v = (p_v−s)/(1−s). Its predicted
multi-onset probability is s + (1−s) P(sum_(v in J) Bernoulli(q_v) >= 2). Minimize the
binary log-loss over these country-years on [0,1]; bounded scalar minimization and both
endpoints are compared. Probabilities in this log-loss are clipped to [1e-12,1−1e-12].
This describes the existing numerical fit; it does not establish predictive validity.

Duration records are counted once when their onset falls in any surveyed mapped
country–product year, even if that node is below the capacity cutoff. Bin uncensored
days/30.44 upward to (3,6,12), capped at 12; a right-censored duration is used only if it
already exceeds six months. National acts count onsets only where coverage is observed.

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

### Lower bound plus residual (W1, 2026-10-16)

Let F be failure and C the event that a sampled state contains an enumerated cut for the
same model. Every cut fails, so C is contained in F. With exact L = P(C), define

    X = 1_F - 1_C = 1_(F minus C),  r = P(F minus C),
    P_hat = L + (1/n) sum_i X_i,    Z_i iid from the original scenario law.

Then E(P_hat) = L + r = P(F) and Var(P_hat) = r(1-r)/n. For m = sum_i X_i and
r_hat = m/n, the sample standard error is sqrt(r_hat(1-r_hat)/(n-1)). The estimate is
at least L without clipping. Its variance comes only from failures outside the cut union;
variance reduction relative to crude MC is measured, not a universal theorem.

Sample the same latent country shocks, independent node onsets and categorical durations
as in the scenario law. States containing a cut have X = 0 and need no LP. If enumeration
is complete through k, states of support <= k without a cut also have X = 0 (Proposition
3). Solve the remaining states with the same strict threshold and numerical epsilon as
the cut certificates. Incomplete enumerations may still supply L, but cannot justify
this second shortcut.

For a useful interval even when m = 0, invert the binomial tails (Clopper and Pearson
1934, SOURCES). At confidence 95%,

    r_lo = 0 if m = 0, else BetaQuantile(0.025; m, n-m+1),
    r_hi = 1 if m = n, else BetaQuantile(0.975; m+1, n-m).

Report [L+r_lo, min(1,L+r_hi)]. This intersection with the probability parameter space
retains coverage. Zero observed residuals imply a zero sample standard error but a
positive upper interval width, not a proof that P(F) = L. The interval covers sampling
uncertainty conditional on fixed rates, durations and capacities; it does not cover data
or scenario uncertainty. The legacy IS and crude MC results remain comparisons.

## Export severity (W2, approved 2026-10-16)

The dated policy-severity design specifies sampling and identification. For event e,
normalize export quantities by each exporter's t0−1 volume. At relative year j, let
d[e,j] be the treated exporter's change from −1 minus the mean control change. Equal
event weights estimate beta[m,j] by the mean d[e,j] over events of type m. This equals
the stacked exporter-within-event and year-within-event fixed-effects regression when
each event gives half its weight to the treated exporter and half to its controls,
divided equally among controls. The panel is balanced over relative years −2,−1,0,+1;
−1 is omitted. This weighting specifies the approved design's equal event weights.

In a country bootstrap, the same country multiplicity is used for its treated events
and every appearance as a control. Reweight the controls within each event, then the
events by their treated-country multiplicities. Report valid bootstrap draws; a draw
with no treated events or no controls supplies no coefficient for that group.

Partial disruption replaces the capacity factor by 1 − f[v] 1{t <= D[v]}, with f in [0,1].
The capacity-conversion scenario assigns f_m = clip(−beta[m,+1],0,1), with full loss for
unidentified types. Product-specific measure mixtures and their pooled fallbacks are
empirical scenario marks, independent of legal duration. Paired states use identical
onsets, durations and measure marks for full loss, central f and both interval endpoints.
Since capacity under partial loss is at least capacity under full loss, its feasible set
contains the full-loss feasible set and its shortfall cannot exceed the latter.

Estimate each failure probability by its observed fraction, with a binomial interval.
The paired reduction indicator is 1{full failure, partial survival}, also Bernoulli;
its interval tests S3 directly. These trade responses and their conversion to capacity
remain conditional scenarios, not measured production losses.

## Alternative recipes and chemistry choice (W3)

The approved dated design fixes physical capacities at the reference 50% NCM mix.
Recipe r at capacity node v has rate y[v,r,t], output p(r), and inputs a[q,r]. One
capacity row sums all its recipe rates. Commodity supply sums all recipes producing
that commodity; recipient inventory subtracts the sum of its recipes' consumption.
Both CAM commodities use the original aggregate CAM requirement as their unit scale.
All other scales remain fixed. Initial stock is h u[v] times the reference blended
input coefficient, once per node/input. These are flexibility and stock assumptions.

Cell-share constraints sum block-weighted delivered output over the whole horizon.
Each period's cell production is capped by its demand, preventing unwanted output
from satisfying a share quota. One-recipe calls without share constraints retain the
legacy LP. Blocks remain exact because the added share rows are linear in block totals.
Lemma B still holds: all nodes of a capacity layer have identical recipes and reference
stock coefficients, and proportional splitting preserves global shares.

For the capacity dual bound, first ignore share constraints. Removing delta units of
one input's availability can be accommodated by withdrawing its downstream flow in the
acyclic recipe graph. Each unit is allocated once among recipients; every downstream
path yields at most the reciprocal product of its input coefficients. Multiple required
inputs cannot amplify this output. Unused shipments can remain as stock or be withdrawn;
inventory moves material through time without multiplying it. Thus the maximum lost
final output is bounded by the largest path yield times delta.

Now impose NCM share [s_lo,s_hi] on total delivered cell output. If withdrawing x NCM
units violates the lower share, also withdraw enough LFP to restore it: the total
withdrawal is at most x/s_lo. If withdrawing x LFP violates the upper share, total
withdrawal is at most x/(1−s_hi). Withdrawals consume fewer upstream inputs and preserve
all capacity constraints. Therefore multiplying every path bound by

    Gamma = max(1, 1/s_lo when 0<s_lo<1, 1/(1−s_hi) when 0<s_hi<1)

is conservative. At pure endpoints, remove the excluded final recipe first and use
Gamma = 1. Each capacity layer takes the maximum value of its available recipe outputs.
An extra unit of block rate lasts ell[t] months, giving Mcap[t,v] = ell[t] M[v].

This withdrawal argument gives a coordinatewise Lipschitz bound on the optimal shortfall
as capacities change, with initial stocks fixed. At positive capacities the capacity
components of an optimal dual can be chosen within these bounds; taking a limit from
positive capacities preserves such a bounded optimum at zero capacities. The dual
feasible polyhedron projected onto its bounded capacity multipliers and objective is
closed, so an optimal multiplier vector exists there. The MILP linearizes against these
bounds using the same primal matrices. Tests compare this bounded dual with the primal,
including binding quotas, zero capacities, pure endpoints and stocked block LPs.

The lattice enumerator also checks phi(0) first: if the undisrupted instance already
fails, its sole minimal cut is the empty state, including when k = 0. This case was
exposed by recipe-network tests; it does not alter the legacy instances with phi(0)=0.

**Nonbinding share sensitivity on this horizon.** In the reference physical network a
50/50 monthly output mix is feasible without stocks; this follows by splitting the
legacy blended CAM flow in proportion to its LFP/NCM masses. All modeled outages end
by month 12, demand is flat over 24 months, and restored capacity is at least nominal.
Thus any unrestricted optimum can deliver the full second year's demand at the
reference 50/50 mix. Let first-year output be a in [0,1] and its NCM output b in [0,a],
in annual demand units. The resulting horizon NCM share is

    (b + 1/2)/(a + 1), which lies in [1/4, 3/4].

This replacement preserves first-year feasibility and second-year demand satisfaction;
leftover input stocks can be carried unused. Hence the approved [0.25,0.75] bounds
cannot worsen optimal shortfall relative to [0,1] under these horizon assumptions.
Identical cut lists across the 94 runs are a check of this implication, not evidence
that arbitrary chemistry quotas do not matter. Tighter bounds, monthly bounds or
outages beyond half the horizon would require a different sensitivity. The probability
law of failure is identical here, so its estimator may be reused with that fact labelled.
