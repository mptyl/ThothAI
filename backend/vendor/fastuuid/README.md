# fastuuid shim

This package provides a minimal, pure-Python `fastuuid` module exposing the
subset of the API required by the ThothAI backend. It delegates to the standard
library `uuid` implementation so the backend can be built without compiling the
original Rust extension.
