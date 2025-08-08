fn main() {
    // Undefined variable
    println!("Value of x: {}", x);
    
    // Type mismatch
    let y: i32 = "not a number";
    
    // Undefined function
    undefined_function();
    
    // Missing semicolon
    let z = 42
    
    // Borrowing error
    let mut s = String::from("hello");
    let r1 = &s;
    let r2 = &mut s;
    println!("{}, {}", r1, r2);
}

fn unused_function() {
    println!("This function is never called");
}