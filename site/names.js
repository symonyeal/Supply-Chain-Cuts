/* Plain display names shared by the overview and the explorer.
   Source names (BACI, USGS) stay unchanged in the data; these change only what readers see.
   BACI's CIV row is double-encoded UTF-8 in the frozen source file. */
"use strict";
window.LABELS = (() => {
  const products = {aam:"Anode material",cam:"Cathode material",pcam:"Cathode precursor",cell:"Battery cells",graphite:"Graphite",
    mine_li:"Lithium ore",mine_co:"Cobalt ore",mine_ni:"Nickel ore",mine_mn:"Manganese ore",li_carbonate:"Lithium carbonate",
    refined_co:"Refined cobalt",refined_ni:"Refined nickel",refined_cu:"Refined copper",aluminium:"Aluminium",
    polysilicon:"Polysilicon",wafer:"Solar wafers",pv_cell:"Solar cells",module:"Solar panels"};
  const places = {CIV:"Côte d'Ivoire",COD:"DR Congo",DEU:"Germany",KOR:"South Korea",RUS:"Russia",TZA:"Tanzania",
    USA:"United States",VNM:"Vietnam","Congo (Kinshasa)":"DR Congo","Korea, Republic of":"South Korea","Korea, North":"North Korea"};
  const capacityCase = (scenario, japan = "Japan at assumed") => {
    const name = scenario.replace(/_(choice|fixed)$/, "");
    return name.startsWith("japan") ? `${japan} ${name.slice(5)} V` :
      name === "eu_sold" ? "German sold carbonate" : name === "supplement" ? "Japan 3.7 V + German carbonate" :
        `Co/Ni reservation; Cu/Al/Mn ${(100 * +name.slice(7)).toFixed(0)}% available`;
  };
  return {product: p => products[p] || p.replaceAll("_"," "), place: (code, name) => places[code] || name || code, capacityCase};
})();
