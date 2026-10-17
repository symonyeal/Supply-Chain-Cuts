# Chemistry choice: proposed model extension

Status: approved by the user, 2026-10-16, with 24-month share bounds; implemented and
certified in the W3 bundles (FINDINGS, CHEMISTRY). Implements NEXT W3.
The intended question is whether precursor, cobalt and nickel cuts survive when cells
may choose LFP or NCM622 while physical plant capacities remain fixed.

## Interpretation and alternatives

The existing fixed-mix sweep changes a coefficient before solving. Its aggregate CAM
recipe consumes precursor even when the surviving output could have been LFP. Giving
the optimizer separate CAM products and cell recipes removes that imposed dependence.

One alternative is to choose a global mix before each disruption and rerun the old LP;
it still binds both chemistries to the aggregate cathode recipe. Another is to split
each observed CAM capacity into separate, dedicated plants; their shares are unobserved.
The proposed shared-capacity process model expresses recipe choice without inventing
additional capacity. It represents hypothetical plant flexibility, not measured
switchability of actual manufacturing lines.

## Capacities and units

Keep the 2024 physical node capacities and their basis labels from the reference NCM
share 0.5. In particular, do not recalculate trade-to-GWh conversions, imputed pCAM or
non-China CAM capacity when the optimizer changes chemistry. Report that dependence
on the original reference mix. Disruption nodes retain their country and capacity-layer
names, including `cam`: an outage of a CAM node removes its shared capacity for both
chemistries. There is no duplication of its tonnes or its outage probability.

Use the Xu et al. pure-LFP and pure-NCM622 bills of materials. The two output commodities
are `cam_lfp` and `cam_ncm`; only NCM CAM consumes pCAM. Both cell recipes consume their
own CAM and the same anode, aluminium and copper inputs in chemistry-specific amounts.
Capacity units remain tonnes for cathode processes and GWh for cell processes.

Normalize both CAM commodities by the same reference total CAM requirement; the sum of
their rates then uses the original CAM capacity. Other product scales retain their
reference values. This scaling need not give capacity dual bounds equal to one.

## One process model, one matrix construction

Let R(v) be the recipes available at capacity node v. Recipe r outputs one unit of
commodity p(r), consumes a[q,r] of each input q, and has rate y[v,r,t] >= 0. Replace the
single-output capacity row by

    sum_(r in R(v)) y[v,r,t] <= U[v,t].

For commodity q, total shipments cannot exceed the sum of all rates producing q.
Input stock at recipient v obeys

    I[q,v,t] = I[q,v,t-1] + x[q,v,t] - sum_r a[q,r] y[v,r,t].

Final demand sums both cell recipes. Every legacy node has one recipe, so the old
matrices and optima must be reproduced as a special case. The interdiction MILP uses
the dual of these matrices; it receives no separate recipe transcription.

Stocks are h times the reference blended input requirement of each node. Cell blend
weights are 0.5 in GWh; CAM weights are the corresponding reference mass proportions.
Stocks are assigned once per input and node, not separately in full to each recipe.
An absent supplier still has a balance row.

## Bounded chemistry shares

Main scenario: NCM share in [0,1]. Sensitivity: [0.25,0.75]. These are assumptions,
not observed 2024 chemistry shares. Bounds apply to aggregate delivered cell output
over the 24-month horizon:

    s_lo sum_(v,r,t) l[t] y[v,r,t]
        <= sum_(v,r=NCM,t) l[t] y[v,r,t]
        <= s_hi sum_(v,r,t) l[t] y[v,r,t].

The sums include cell recipes only. Cap total cell output in each period at that
period's demand, so surplus production cannot satisfy a chemistry quota without serving
demand. Inventory may move cathode inputs across time; a terminal mix requirement may
be met at different shares in different months. This is deliberate; monthly share
bounds would be a distinct, more restrictive scenario.

## Certificates and dual bounds

Exact blocks remain valid: all added constraints are linear in block totals. Lemma B
still holds within each capacity layer because nodes have identical available recipes
and proportional reference stocks, differing only in capacity. Splitting an aggregate
solution proportionally preserves recipe shares, stocks and global mix constraints.

For unrestricted shares, recursively bound marginal value by the largest reciprocal
input coefficient over every downstream recipe path. With an interior lower NCM quota,
losing delta NCM output can force total output down by at most delta/s_lo; with an
interior upper quota, losing delta LFP output can force total output down by at most
delta/(1-s_hi). A conservative multiplier on the path bound is therefore

    Gamma = max(1, 1/s_lo if s_lo>0, 1/(1-s_hi) if s_hi<1).

Pure endpoints disable the excluded chemistry and use Gamma = 1. The implementation
must supply the complete withdrawal argument and test bounded duals against unbounded
duals, including zero capacities and binding share limits, before treating the bound
as a certificate. If that argument fails, report a model-design obstruction rather
than silently increasing M until a solver accepts it.

## Registered claim and acceptance

Before running probabilities, register C2: allowing [0,1] chemistry removes the Chinese
pCAM and refined-Co headline singletons. Kill the claim separately for either singleton
if its 12-month loss still exceeds alpha = 25%. Report all changed Co/Ni/pCAM cut sets,
including contrary outcomes. Cuts containing other independently failing nodes must be
distinguished from a Co/Ni dependence.

Required checks: a hand-derived LFP route survives total precursor loss; legacy
one-recipe optima agree; monthly and block LPs agree; primal and bounded dual agree;
capacity dominance holds; lattice equals exhaustive search on random networks with
alternative recipes and share bounds; MILP equals that list on those toys. Rerun the
headline Li-ion cut sweep with primal/dual and immediate-duration witnesses. Restate
every Co/Ni/pCAM result in FINDINGS under each share bound. Preserve legacy bundles.
