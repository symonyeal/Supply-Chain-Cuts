//! Admission for the closed analytical scenario supplied at the CLI boundary.
use serde_json::Value;

pub fn validate(c: &Value) -> Result<(), String> {
    let c = c.as_object().ok_or("Config must be an object")?;
    for (key, value) in c {
        let valid = match key.as_str() {
            "sector" => value
                .as_str()
                .is_some_and(|x| ["liion", "pv", "joint"].contains(&x)),
            "basis" => value
                .as_str()
                .is_some_and(|x| ["production", "trade"].contains(&x)),
            "choice" | "aggregate" | "dual" | "eu_sold" => value.is_boolean(),
            "k" | "seed" => value.as_u64().is_some(),
            "n" => value.as_u64().is_some_and(|n| n >= 2),
            "T" => value.as_u64().is_some_and(|n| n > 0),
            "h" | "sigma" => value.as_f64().is_some_and(|x| x.is_finite() && x >= 0.0),
            "L" | "time_limit" | "japan_voltage" => {
                value.as_f64().is_some_and(|x| x.is_finite() && x > 0.0)
            }
            "alpha" | "ncm" => value.as_f64().is_some_and(|x| (0.0..=1.0).contains(&x)),
            "cutoff" => value.as_f64().is_some_and(|x| (0.0..1.0).contains(&x)),
            "durations" => value.as_array().is_some_and(|a| {
                !a.is_empty()
                    && a.iter().all(|x| x.as_u64().is_some_and(|x| x > 0))
                    && a.windows(2).all(|w| w[0].as_u64() < w[1].as_u64())
            }),
            "shares" | "f" => value.as_array().is_some_and(|a| {
                !a.is_empty()
                    && a.iter()
                        .all(|x| x.as_f64().is_some_and(|x| (0.0..=1.0).contains(&x)))
            }),
            "exclude" => value.as_array().is_some_and(|a| {
                a.iter().all(|p| {
                    p.as_array().is_some_and(|p| {
                        p.len() == 2 && p.iter().all(|x| x.as_str().is_some_and(|x| !x.is_empty()))
                    })
                })
            }),
            _ => return Err(format!("Unknown scenario field: {key}")),
        };
        if !valid {
            return Err(format!("Invalid scenario field: {key}"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn absent_defaults_differ_from_invalid_present_values() {
        assert!(validate(&json!({})).is_ok());
        for c in [
            json!({"choice":"true"}),
            json!({"aggregate":null}),
            json!({"k":1.5}),
            json!({"seed":-1}),
            json!({"unknown":true}),
            json!({"durations":[3,"6"]}),
            json!({"durations":[6,3]}),
            json!({"exclude":[["A"]]}),
        ] {
            assert!(validate(&c).is_err(), "{c}");
        }
    }
}
