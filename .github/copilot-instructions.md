# Instructions for LLM Code Generation

- This repository contains small Python GTK4 applications.
- Applications are packaged with Nix and do not require external dependencies.
- Each application has its own `.nix` file specifying dependencies.
- All applications are exported in the `flake.nix` file.

## Running Applications

To run an application, use:

```bash
nix --offline run path:.#app_name
```

## Testing Applications

To test an application, navigate to the application's directory and run the tests using Python's unittest framework:

```bash
cd $app_name && python -m unittest test_*.py
```
