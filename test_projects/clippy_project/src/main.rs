#![warn(clippy::all)]

use std::collections::HashMap;

fn main() {
    // Clippy warning: redundant clone
    let s = String::from("hello");
    let _s2 = s.clone().clone();
    
    // Clippy warning: unnecessary vec! macro
    let _v = vec![1, 2, 3];
    
    // Clippy warning: comparison to NaN
    let x = 0.0 / 0.0;
    if x == f64::NAN {
        println!("This won't work");
    }
    
    // Clippy warning: inefficient string comparison
    let name = String::from("Alice");
    if name == "Alice".to_string() {
        println!("Hi Alice");
    }
    
    // Clippy warning: unnecessary match
    let opt = Some(5);
    let _val = match opt {
        Some(x) => x,
        None => 0,
    };
    
    // Clippy warning: HashMap could use entry API
    let mut map = HashMap::new();
    if !map.contains_key(&"key") {
        map.insert("key", "value");
    }
    
    // Clippy warning: needless return
    let result = calculate(5);
    println!("Result: {}", result);
}

fn calculate(x: i32) -> i32 {
    // Clippy warning: needless return
    return x * 2;
}

// Clippy warning: function could be const
fn get_constant() -> i32 {
    42
}