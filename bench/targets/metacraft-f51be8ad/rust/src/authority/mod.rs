pub use interface::Authority;

mod interface;
mod lifecycle;
mod protocol;

#[cfg(test)]
mod scale_tests;
#[cfg(test)]
mod verified_state_tests;
