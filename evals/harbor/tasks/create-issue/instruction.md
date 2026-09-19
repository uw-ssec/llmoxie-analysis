File a GitHub issue for the repository at `/app`: the ADLS reader in the `io`
module crashes on empty JSON files. It should skip them and log a warning with
the file path.
