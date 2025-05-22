# SigSynth

A tool for generating and validating synthetic log tests for Sigma rules against Panther, using a single OpenAI call per rule and local expansion for edge-case coverage.

## Features

- Parse Sigma YAML/JSON rules
- Generate positive and negative test seeds using OpenAI
- Expand seeds locally to create test variants
- Validate tests against rule logic
- Output Panther-compatible JSON test suites

## Installation

```bash
pip install sigsynth
```

## Usage

```bash
sigsynth generate \
  --rule aws_cloudtrail_change.yml \
  --platform panther \
  --seed-samples 5 \
  --samples 200 \
  --output panther_tests/
```

## Requirements

- Python 3.8+
- OpenAI API key (set via OPENAI_API_KEY environment variable)

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```

## License

MIT 