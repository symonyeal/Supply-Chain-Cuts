# Every former cobalt or precursor cut survives with chemistry choice

The headline uses alpha = 25%, h = sigma = 0, a 24-month horizon and outages up to
12 months. Capacities stay at the reference 50/50 blend. The two approved aggregate
NCM-share ranges [0,1] and [0.25,0.75] give identical failure events (MODEL, restored
second-year argument). This is hypothetical recipe flexibility, not measured plant
switchability. No nickel-containing minimal cut existed at this reference headline.

Sources: `results/chemistry-896581f/cuts/liion_{free,bounded}_a0.25_h0_s0_L6.json`,
producer `d18c743`; both clean. Each row below restates one former minimal cut; zero
means no unmet cell demand, not merely a shortfall below the failure threshold.

| Former cut (country, product, months) | Shortfall, free choice | Shortfall, bounded choice | Still a cut? |
| --- | ---: | ---: | --- |
| AUS mine_co 3 + CAN mine_co 12 + COD mine_co 12 | 0% | 0% | no |
| AUS mine_co 3 + COD mine_co 12 + CUB mine_co 12 | 0% | 0% | no |
| AUS mine_co 3 + COD mine_co 12 + MDG mine_co 12 | 0% | 0% | no |
| AUS mine_co 3 + COD mine_co 12 + PHL mine_co 12 | 0% | 0% | no |
| AUS mine_co 6 + CAN mine_co 6 + COD mine_co 12 | 0% | 0% | no |
| AUS mine_co 6 + COD mine_co 12 + CUB mine_co 6 | 0% | 0% | no |
| AUS mine_co 6 + COD mine_co 12 + RUS mine_co 3 | 0% | 0% | no |
| AUS mine_co 12 + COD mine_co 12 | 0% | 0% | no |
| CAN mine_co 3 + COD mine_co 12 + CUB mine_co 12 | 0% | 0% | no |
| CAN mine_co 6 + COD mine_co 12 + MDG mine_co 12 | 0% | 0% | no |
| CAN mine_co 6 + COD mine_co 12 + PHL mine_co 12 | 0% | 0% | no |
| CAN mine_co 12 + COD mine_co 12 + CUB mine_co 3 | 0% | 0% | no |
| CAN mine_co 12 + COD mine_co 12 + MDG mine_co 3 | 0% | 0% | no |
| CAN mine_co 12 + COD mine_co 12 + PHL mine_co 3 | 0% | 0% | no |
| CAN mine_co 12 + COD mine_co 12 + RUS mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + CUB mine_co 3 + MDG mine_co 12 | 0% | 0% | no |
| COD mine_co 12 + CUB mine_co 3 + PHL mine_co 12 | 0% | 0% | no |
| COD mine_co 12 + CUB mine_co 12 + MDG mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + CUB mine_co 12 + PHL mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + CUB mine_co 12 + RUS mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + IDN mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + MDG mine_co 6 + PHL mine_co 12 | 0% | 0% | no |
| COD mine_co 12 + MDG mine_co 12 + PHL mine_co 6 | 0% | 0% | no |
| COD mine_co 12 + MDG mine_co 12 + RUS mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + PHL mine_co 12 + RUS mine_co 3 | 0% | 0% | no |
| COD mine_co 12 + RUS mine_co 6 | 0% | 0% | no |
| CHN pcam 6 + POL pcam 12 + USA pcam 12 | 0% | 0% | no |
| CHN pcam 12 | 0% | 0% | no |
| CHN refined_co 12 | 0% | 0% | no |
