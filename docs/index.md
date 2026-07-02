# Ethereum SSZ Specifications

This project provides a reference implementation of Ethereum's SSZ (Simple Serialize)
type system, serialization, and Merkleization.

## Specifications Overview

### SSZ Types and Serialization

The SSZ type system and (de)serialization live in `src/ssz/`: booleans, unsigned
integers, byte arrays, bitfields, lists, vectors, and containers.

### Merkleization

The `hash_tree_root` dispatch and the Merkleization primitives live in
`src/ssz/merkleization.py`.

## Design Principles

1. **Clarity over Performance**: Readable reference implementations
1. **Strong Typing**: Pydantic models with full validation
1. **Test Coverage**: Extensive tests for all modules

## Development

- [Readme](https://github.com/ethereum/ssz-specs/blob/main/README.md)
- [Contributing](https://github.com/ethereum/ssz-specs/blob/main/CONTRIBUTING.md)
