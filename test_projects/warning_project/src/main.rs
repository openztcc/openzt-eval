#![warn(unused_variables)]
#![warn(dead_code)]

fn main() {
    // Unused variable
    let unused_var = 42;
    
    // Variable that is written but never read
    let mut unused_mut = 10;
    unused_mut = 20;
    
    // Unnecessary parentheses
    let result = (5 + 3);
    println!("Result: {}", result);
    
    // Unreachable code
    return;
    println!("This will never print");
}

// Unused function
fn dead_function() {
    println!("This function is never called");
}

// Function with unused parameter
fn function_with_unused_param(x: i32, _y: i32) -> i32 {
    x * 2
}

// Non-snake-case function name
fn CamelCaseFunction() {
    println!("This should be snake_case");
}