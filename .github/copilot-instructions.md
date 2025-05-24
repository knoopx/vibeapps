# Instructions for LLM Code Generation

- This repository contains small Python GTK4/libadwaita applications and some other utilities in javascript.
- Applications are packaged with Nix and do not require external dependencies.
- Each application has its own `.nix` file specifying dependencies.
- All applications are exported in the `flake.nix` file.

## Running Python Applications

To run an application, use:

```bash
nix --offline run path:.#app_name -- arg1 arg2
```

## Testing Python Applications

To test an application, navigate to the application's directory and run the tests using Python's unittest framework:

```bash
cd $app_name && python -m unittest test_*.py
```

## Running JavaScript Applications

Use **bun** to run JavaScript applications.

## Testing JavaScript Applications

Use Vitest for testing JavaScript applications.
Test files contain the suffix `test.js` and are located in the same directory as the application.


## Special Considerations when running shell commands in VSCode terminal

When running shell commands in the VSCode terminal, keep in mind the following:

The VSCode terminal is running Fish shell. You cannot run commands that span multiple lines like:

```bash
python -c "
# This is a multi-line command
print('Hello, World!')
"
```


Use **bun** instead of **node**.
