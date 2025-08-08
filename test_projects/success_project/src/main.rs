fn main() {
    println!("Hello, world!");
    
    let numbers = vec![1, 2, 3, 4, 5];
    let sum: i32 = numbers.iter().sum();
    println!("Sum of numbers: {}", sum);
    
    let result = calculate_factorial(5);
    println!("5! = {}", result);
}

fn calculate_factorial(n: u32) -> u32 {
    match n {
        0 => 1,
        _ => n * calculate_factorial(n - 1),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_factorial() {
        assert_eq!(calculate_factorial(0), 1);
        assert_eq!(calculate_factorial(1), 1);
        assert_eq!(calculate_factorial(5), 120);
    }
}